#!/usr/bin/env python3
"""Build only; no install, AE launch, settings changes or SDK redistribution."""
import argparse
import hashlib
import json
import platform
import plistlib
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SOURCE = Path(__file__).resolve().parent
SDK_HEADER_SHA = '30d12ec3eb5af1a902c7414053b1be1da0204b226e0b1cdc71272be1e137000c'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(args):
    done = subprocess.run(args, check=True, capture_output=True, text=True, timeout=120)
    return done.stdout.strip()


def build(sdk, research_opt_in=False):
    if platform.system() != 'Darwin' or platform.machine() != 'arm64':
        raise ValueError('BLOCKED: a native Apple Silicon macOS build is required')
    def git(*args):
        return run(['git', '-C', str(ROOT), *args])
    if git('status', '--porcelain', '--untracked-files=normal'):
        raise ValueError('DIRTY_SOURCE')
    commit = git('rev-parse', 'HEAD')
    sdk = sdk.resolve(strict=True)
    headers = sdk / 'Examples/Headers'
    resources = sdk / 'Examples/Resources'
    if digest(headers / 'AE_GeneralPlug.h') != SDK_HEADER_SHA:
        raise ValueError('SDK_HEADER_IDENTITY_MISMATCH')
    inputs = sorted(p for p in headers.rglob('*') if p.is_file() and not p.name.startswith('._'))
    inputs += [resources / 'AE_General.r']
    if any(p.is_symlink() for p in inputs):
        raise ValueError('SDK_SYMLINK_INPUT_REFUSED')
    sdk_hashes = {str(p.relative_to(sdk)): digest(p) for p in inputs}
    mode = 'research-opt-in' if research_opt_in else 'disabled'
    out = ROOT / 'dist/chain-probe' / (commit + '-' + mode)
    out.mkdir(parents=True, exist_ok=False)
    marker = out / 'INCOMPLETE'
    marker.write_text('No artifact acceptance until build-record.json exists.\n')
    bundle = out / 'FSTRChainProbe.plugin'
    mac = bundle / 'Contents/MacOS'; res = bundle / 'Contents/Resources'
    mac.mkdir(parents=True); res.mkdir()
    build_id = 'fstr-chain-aegp-' + commit[:12] + '-' + mode
    binary = mac / 'FSTRChainProbe'
    metadata = {'CFBundleExecutable':'FSTRChainProbe', 'CFBundleIdentifier':'tv.fstr.line.chain-probe',
        'CFBundleName':'FSTR Chain Probe', 'CFBundlePackageType':'AEgx', 'CFBundleSignature':'FXTC',
        'CFBundleVersion':'1.0.0', 'CFBundleShortVersionString':'1.0', 'FSTRBuildID':build_id}
    (bundle / 'Contents/Info.plist').write_bytes(plistlib.dumps(metadata))
    compiler = run(['xcrun', 'clang++', '--version'])
    run(['xcrun','clang++','-arch','arm64','-std=c++17','-O2','-bundle','-fvisibility=hidden',
        '-fexceptions','-Wall','-Wextra','-Werror','-Wno-deprecated-declarations',
        '-mmacosx-version-min=12.0', '-I',str(headers),'-I',str(headers/'SP'),
        '-DFSTR_PROBE_BUILD_ID=' + json.dumps(build_id),
        '-DFSTR_ENABLE_PRIVATE_CHAIN_PROBE=' + str(int(research_opt_in)),
        str(SOURCE/'aegp_probe.cpp'),str(SOURCE/'binding_macos.cpp'),
        '-framework','CoreFoundation','-framework','CoreServices','-o',str(binary)])
    run(['xcrun','Rez','-useDF','-i',str(resources),str(SOURCE/'Probe_PiPL.r'),
         '-o',str(res/'FSTRChainProbe.rsrc')])
    run(['plutil','-lint',str(bundle/'Contents/Info.plist')])
    if run(['xcrun','lipo','-archs',str(binary)]) != 'arm64':
        raise ValueError('UNEXPECTED_ARCHITECTURE')
    exports = run(['xcrun','nm','-gU',str(binary)])
    if '_EntryPointFunc' not in {line.split()[-1] for line in exports.splitlines() if line.split()}:
        raise ValueError('MISSING_ENTRY_EXPORT')
    run(['codesign','--force','--sign','-',str(bundle)])
    run(['codesign','--verify','--strict',str(bundle)])
    if any(digest(p) != sdk_hashes[str(p.relative_to(sdk))] for p in inputs):
        raise ValueError('SDK_CHANGED_DURING_BUILD')
    if git('rev-parse','HEAD') != commit or git('status','--porcelain'):
        raise ValueError('SOURCE_CHANGED_DURING_BUILD')
    record = {'status':'BUILT_NOT_RUNTIME_TESTED','sourceCommit':commit,'sourceState':'clean',
        'buildId':build_id,'platform':'macOS arm64','compiler':compiler,
        'sdkInputSha256':sdk_hashes,'privateProbeOptIn':research_opt_in,'signing':'ad-hoc',
        'files':{str(p.relative_to(bundle)):digest(p) for p in sorted(bundle.rglob('*')) if p.is_file()},
        'AEGP_load':'NOT RUN','SYNC-001':'NOT RUN','handoffApproved':False}
    (out/'build-record.json').write_text(json.dumps(record,indent=2)+'\n')
    marker.unlink() # only our completion marker; never user/application files
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sdk',type=Path,required=True)
    parser.add_argument('--research-opt-in',action='store_true',help='Unaccepted isolated research only, not production')
    args = parser.parse_args()
    try:
        print(json.dumps(build(args.sdk,args.research_opt_in)))
    except (OSError,ValueError,subprocess.SubprocessError) as error:
        raise SystemExit('BLOCKED: ' + str(error))
