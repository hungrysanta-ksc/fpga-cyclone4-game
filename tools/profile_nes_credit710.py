"""Linked enqueue/room instruction costs including unchanged retired replies."""
import argparse,json
from pathlib import Path
from check_nes_credit709_arm import machine,seed,send,packet
from nes_raw506 import sha

def run(a):
    rows={};pins={}
    for name,src in [('base',a.probe.parent/'nes-longrun694/arm01/src'),
        ('709_needed',a.probe.parent/'nes-credit709/arm-needed01/src'),('710',a.probe/'arm01/src')]:
        out=[];pins[name]=sha(src/'obj-nes-100/firmware.stm')
        for scenario in ('no_need','unchanged','advanced'):
            m=machine(src);seed(m)
            if scenario=='advanced':m.put(m.w,'nes_sink_window184','retired',65535,2)
            if scenario=='unchanged':
                m.put(m.w,'nes_sink_window184','sent',3,2);m.endpoint.sent=3
                m.endpoint.pending=[packet(seq=1),packet(seq=2)]
            before=m.instructions;start=len(m.endpoint.calls)
            assert send(m,packet(n=192,seq=3 if scenario=='unchanged' else 1));tx=m.instructions-before
            assert m.call('nes_window532_room',[m.w,m.q+400])
            out.append(dict(scenario=scenario,enqueue_instructions=tx,
                enqueue_plus_room_instructions=m.instructions-before,SPI=m.endpoint.calls[start:]))
        rows[name]=out
    r=dict(scope=__doc__,firmware=pins,rows=rows)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('probe','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
