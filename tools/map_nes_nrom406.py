# SPDX-License-Identifier: MIT
"""Lite whole-board A&S comparison with only the 227 cart_top changed.

The NROM loader and physical package are not integrated: this is an area
diagnostic, not a functional-board or timing result. No FIT is run.
"""
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from nes_delta231 import BASE, sha


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    p.add_argument('--cart', required=True, type=Path)
    a = p.parse_args()
    d = a.out.resolve()
    assert d.as_posix().isascii() and not d.exists()
    d.mkdir(parents=True)
    src = BASE / 'probes/nes-repeat227/asm02'
    for q in src.rglob('*'):
        rel = q.relative_to(src)
        if any(part in ('db', 'incremental_db', 'output_files', 'simulation') for part in rel.parts):
            continue
        if q.is_file() and q.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
            dest = d / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(q, dest)
    shutil.copyfile(a.cart, d / 'cart_nrom.sv')
    inputs = {x.relative_to(d).as_posix(): sha(x) for x in d.rglob('*') if x.is_file()}
    with (d / 'map.log').open('wb') as log:
        run = subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe', 'board'],
                             cwd=d, stdout=log, stderr=subprocess.STDOUT,
                             timeout=900, creationflags=subprocess.CREATE_NO_WINDOW)
    raw = (d / 'map.log').read_text(errors='replace')
    report = d / 'output_files/board.map.summary'
    undriven = re.findall(r'Warning \(10034\):[^\r\n]+', raw)
    result = {'passed': run.returncode == 0 and report.exists() and not undriven,
              'inputs': inputs, 'cart_sha256': sha(d / 'cart_nrom.sv'),
              'undriven': undriven, 'summary': report.read_text() if report.exists() else None,
              'functional_board_test': False, 'loader_integrated': False,
              'FIT': False, 'STA': False}
    (d / 'result.json').write_text(json.dumps(result, indent=2) + '\n', newline='\n')
    print(json.dumps({k:v for k,v in result.items() if k != 'inputs'}, indent=2))
    assert result['passed']


if __name__ == '__main__':
    main()
