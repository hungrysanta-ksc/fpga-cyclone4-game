# SPDX-License-Identifier: MIT
"""Atomic emulator DMA must neither stall ARM nor publish a future receipt."""
import argparse,json
from pathlib import Path
from types import SimpleNamespace
from test_nes_raw506_joint import Link

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    link=Link.__new__(Link);link.a=a;link.sequence=0;link.max_rounding=0;link.future=[];link.retired=0;link.last=bytes(12);link.jobs=[dict(token=7)];link.producer_clock=0
    times=[];link.advance=lambda t:times.append(t);ack=bytes([1,3,4,0,1,0,0,0,9,0,0x65,0x9a])
    for seq in range(1,4):
        text='140\n1\n'+ack.hex()+'\n'+('7:120;'if seq==1 else '')+'\n'+('1:140:'+ack.hex()+';'if seq==1 else '')+'\n'
        (a.out/f'reply-{seq}.txt').write_text(text)
    assert link.rpc(100)==100 and link.retired==0 and len(link.jobs)==1 and times==[100]
    assert link.rpc(125)==125 and link.retired==0 and not link.jobs and link.last==bytes(12)
    assert link.rpc(140)==140 and link.retired==1 and link.last==ack and not link.future
    report=dict(passed=True,scope=__doc__,DMA_atomic_overshoot=40,ARM_stall_added=0,consume_visible_at=120,final_ACK_visible_at=140)
    (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
