"""Join same-image ARM evidence and price the whole firmware."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import sha
from analyze_nes_ownership585 import inventory

ROOT=Path(__file__).resolve().parents[1]

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('arm','receiver','display','out'):p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args()
    r=json.loads(a.receiver.read_text())
    ack=json.loads(a.display.read_text())
    prior=json.loads((ROOT/'analysis/roles591-verification.json').read_text())
    fw=a.arm/'obj-nes-100/firmware.stm'
    assert sha(a.arm/'obj-nes-100/sd2snes.elf')==r['pins']['sd2snes.elf']==ack['ELF']
    assert fw.stat().st_size==r['firmware_B'] and sha(fw)==r['pins'][fw.name]
    assert r['cold905_ordered_map_bytes_read']==1914 and len(r['frames'])==53
    assert len(r['guards'])==27 and len(ack['guards'])==3
    r['display']=ack
    r['product']='MMC577'
    r['cap_B']=212992
    r['Flash_excess_B']=r['firmware_B']-r['cap_B']
    r['net_removed_from591_B']=prior['linked_cost']['591']['firmware_B']-r['firmware_B']
    r['reference_groups']={key:{v:val[v] for v in ('577','591')} for key,val in prior['groups'].items()}
    layout=inventory(a.arm)
    r['memory']=dict(receiver_B=layout['structs']['nes_native165']['size_B'],
                     caller_frame_B=layout['stack_frames_B']['native_frames222.isra'],
                     before_callees_and_IRQ_B=layout['gap_before_callees_IRQ_B'])
    r['receiver_symbols_B']=layout['modules']['nes_native165']
    assert not {'logical_record','record','canonical591','request591'}.intersection(r['receiver_symbols_B'])
    r['source_hashes']={n:sha(a.arm/n) for n in ('nes_native165.c','nes_native165.h','nes_native_runtime165.c','nes_native_sink165.c','nes_plan_service200.c')}
    r['tool_hashes']={n:sha(ROOT/'tools'/n) for n in ('nes_decode593.inc','nes_transport593.inc','prepare_nes_receiver593.py','check_nes_receiver593.py','check_nes_ack593.py','report_nes_receiver593.py','build_nes_trial577.ps1')}
    a.out.write_bytes((json.dumps(r,indent=2)+'\n').encode())
    print(r['firmware_B'],r['Flash_excess_B'],r['net_removed_from591_B'],r['groups']['cold905'],r['memory'])
if __name__=='__main__':main()
