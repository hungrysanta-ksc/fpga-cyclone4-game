"""Package only the routed, linked MMC1010 limited timing observer."""
import argparse
import json
import re
from pathlib import Path
from types import SimpleNamespace

from analyze_nes_display1010 import sha, summarize
from nes_display1010 import ROOT, QUARTUS
from package_nes_trial704 import decode, digest, image
from package_nes_trial872 import write_verified_archive
from prepare_nes_display1010_arm import PROBE

def package(temp):
    ref=json.loads((ROOT/'analysis/trial966-package.json').read_bytes())
    evidence=summarize(temp)
    assert evidence==json.loads((ROOT/'analysis/display1010-results.json').read_bytes())
    assert evidence['positive_STA']
    board=temp/'nes-display1010-boardD'
    out=temp/'nes-display1010-image'
    if not (out/'image.json').is_file():
        image(SimpleNamespace(board=board,quartus=QUARTUS,out=out,number='1010'))
    img=json.loads((out/'image.json').read_bytes())
    packed=(out/'fpga_mmc1010.bi3').read_bytes()
    assert img['SOF']==sha(board/'output_files/board.sof')==sha(out/'board.sof')
    assert img['programmer']['passed'] and digest(packed)==img['BI3']==img['programmer']['image_sha256']
    assert digest(decode(packed))==img['RBF']==img['programmer']['rbf_sha256']
    mif,=(board/'db').glob('board.ram*_nes_sink_bus165_*.hdl.mif')
    cells=sorted((int(i),int(v,2)) for i,v in re.findall(r'^\s*(\d+)\s*:\s*([01]{8});',mif.read_text(),re.M))
    assert [i for i,v in cells]==list(range(5120))
    rom=(temp/'nes-display1010-ppu-p1/client.sfc').read_bytes()
    assert digest(rom)==ref['client']
    assert bytes(v for i,v in cells)==rom[:5056]+rom[-64:]==bytes.fromhex((board/'sink-program.hex').read_text())
    firmware=(PROBE/'src/obj-nes-100/firmware.stm').read_bytes()
    report=dict(edition=1010,reference='MMC966',physical=False,firmware=digest(firmware),
                flash_B=len(firmware),client=digest(rom),compiled_MIF=sha(mif),image=img,
                diagnostic='55-60 s display/retirement observer',evidence=evidence)
    write_verified_archive(PROBE.parent,ref,firmware,packed,report)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('temp',type=Path)
    package(p.parse_args().temp)
