"""Isolated linked192B enqueue+room instruction cost, not a frame-time model."""
import argparse,json
from pathlib import Path
from check_nes_credit709_arm import machine,seed,send,packet
from nes_raw506 import sha

def run(a):
    rows={};pins={}
    for name,src in [('base',a.base),('all',a.probe/'arm01/src'),('needed',a.probe/'arm-needed01/src')]:
        out=[];pins[name]=sha(src/'obj-nes-100/firmware.stm')
        for pending in (0,2):
            m=machine(src);seed(m)
            if pending:m.put(m.w,'nes_sink_window184','retired',65535,2)
            before=m.instructions;start=len(m.endpoint.calls)
            assert send(m,packet(n=192,seq=1));tx=m.instructions-before
            assert m.call('nes_window532_room',[m.w,m.q+400])
            out.append(dict(pending_before=pending,enqueue_instructions=tx,
                enqueue_plus_room_instructions=m.instructions-before,SPI=m.endpoint.calls[start:]))
        rows[name]=out
    r=dict(scope=__doc__,firmware=pins,rows=rows)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('base','probe','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
