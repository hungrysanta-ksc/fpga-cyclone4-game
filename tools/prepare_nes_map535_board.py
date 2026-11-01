# SPDX-License-Identifier: MIT
"""Build the 535 whole board from the exact 73 MMC533 inputs, replacing only the mapped 65816 ROM."""
import argparse
import json
import shutil
from pathlib import Path
from package_nes_window516 import ROOT,read,sha

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('reference','client','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    ref=read(ROOT/'analysis/trial533-verification.json')
    assert sha(a.reference/'output_files/board.sof')==ref['SOF_SHA256']
    rom=(a.client/'sink165.sfc').read_bytes()
    assert len(rom)==32768 and bytes.fromhex((a.client/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
    a.out.mkdir(parents=True,exist_ok=False)
    inputs={}
    for n,h in ref['inputs'].items():
        assert sha(a.reference/n)==h
        dst=a.out/n;dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile((a.client if n=='sink-program.hex' else a.reference)/n,dst)
        inputs[n]=sha(dst)
    assert [n for n,h in inputs.items() if h!=ref['inputs'][n]]==['sink-program.hex']
    (a.out/'inputs535.json').write_text(json.dumps(inputs,indent=2)+'\n')
