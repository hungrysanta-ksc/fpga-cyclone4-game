# SPDX-License-Identifier: MIT
"""Copy the fitted 661 board inputs, changing only the CPU program ROM contents."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import sha


def prepare(a):
    assert sha(a.base/'sink-program.hex')==sha(a.old_client/'sink-program.hex')
    a.out.mkdir(parents=True,exist_ok=False)
    extensions={'.v','.sv','.vhd','.qsf','.qpf','.sdc','.hex','.mif','.qip','.tcl'}
    for p in a.base.iterdir():
        if p.is_file() and p.suffix.lower() in extensions:
            shutil.copyfile(p,a.out/p.name)
    for name in ('rtl','sys'):
        shutil.copytree(a.base/name,a.out/name)
    shutil.copyfile(a.client/'sink-program.hex',a.out/'sink-program.hex')
    inputs={p.relative_to(a.out).as_posix():sha(p) for p in a.out.rglob('*') if p.is_file()}
    changed=[name for name,h in inputs.items() if h!=sha(a.base/name)]
    assert changed==['sink-program.hex']
    assert len((a.out/'sink-program.hex').read_text().splitlines())==5120
    (a.out/'inputs665.json').write_text(json.dumps(dict(inputs=inputs,changed=changed,
        base_SOF=sha(a.base/'output_files/board.sof'),client=sha(a.client/'sink165.sfc')),indent=2)+'\n')
    print(len(inputs),'inputs; ROM contents only')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','out','client','old-client'):p.add_argument('--'+k,type=Path,required=True)
    prepare(p.parse_args())
