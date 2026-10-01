"""Owned Mach-O/file and synthetic collector controls. None invokes Adobe code."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
import plistlib
import struct
import zipfile
import subprocess
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / 'research/ae-notifications'


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


m = load('range_inspector', SRC / 'inspect_binary.py')
q = load('context_queue', SRC / 'queue_static.py')
k = load('context_kit', SRC / 'queue_kit.py')
p = load('context_packager', ROOT / 'scripts/package-queue-research.py')
UID = '00000000-0000-4000-8000-000000000001'


def linked_image(*, cpu=0x100000c, subtype=0, section_type=0, section_offset=0x200, duplicate=False):
    """Fabricated linked-image bytes; NOT an Adobe image."""
    section = struct.pack('<16s16sQQIIIIIIII', b'__const', b'__TEXT', 0x1200, 16,
                          section_offset, 0, 0, 0, section_type, 0, 0, 0)
    n = 2 if duplicate else 1
    segment = struct.pack('<II16sQQQQiiII', 0x19, 72 + 80*n, b'__TEXT',
                          0x1000, 0x300, 0, 0x300, 7, 5, n, 0) + section*n
    commands = struct.pack('<II16s', 0x1b, 24, uuid.UUID(UID).bytes) + segment
    header = struct.pack('<8I', 0xfeedfacf, cpu, subtype, 6, 2, len(commands), 0, 0)
    data = bytearray((header + commands).ljust(0x300, b'\0'))
    data[0x200:0x204] = bytes([0, 41, 43, 47])
    return bytes(data)


def output(text):
    return {'text': text, 'complete': True, 'exitCode': 0, 'reason': None,
            'bytes': len(text.encode()), 'sha256': q.digest(text.encode())}


class RangeTests(unittest.TestCase):
    def read(self, data=None, address=0x1200, length=4, **kw):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td)/'owned.dylib'
            path.write_bytes(data if data is not None else linked_image())
            return m.read_macho_range(path, kw.get('expected_sha', q.fingerprint(path)),
                                      kw.get('expected_uuid', UID), address, length)

    def test_vm_address_is_not_file_offset(self):
        row = self.read()
        self.assertEqual(row['hex'], '00292b2f')
        self.assertEqual(row['fileOffset'], 0x200)
        self.assertEqual(row['vmAddress'], '0x1200')
        self.assertEqual(row['sha256'], q.digest(bytes.fromhex(row['hex'])))

    def test_fat_slice_offset_not_first_slice(self):
        a, b = linked_image(cpu=0x1000007), linked_image()
        header = struct.pack('>II', 0xcafebabe, 2)
        header += struct.pack('>IIIII', 0x1000007, 0, 0x1000, len(a), 12)
        header += struct.pack('>IIIII', 0x100000c, 0, 0x2000, len(b), 12)
        raw = header.ljust(0x1000,b'\0')+a
        raw = raw.ljust(0x2000,b'\0')+b
        row = self.read(raw)
        self.assertEqual(row['fileOffset'], 0x2200)
        self.assertEqual(row['sliceOffset'], 0x2000)
        self.assertEqual(row['hex'], '00292b2f')

    def test_uuid_hash_and_architecture_refusal(self):
        for kw in ({'expected_sha':'f'*64}, {'expected_uuid':str(uuid.uuid4())},
                   {'data':linked_image(cpu=0x1000007)}, {'data':linked_image(subtype=2)}):
            with self.subTest(kw=kw), self.assertRaises(ValueError): self.read(**kw)

    def test_zero_fill_cross_section_and_ambiguous_range_refusal(self):
        for kw in ({'data':linked_image(section_type=1)}, {'address':0x120e},
                   {'data':linked_image(duplicate=True)}, {'address':0x1111}):
            with self.subTest(kw=kw), self.assertRaises(ValueError): self.read(**kw)

    def test_invalid_size_mapping_and_truncated_commands_refusal(self):
        for data in (linked_image(section_offset=0x400), linked_image()[:150],
                     linked_image(section_offset=0x204), b'\0'*128):
            with self.subTest(length=len(data)), self.assertRaises(ValueError): self.read(data)

    def test_read_bounds_strict(self):
        for address, length in ((True,4),(-1,4),(0x1200,0),(0x1200,65),(2**64-1,4)):
            with self.subTest(address=address,length=length), self.assertRaises(ValueError):
                self.read(address=address,length=length)

    def test_symlink_and_fifo_refused_without_blocking(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); target=root/'source'; target.write_bytes(linked_image())
            for path in (root/'link',root/'fifo'):
                if path.name=='link': path.symlink_to(target)
                else: os.mkfifo(path)
                with self.assertRaises((OSError,ValueError)):
                    m.read_macho_range(path,q.fingerprint(target),UID,0x1200,4)
            self.assertEqual(target.read_bytes(),linked_image())

    def test_detects_changes_between_hashes(self):
        real = hashlib.sha256
        count = 0
        def changed(data):
            nonlocal count
            count += 1
            return real(data) if count == 1 else real(b'changed')
        # fingerprint uses the same hashlib module, so supply known digest first.
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'source'; path.write_bytes(linked_image()); digest=q.fingerprint(path)
            with mock.patch.object(m.hashlib,'sha256',side_effect=changed), self.assertRaisesRegex(ValueError,'changed'):
                m.read_macho_range(path,digest,UID,0x1200,4)

    @unittest.skipUnless(sys.platform=='darwin', 'requires Apple linker; mandatory in macOS CI, not an AE test')
    def test_real_linked_macho_table(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); source=root/'owned.c'; binary=root/'owned.dylib'
            source.write_text('const unsigned char fstr_range_table[4]={1,7,29,43};\nint fstr_range_control(void){return 1;}\n')
            args=['xcrun','clang','-arch','arm64','-dynamiclib',str(source),'-o',str(binary)]
            subprocess.run(args,check=True,capture_output=True,timeout=30)
            symbols=subprocess.check_output(['xcrun','nm','-U',str(binary)],text=True,timeout=30)
            line=next(x for x in symbols.splitlines() if x.split() and x.split()[-1]=='_fstr_range_table')
            address=int(line.split()[0],16)
            image=next(s for s in m.parse_macho(binary.read_bytes()) if s['cpuType']==0x100000c)
            row=m.read_macho_range(binary,q.fingerprint(binary),image['uuid'],address,4)
            self.assertEqual(row['hex'],'01071d2b')
            self.assertEqual(row['byteCount'],4)


class ContextProfileTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name).resolve(); self.app=self.root/'Owned fixture.app'
        (self.app/'Contents').mkdir(parents=True)
        self.policy={'aeBundleId':'org.fstr.fixture','aeShortVersion':'fixture','aeBundleVersion':'fixture.1','modules':{}}
        (self.app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'org.fstr.fixture',
            'CFBundleShortVersionString':'fixture','CFBundleVersion':'fixture.1'}))
        self.calls=[];self.symbols={}
        for key,names in q.CONTEXT_REQUIRED.items():
            path=self.app/'Contents'/key;path.write_bytes(key.encode())
            self.policy['modules'][key]={'relativePath':'Contents/'+key,'sha256':q.fingerprint(path),'uuid':UID}
            self.symbols[key]={n:(q.CONTEXT_TABLE['functionAddress'] if n==q.CONTEXT_REQUIRED['BEE'][-1] else 0x1000+16*i)
                               for i,n in enumerate(names)} or {'_owned':0x1000}
        self.table={**q.CONTEXT_TABLE,'moduleSha256':self.policy['modules']['BEE']['sha256']}
        self.patch=mock.patch.object(q,'CONTEXT_TABLE',self.table);self.patch.start();self.addCleanup(self.patch.stop)
        self.reader=mock.Mock(side_effect=self.range_row)

    def range_row(self,path,digest,uid,address,length):
        return {'moduleSha256':digest,'arm64UUID':uid,'vmAddress':hex(address),'byteCount':length,
                'hex':'00292b2f','sha256':q.digest(bytes.fromhex('00292b2f'))}

    def runner(self,args,**limits):
        self.calls.append(args)
        if args[-1]=='--version': return output('Owned fixture tool\n')
        key=Path(args[-1]).name
        if args[1]=='dwarfdump':return output(f'UUID: {UID} (arm64) fixture\n')
        if args[1]=='nm': return output(''.join(f'{a:016x} T {n}\n' for n,a in self.symbols[key].items()))
        name=args[args.index('--dis-symname')+1];address=self.symbols[key][name]
        count=128 if name==q.CONTEXT_REQUIRED['BEE'][-1] else 2
        return output(name+':\n'+''.join(f'{address+4*i:x}\t'+('ret' if i==count-1 else 'nop')+'\n' for i in range(count)))

    def collect(self,**kw):
        return q.collect(self.app,self.policy,self.runner,context_followup=True,read_range=self.reader,**kw)

    def test_only_missing_helpers_and_anchor_are_requested(self):
        row=self.collect()
        self.assertEqual(row['collectionStatus'],'PASS',row)
        self.assertEqual(row['expectedBodyCount'],5)
        self.assertEqual(row['profile'],'context-followup')
        self.assertEqual(len([a for a in self.calls if '--disassemble' in a]),5)
        self.assertEqual(set(row['claims'].values()),{'UNPROVEN'})
        self.assertFalse(row['privateInvocationAllowed']);self.assertEqual(row['SYNC-001'],'NOT RUN')
        self.assertEqual(row['commandTypeTable']['targets'][0],{'commandType':0,'unslidTarget':'0x777c8c'})
        self.assertNotIn(str(self.root),json.dumps(row))
        self.assertFalse(any('lldb' in ' '.join(a) for a in self.calls))

    def test_missing_helper_refused_before_body_or_range(self):
        self.symbols['BEE'].pop(q.CONTEXT_REQUIRED['BEE'][0])
        row=self.collect()
        self.assertEqual(row['collectionStatus'],'BLOCKED');self.reader.assert_not_called()
        self.assertFalse(any('--disassemble' in a for a in self.calls))

    def test_ambiguous_helper_refused_before_disassembly(self):
        original = self.runner
        name = q.CONTEXT_REQUIRED['BEE'][0]
        def ambiguous(args, **kw):
            row = original(args, **kw)
            if args[1] == 'nm' and Path(args[-1]).name == 'BEE' and '-gU' not in args:
                return output(row['text'] + f'00009000 T {name}\n')
            return row
        self.runner = ambiguous
        row = self.collect()
        self.assertEqual(row['collectionStatus'], 'BLOCKED')
        self.assertTrue(row['reason'].startswith('AMBIGUOUS_REQUESTED_TEXT_SYMBOL'))
        self.assertFalse(any('--disassemble' in a for a in self.calls))
        self.reader.assert_not_called()

    def test_both_module_identities_required(self):
        (self.app/'Contents/AfterFXLib').write_bytes(b'changed')
        row=self.collect()
        self.assertEqual(row['reason'],'MODULE_HASH_MISMATCH:AfterFXLib')
        self.reader.assert_not_called();self.assertFalse(any('nm' in a for a in self.calls))

    def test_profile_rejects_other_build_and_extra_selection(self):
        self.policy['modules']['BEE']['sha256']='f'*64
        self.assertEqual(self.collect()['reason'],'CONTEXT_PROFILE_BUILD_MISMATCH')
        self.assertEqual(self.collect(inspect_symbols=['BEE:_other'])['reason'],'CONTEXT_PROFILE_DISALLOWS_EXTRA_SYMBOLS')
        self.assertEqual(self.calls,[]);self.reader.assert_not_called()

    def test_failed_range_never_becomes_partial_pass(self):
        self.reader.side_effect=ValueError('no backing section')
        row=self.collect();self.assertEqual(row['collectionStatus'],'BLOCKED')
        self.assertNotIn('commandTypeTable',row)

    def test_range_hash_uuid_address_and_out_of_body_refused(self):
        original=self.range_row(None,self.table['moduleSha256'],UID,self.table['vmAddress'],4)
        for change in ({'sha256':'0'*64},{'arm64UUID':str(uuid.uuid4())},{'vmAddress':'0x0'},
                       {'hex':'ffffffff','sha256':q.digest(bytes.fromhex('ffffffff'))}):
            with self.subTest(change=change):
                self.reader.side_effect=None;self.reader.return_value={**original,**change}
                self.assertEqual(self.collect()['collectionStatus'],'BLOCKED')

    def test_anchor_and_persistent_replacement_refused(self):
        anchor=q.CONTEXT_REQUIRED['BEE'][-1];self.symbols['BEE'][anchor]+=4
        self.assertEqual(self.collect()['reason'],'CONTEXT_ANCHOR_ADDRESS_MISMATCH')
        self.reader.assert_not_called();self.symbols['BEE'][anchor]-=4
        def change(*args):
            row=self.range_row(*args);(self.app/'Contents/BEE').write_bytes(b'changed');return row
        self.reader.side_effect=change
        self.assertEqual(self.collect()['reason'],'MODULE_CHANGED_DURING_COLLECTION:BEE')

    def test_default_request_unchanged(self):
        self.assertEqual(q.requested_symbols([]),{key:list(names) for key,names in q.REQUIRED.items()})


class PackagedContextTests(unittest.TestCase):
    def test_clean_committed_package_has_complete_context_payload(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = root / 'research/ae-notifications'; source.mkdir(parents=True)
            for name in p.NAMES:
                (source / name).write_bytes((SRC / name).read_bytes())
            (root / '.gitignore').write_text('dist/\n')
            def git(*args):
                return subprocess.check_output(['git','-C',str(root),*args],stderr=subprocess.PIPE,timeout=15)
            git('init','-q'); git('add','.')
            git('-c','user.name=Owned test','-c','user.email=test@example.invalid',
                '-c','commit.gpgsign=false','commit','-qm','owned context package control')
            built = p.build(root)
            with zipfile.ZipFile(built['archive']) as archive:
                self.assertEqual(set(archive.namelist()), {'FSTR-AE-Queue/'+n for n in (*p.NAMES,'build-manifest.json')})
                archive.extractall(root/'unpacked')
            kit = root/'unpacked/FSTR-AE-Queue'
            manifest, payload = k.verify_kit(kit)
            self.assertEqual(manifest['sourceCommit'], built['sourceCommit'])
            self.assertEqual(payload['inspect_binary.py'], (SRC/'inspect_binary.py').read_bytes())
            done = subprocess.run(['bash',str(kit/'Queue-Context.command'),'--verify-only'],capture_output=True,text=True,timeout=15)
            self.assertEqual(done.returncode,0,done.stdout+done.stderr)

    def test_verified_context_entrypoint_and_changed_reader_refusal(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);kit=root/'kit with spaces';kit.mkdir()
            files={n:(SRC/n).read_bytes() for n in p.NAMES}
            manifest={'schemaVersion':1,'sourceCommit':'1'*40,'sourceState':'clean','buildId':'fstr-queue-'+'1'*12,
                      'files':{n:q.digest(b) for n,b in files.items()}}
            for n,b in files.items():(kit/n).write_bytes(b)
            (kit/'build-manifest.json').write_text(json.dumps(manifest))
            run=subprocess.run(['bash',str(kit/'Queue-Context.command'),'--verify-only'],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertEqual(json.loads(run.stdout)['kitStatus'],'PASS')
            app=root/'Non Adobe.app';(app/'Contents').mkdir(parents=True)
            (app/'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleIdentifier':'org.fstr.fixture'}))
            with mock.patch.object(k.platform,'system',return_value='Darwin'),contextlib.redirect_stdout(io.StringIO()):
                code=k.main(['--context-followup','--app',str(app),'--output',str(root/'reports')],root=kit)
            self.assertEqual(code,2)
            report=json.loads(next((root/'reports').glob('*/report.json')).read_bytes())
            self.assertEqual(report['reason'],'AE_BUILD_MISMATCH')
            (kit/'inspect_binary.py').write_text("raise AssertionError('must not run')")
            run=subprocess.run(['bash',str(kit/'Queue-Context.command'),'--verify-only'],capture_output=True,text=True,timeout=15)
            self.assertEqual(run.returncode,2);self.assertIn('KIT_HASH_MISMATCH:inspect_binary.py',run.stdout)


if __name__=='__main__':unittest.main()
