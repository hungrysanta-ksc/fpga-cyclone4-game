# SPDX-License-Identifier: MIT
"""ASM-only reproduction from the explicitly pinned private061 fit database.
The public clone does not supply this database, firmware, or binaries.
"""
from pathlib import Path
import argparse, json, shutil, subprocess
from nes_pair_preflight import digest, RBF_SHA

ROOT = Path(__file__).resolve().parents[1]

def database(root):
    entries = []
    for directory in ['db', 'incremental_db']:
        for f in sorted((root/directory).rglob('*')):
            if f.is_file():
                entries.append([f.relative_to(root).as_posix(), digest(f.read_bytes())])
    entries.sort()
    return len(entries), digest(json.dumps(entries, separators=(',', ':')).encode())

def assemble(fit, out, quartus):
    m = json.loads((ROOT/'analysis/pair-preflight-verification.json').read_text())
    def validate(root):
        for name, value in m['fit_inputs'].items():
            if digest((root/name).read_bytes()) != value:
                raise ValueError('061 fit input changed: '+name)
        if database(root) != (m['database_files'], m['database_sha256']):
            raise ValueError('061 database lineage mismatch')
    validate(fit)
    if out.exists() or not str(out.resolve()).isascii() or out.resolve().is_relative_to(fit.resolve()):
        raise ValueError('New independent ASCII output required')
    shutil.copytree(fit, out)
    validate(out)
    phases = [('asm', [quartus/'quartus_asm.exe', 'board']),
              ('cpf', [quartus/'quartus_cpf.exe', '-c',
                       'output_files/board.sof', 'output_files/board.rbf'])]
    for phase, command in phases:
        log = out/(phase+'-066.log')
        with log.open('wb') as stream:
            result = subprocess.run(command, cwd=out, stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=300)
        text = log.read_text(encoding='utf-8', errors='replace')
        if (result.returncode or 'successful. 0 errors, 0 warnings' not in text
                or 'SC Standard Edition' not in text or '25.1std.0 Build 1129' not in text):
            raise ValueError('Inspect raw '+str(log))
    raw = out/'output_files/board.rbf'
    if digest(raw.read_bytes()) != RBF_SHA:
        raise ValueError('RBF differs from reviewed066 image')
    (out/'assembly-066.json').write_text(json.dumps(dict(candidate=m['candidate'],
         database_sha256=m['database_sha256'], fit_inputs=m['fit_inputs'],
         rbf_sha256=RBF_SHA, rbf_bytes=raw.stat().st_size,
         new_map_fit_sta=False, external_io_constrained=False, installable=False), indent=2)+'\n')
    print('PASS066 pinned061 Standard ASM/CPF; RBF bytes='+str(raw.stat().st_size))

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--fit', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--quartus-bin', type=Path, required=True)
    a = p.parse_args()
    assemble(a.fit, a.out, a.quartus_bin)
