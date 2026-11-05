"""Bind layout, report compatibility, receiver and ACK checks to one ELF."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import ELFFile, sha

ROOT=Path(__file__).resolve().parents[1]

def read(path):
    return json.loads(path.read_text())

def allocated(path):
    with path.open('rb') as f:
        return {s.name:(s['sh_size'],s.data()) for s in ELFFile(f).iter_sections() if s['sh_flags']&2}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('base','arm','receiver','ack','reports','out'):
        p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    prior=read(ROOT/'analysis/receiver593-verification.json')
    rx,ack,reports=map(read,(a.receiver,a.ack,a.reports))
    pack=read(a.arm.parent/'packing.json')
    old,new=[path/'obj-nes-100' for path in (a.base,a.arm)]
    assert sha(old/'sd2snes.elf')==pack['baseline_ELF']==prior['pins']['sd2snes.elf']==reports['base_ELF']
    assert sha(new/'sd2snes.elf')==rx['pins']['sd2snes.elf']==ack['ELF']==reports['ELF']
    assert sha(new/'firmware.stm')==rx['pins']['firmware.stm']
    assert rx['joint_pass'] and rx['frames']==prior['frames'] and rx['guards']==prior['guards']
    assert ack['guards']==prior['display']['guards'] and len(rx['frames'])==53 and len(rx['guards'])==27
    assert rx['cold905_ordered_map_bytes_read']==1914 and reports['exercised_formats']==pack['formats']
    objects=sorted(q.relative_to(old) for q in old.rglob('*.o'))
    assert objects==sorted(q.relative_to(new) for q in new.rglob('*.o'))
    changed=[path.as_posix() for path in objects if allocated(new/path)!=allocated(old/path)]
    assert set(changed)=={Path(k).with_suffix('.o').name for k in pack['files']},changed
    cap=prior['cap_B']
    size=(new/'firmware.stm').stat().st_size
    assert size==rx['firmware_B'] and size<=cap
    result=dict(stage=594,firmware_B=size,Flash_margin_B=cap-size,cap_B=cap,
                net_removed_from593_B=prior['firmware_B']-size,packing=pack,
                objects_checked=len(objects),allocated_sections_changed=changed,
                input_test=rx,display=ack,report_test=reports,
                new_RTL=False,new_full_timeline=False,product='MMC577',
                scope='Actual whole ARM link and instructions. Mocked peripherals, same driver/CPI model as 593. Report-only extra work and stack measured separately.',
                pins={p.name:sha(p) for p in (a.receiver,a.ack,a.reports,new/'sd2snes.map',ROOT/'tools/check_nes_report594.py',
                                               ROOT/'tools/prepare_nes_report594.py',ROOT/'tools/nes_report594.inc',Path(__file__))})
    a.out.write_bytes((json.dumps(result,indent=2)+'\n').encode())
    print(size,cap-size,changed,len(objects))
if __name__=='__main__':main()
