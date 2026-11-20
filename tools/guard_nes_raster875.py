"""Compare complete receiver state on the linked reference and accelerated ARM."""
import argparse
import json
from pathlib import Path

from check_nes_game478 import Machine, next_y, sha


def exercise(cpu, case):
    layout=cpu.layout['nes_native165']
    gen=952
    start,n,value=case['start'],case['count'],case['value']
    counts=[33,224,2,2,224,case.get('palette',64)]
    cursors=counts[:4]+[start,0]
    if case.get('incomplete'):
        cursors[2]-=1
    state=bytearray(layout['size'])
    def field(name,data):
        state[layout[name]:layout[name]+len(data)]=data
    for name,v in [('counts',counts),('at',cursors)]:
        field(name,b''.join(x.to_bytes(2,'little') for x in v))
    for name,v in [('generation',gen),('records',100),('next_token',17)]:
        field(name,v.to_bytes(2,'little'))
    for name,v in [('state',case.get('state',1)),('next_kind',case.get('kind',2)),('token_valid',1)]:
        field(name,bytes([v]))
    offset=layout['raster']
    state[offset:offset+224*8]=bytes([0xa5])*(224*8)
    cpu.u.mem_write(cpu.state,bytes(state))
    data=(0xfc00+n-1).to_bytes(2,'big')+case.get('wire_gen',gen).to_bytes(2,'big')+value.to_bytes(8,'big')
    buf=cpu.lut+256
    cpu.u.mem_write(buf,data)
    before=cpu.instructions
    status=cpu.call('nes_native165_packet',[cpu.state,case.get('token',17),buf,len(data)])
    actual=bytes(cpu.u.mem_read(cpu.state,len(state)))
    if status:
        raster=bytearray(state[offset:offset+224*8])
        for i in range(start,start+n):
            raster[i*8:i*8+8]=value.to_bytes(8,'little')
            value=next_y(value)
        assert raster==actual[offset:offset+224*8]
    return status,actual,cpu.instructions-before


def check(reference,candidate):
    machines=[Machine(p,bytes(128)) for p in (reference,candidate)]
    cases=[dict(start=start,count=n,value=(1<<44)|(7<<12)|(y<<5)|17)
           for y in (0,29,30,31) for start,n in ((0,224),(1,2),(222,2))]
    valid=len(cases)
    cases.extend(dict(dict(start=0,count=2,value=0),**extra) for extra in (
        {'start':223},{'state':2},{'kind':5},{'wire_gen':951},{'token':16},
        {'incomplete':True},{'count':1},{'value':1<<49},{'value':1<<44,'palette':32}))
    rows=[]
    for i,case in enumerate(cases):
        a,b=[exercise(cpu,case) for cpu in machines]
        assert a[:2]==b[:2] and bool(a[0])==(i<valid),(case,a[0],b[0])
        rows.append(dict(**case,accepted=bool(b[0]),instructions=[a[2],b[2]]))
    return dict(ARM=[sha(p/'obj-nes-100/firmware.stm') for p in (reference,candidate)],cases=rows)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('reference','candidate','out'):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    a.out.write_text(json.dumps(check(a.reference,a.candidate),indent=2)+'\n')
