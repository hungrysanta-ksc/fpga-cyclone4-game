# SPDX-License-Identifier: MIT
"""Materialize a clean Quartus board or the same-width MMC533 firmware labels."""
import argparse
import json
import shutil
from pathlib import Path
from package_nes_window516 import LABELS, ROOT, read, sha


def board(src,client,out):
    old=read(ROOT/'analysis/map526-verification.json')['builds']['row254']
    selected=read(ROOT/'analysis/tile532-verification.json')
    assert selected['target_met']['pair'] and sha(client/'sink165.sfc')==selected['clients']['pair']['sha256']
    assert sha(src/'output_files/board.sof')==old['SOF']
    assert sha(src/'sink-program.hex')==old['board']['report_SHA256']['sink-program.hex']
    names=[*read(ROOT/'analysis/capture502-verification.json')['FPGA']['whole_board_inputs'],'board.qpf','nominal204.sdc','timing506.tcl']
    assert len(set(names))==73
    for n in names:
        dst=out/n
        dst.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile((client if n=='sink-program.hex' else src)/n,dst)
    assert [n for n in names if sha(src/n)!=sha(out/n)]==['sink-program.hex']
    (out/'inputs533.json').write_text(json.dumps({n:sha(out/n) for n in names},indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('board','labels'))
    for n in ('src','out','client'):p.add_argument('--'+n,type=Path,required=n!='client')
    a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False)
    if a.mode=='board':board(a.src,a.client,a.out)
    else:
        assert sha(a.src/'obj-nes-100/firmware.stm')==read(ROOT/'analysis/tile532-verification.json')['ARM']
        for n in LABELS:
            s=(a.src/n).read_text()
            assert '529' in s
            (a.out/n).write_text(s.replace('529','533'),newline='\n')
