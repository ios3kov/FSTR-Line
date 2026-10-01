import importlib.util
import json
from pathlib import Path
import struct
import tempfile
import unittest
import uuid

MODULE = Path(__file__).resolve().parents[2] / 'research/ae-notifications/inspect_binary.py'
spec = importlib.util.spec_from_file_location('inspect_binary', MODULE)
inspector = importlib.util.module_from_spec(spec)
spec.loader.exec_module(inspector)


def thin(endian='<', bits=64, symbol=True):
    marker = 0xFEEDFACF if bits == 64 else 0xFEEDFACE
    cpu = 0x100000C if bits == 64 else 12
    size = 32 if bits == 64 else 28
    uid = uuid.UUID('01234567-89ab-cdef-0123-456789abcdef').bytes
    commands = struct.pack(endian + '2I', 0x1B, 24) + uid
    symoff = size + 48
    name = b'\0_ProjectNotifyCandidate\0'
    stroff = symoff + (16 if bits == 64 else 12)
    if symbol:
        commands += struct.pack(endian + '6I', 2, 24, symoff, 1, stroff, len(name))
    header = struct.pack(endian + '7I', marker, cpu, 0, 2, 2 if symbol else 1, len(commands), 0)
    if bits == 64:
        header += struct.pack(endian + 'I', 0)
    entry = struct.pack(endian + ('IBBHQ' if bits == 64 else 'IBBHI'), 1, 0x0F, 1, 0, 0x1000)
    return header + commands + (entry + name if symbol else b'') + b'\0Timeline dispatch\0'


class InspectionTests(unittest.TestCase):
    def test_thin_byte_orders_and_sizes(self):
        for endian in ['<', '>']:
            for bits in [32, 64]:
                with self.subTest(endian=endian, bits=bits):
                    result = inspector.parse_macho(thin(endian, bits))[0]
                    self.assertEqual(result['uuid'], '01234567-89ab-cdef-0123-456789abcdef')
                    self.assertEqual(result['matchingSymbols'][0]['unslidValue'], '0x1000')
                    self.assertTrue(result['matchingSymbols'][0]['defined'])

    def test_fat_variants(self):
        for endian in ['<', '>']:
            for is64 in [False, True]:
                payload = thin()
                magic = 0xCAFEBABF if is64 else 0xCAFEBABE
                header = struct.pack(endian + '2I', magic, 1)
                values = [0x100000C, 0, 64, len(payload), 2] + ([0] if is64 else [])
                header += struct.pack(endian + ('IIQQII' if is64 else 'IIIII'), *values)
                data = header + b'\0' * (64 - len(header)) + payload
                self.assertEqual(inspector.parse_macho(data)[0]['fileOffset'], 64)

    def test_truncated_bad_headers_and_unrecognized_file(self):
        for data in [b'', b'ELF\0', thin()[:20], thin()[:55], b'\xca\xfe\xba\xbe' + struct.pack('>I', 1000)]:
            with self.assertRaises(ValueError):
                inspector.parse_macho(data)

    def test_fat_out_of_bounds(self):
        data = struct.pack('>7I', 0xCAFEBABE, 1, 0x100000C, 0, 100, 1000, 2)
        with self.assertRaises(ValueError):
            inspector.parse_macho(data)

    def test_bounded_strings_and_no_input_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Fixture'
            data = thin() + b'project\0' * 100
            path.write_bytes(data)
            before = path.stat().st_mtime_ns
            report = inspector.inspect_file(path, max_scan=100, max_leads=1)
            self.assertTrue(report['stringScanLimited'])
            self.assertEqual(report['SYNC-001'], 'NOT RUN')
            self.assertEqual(path.read_bytes(), data)
            self.assertEqual(path.stat().st_mtime_ns, before)

    def test_stripped_binary_does_not_prove_no_events(self):
        result = inspector.parse_macho(thin(symbol=False))[0]
        self.assertEqual(result['symbolsDeclared'], 0)
        self.assertEqual(result['matchingSymbols'], [])

    def test_reject_symlink_and_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'Fixture'
            path.write_bytes(thin())
            link = Path(directory) / 'Link'
            link.symlink_to(path)
            for item in [link, Path(directory)]:
                with self.assertRaises(ValueError):
                    inspector.inspect_file(item)

    def test_unique_results_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            a = inspector.write_report({'status': 'fixture'}, root)
            b = inspector.write_report({'status': 'fixture'}, root)
            self.assertNotEqual(a, b)
            self.assertNotEqual(json.loads(a.read_text())['testRunId'], json.loads(b.read_text())['testRunId'])

    def test_corrupt_symbol_string_index(self):
        data = bytearray(thin())
        struct.pack_into('<I', data, 80, 999999)
        with self.assertRaises(ValueError):
            inspector.parse_macho(data)


if __name__ == '__main__':
    unittest.main()
