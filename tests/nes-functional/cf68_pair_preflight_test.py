# SPDX-License-Identifier: MIT
"""Read-only preflight safety tests using an explicitly supplied private pair.
All SD operations use local temporary fixtures, never a mounted user card.
"""
from pathlib import Path
import argparse, json, shutil, sys, unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'tools'))
import nes_cf68_pair_preflight as p

class Preflight(unittest.TestCase):
    def setUp(self):
        self.root = OUT/self._testMethodName
        self.root.mkdir()
        self.sd = self.root/'sd'
        self.sd.mkdir()
        for name, data in [(p.TARGETS[0], b'original working firmware'),
                           (p.RECOVERY[0], p.encode(b'original base FPGA')),
                           (p.RECOVERY[1], b'menu fixture; classification pending'),
                           ('sd2snes/gbc-sentinel.bi3', b'untouched GBC')]:
            p.write_new(self.sd, name, data)
        self.before = self.snapshot()
        self.copy = self.root/'backup'

    def snapshot(self):
        return {f.relative_to(self.sd).as_posix():p.digest(f.read_bytes())
                for f in self.sd.rglob('*') if f.is_file()}

    def backup(self):
        value = p.backup(PAIR, SHA, self.sd, self.copy)
        self.assertEqual(self.before, self.snapshot())
        return value

    def changed_candidate(self):
        for name in p.TARGETS:
            dest = self.sd/name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(p.read(PAIR, 'sd-overlay/'+name))

    def test_01_eof_and_long_run(self):
        for n in [1, 3, 4, 255, 256, 65534, 65535, 65536, 131071]:
            raw = b'\xff'*n
            self.assertEqual(p.decode(p.encode(raw)), raw)
        raw = bytes(range(256))*2+b'\x9b'*4+b'\x77'*65536+b'\x5b'*257
        self.assertEqual(p.decode(p.encode(raw)), raw)
        p.write_new(self.root, 'boundaries.rbf', raw)
        p.write_new(self.root, 'boundaries.bi3', p.encode(raw))

    def test_02_bad_tokens_and_limits(self):
        for raw in [b'', b'\x9b', b'\x5b\x01', b'\x5b\x01\0',
                    b'\x77\x01\x01', b'\x77\x01\0\0', b'a'*1048577,
                    b'\x77\x01\xff\xff'*33]:
            with self.assertRaises(ValueError):
                p.decode(raw)

    def test_03_real_pair(self):
        m = p.verify(PAIR, SHA)
        self.assertFalse(m['installable'])
        self.assertEqual(m['files'][p.RAW]['size'], 510856)

    def test_04_pair_tamper(self):
        altered = self.root/'pair'
        shutil.copytree(PAIR, altered)
        (altered/'sd-overlay'/p.TARGETS[1]).write_bytes(b'bad')
        with self.assertRaisesRegex(ValueError, 'Pair file mismatch'):
            p.verify(altered, SHA)

    def test_05_manifest_tamper(self):
        altered = self.root/'pair'
        shutil.copytree(PAIR, altered)
        (altered/'pair-manifest.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'digest mismatch'):
            p.verify(altered, SHA)

    def test_06_wrong_firmware(self):
        fw = self.root/'bad.stm'
        fw.write_bytes(b'wrong firmware')
        with self.assertRaisesRegex(ValueError, 'Unreviewed069'):
            p.prepare(fw, PAIR/p.RAW, self.root/'new')
        self.assertFalse((self.root/'new').exists())

    def test_07_wrong_fpga(self):
        raw = self.root/'bad.rbf'
        raw.write_bytes(b'wrong FPGA')
        with self.assertRaisesRegex(ValueError, 'Unreviewed068'):
            p.prepare(PAIR/'sd-overlay'/p.TARGETS[0], raw, self.root/'new')

    def test_08_traversal(self):
        for name in ['../escape', 'C:/escape', '/escape', 'dir\\escape']:
            with self.assertRaises(ValueError):
                p.read(self.sd, name)

    def test_09_required_recovery(self):
        (self.sd/p.RECOVERY[1]).unlink()
        with self.assertRaisesRegex(ValueError, 'required'):
            p.backup(PAIR, SHA, self.sd, self.copy)
        self.assertFalse(self.copy.exists())

    def test_10_backup_must_be_off_sd(self):
        with self.assertRaisesRegex(ValueError, 'independent'):
            p.backup(PAIR, SHA, self.sd, self.sd/'backup')
        self.assertEqual(self.before, self.snapshot())

    def test_11_backup_noop_rollback(self):
        sha = self.backup()
        plan = p.rollback_plan(PAIR, SHA, self.sd, self.copy, sha)
        self.assertEqual(plan['actions'], [])
        self.assertFalse(plan['executed'])
        self.assertEqual(self.before, self.snapshot())

    def test_12_candidate_restore_plan(self):
        sha = self.backup()
        self.changed_candidate()
        after = self.snapshot()
        plan = p.rollback_plan(PAIR, SHA, self.sd, self.copy, sha)
        self.assertEqual(len(plan['actions']), 6)
        self.assertEqual(sum(a['action']=='restore' for a in plan['actions']), 1)
        self.assertEqual(sum(a['action']=='remove-created' for a in plan['actions']), 5)
        self.assertEqual(after, self.snapshot())
        p.save(self.root, 'rollback-plan.json', plan)

    def test_13_unknown_changed_target(self):
        sha = self.backup()
        (self.sd/p.TARGETS[0]).write_bytes(b'other firmware')
        with self.assertRaisesRegex(ValueError, 'Unknown changed'):
            p.rollback_plan(PAIR, SHA, self.sd, self.copy, sha)

    def test_14_changed_recovery(self):
        sha = self.backup()
        (self.sd/p.RECOVERY[1]).write_bytes(b'other menu')
        with self.assertRaisesRegex(ValueError, 'Unknown changed'):
            p.rollback_plan(PAIR, SHA, self.sd, self.copy, sha)

    def test_15_backup_digest(self):
        self.backup()
        with self.assertRaisesRegex(ValueError, 'Backup manifest digest'):
            p.rollback_plan(PAIR, SHA, self.sd, self.copy, '0'*64)

    def test_16_backup_file_corruption(self):
        sha = self.backup()
        (self.copy/'original'/p.TARGETS[0]).write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError, 'Original backup mismatch'):
            p.rollback_plan(PAIR, SHA, self.sd, self.copy, sha)

    def test_17_existing_backup_not_overwritten(self):
        self.backup()
        with self.assertRaises(FileExistsError):
            p.backup(PAIR, SHA, self.sd, self.copy)

    def test_18_sd_changed_during_backup(self):
        original = p.state
        calls = 0
        def changed(sd, name):
            nonlocal calls
            calls += 1
            value = original(sd, name)
            if calls > len(p.TARGETS+p.RECOVERY):
                return p.record(b'changed'), b'changed'
            return value
        with patch.object(p, 'state', changed):
            with self.assertRaisesRegex(ValueError, 'SD changed'):
                p.backup(PAIR, SHA, self.sd, self.copy)
        self.assertFalse((self.copy/'backup-manifest.json').exists())
        self.assertEqual(self.before, self.snapshot())

    def test_19_old_firmware(self):
        with self.assertRaisesRegex(ValueError, 'Unreviewed069'):
            p.prepare(LEGACY/'sd-overlay/sd2snes/firmware.stm', PAIR/p.RAW, self.root/'new')

    def test_20_old_fpga(self):
        with self.assertRaisesRegex(ValueError, 'Unreviewed068'):
            p.prepare(PAIR/'sd-overlay'/p.TARGETS[0], LEGACY/p.RAW, self.root/'new')

    def test_21_contract_identity(self):
        for field,value in [('fpga_identity','CF61/protocol59'),('firmware_identity','NES-MENU-RETURN-065'),('log_path','/sd2snes/nes-verify-last-065.txt'),('clock_halt_safe',True),('installable',True),('start_enabled',True)]:
            altered=self.root/field
            shutil.copytree(PAIR,altered)
            m=json.loads(p.read(altered,'pair-manifest.json'));m[field]=value
            data=(json.dumps(m)+'\n').encode();(altered/'pair-manifest.json').write_bytes(data)
            with self.assertRaisesRegex(ValueError,'Pair contract mismatch'):
                p.verify(altered,p.digest(data))

    def test_22_old_package(self):
        with self.assertRaisesRegex(ValueError,'Pair contract mismatch'):
            p.verify(LEGACY,p.digest(p.read(LEGACY,'pair-manifest.json')))

    def test_23_extra_eof_byte(self):
        altered=self.root/'pair';shutil.copytree(PAIR,altered)
        name=p.TARGETS[1];data=p.read(altered,'sd-overlay/'+name)+b'\xff'
        (altered/'sd-overlay'/name).write_bytes(data)
        m=json.loads(p.read(altered,'pair-manifest.json'));m['files'][name]=p.record(data)
        manifest=json.dumps(m).encode();(altered/'pair-manifest.json').write_bytes(manifest)
        with self.assertRaisesRegex(ValueError,'Pair roundtrip mismatch'):
            p.verify(altered,p.digest(manifest))

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--legacy-package', type=Path, required=True)
    parser.add_argument('--package', type=Path, required=True)
    parser.add_argument('--manifest-sha', required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    PAIR, SHA, OUT, LEGACY = args.package, args.manifest_sha, args.out, args.legacy_package
    OUT.mkdir(exist_ok=False)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Preflight))
    p.save(OUT, 'result.json', dict(tests=result.testsRun, failures=len(result.failures),
           errors=len(result.errors), skipped=len(result.skipped), physical_sd=False,
           pair_manifest_sha256=SHA))
    sys.exit(not result.wasSuccessful())
