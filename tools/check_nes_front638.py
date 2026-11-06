# SPDX-License-Identifier: MIT
"""Differential linked receiver checks at each POP and at invalid map record boundaries."""
import argparse
import hashlib
import json
from pathlib import Path
from check_nes_game478 import Machine
from check_nes_supply485_arm import ARM
from nes_raw506 import encode, sha


def image(m):
    return bytes(m.u.mem_read(m.state,m.layout['nes_native165']['size']))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def poll_trace(src,data,g):
    geometry=(data/f'frame{g}.geometry').read_bytes()
    raw=(data/f'frame{g}.raw').read_bytes()
    m=Machine(src,bytes(128))
    m.packets,_,_=encode(geometry,raw,g)
    m.start_token=65530
    m.prepared=False
    m.index=m.spi_calls=0
    history=[]
    while m.index<len(m.packets):
        before=m.instructions
        if m.state_value()==2:
            opcode='prepare'
            ok=m.call('nes_native165_prepare',[m.state,1,m.spi|1,0])
        else:
            opcode='poll'
            ok=m.call('nes_native165_poll',[m.state,m.spi|1,0])
        assert ok==1
        history.append((opcode,m.index,digest(image(m)),m.instructions-before))
    assert m.state_value()==4
    return history


def record(kind,index,value,width,gen=953):
    return ((kind<<13)|index).to_bytes(2,'big')+gen.to_bytes(2,'big')+value.to_bytes(width,'big')


def edge_states(src):
    m=Machine(src,bytes(128))
    layout=m.layout['nes_native165']
    buf=0x2001b000
    repeat=lambda n,v:record(6,0x1000+n-1,v,2)
    literals=lambda index,n,words:record(0,0x1000|index,(n<<60)|words,8)
    cases=[
        ('mixed-attributes',0,literals(0,4,(8193<<45)|(1<<30)|(16385<<15)|32767),True),
        ('tail',32,literals(32,1,2),True),('duplicate-run',1,repeat(32,8193),True),
        ('one-repeat',0,repeat(1,1),False),('past-end',32,repeat(2,1),False),
        ('repeat-width',0,repeat(2,32768),False),('packed-width',32,literals(32,1,1<<15),False),
        ('wrong-start',0,literals(1,4,0),False),('tail-count',32,literals(32,2,0),False),
        ('foreign-owner',0,record(6,0x1001,1,2,gen=952),False),
        ('late-section',0,repeat(2,1),False),('wrong-state',0,repeat(2,1),False),
        ('truncated',0,literals(0,4,0)[:-1],False)]
    results={}
    for label,start,pkt,valid in cases:
        m.call('nes_native165_reset',[m.state])
        for key,value,n in [('state',0 if label=='wrong-state' else 1,1),('generation',953,2),
                            ('counts',33,2),('at',start,2),('next_kind',int(label=='late-section'),1)]:
            m.u.mem_write(m.state+layout[key],value.to_bytes(n,'little'))
        # A previously requested OBJ tag must retain that requirement when also used by BG.
        m.u.mem_write(m.state+layout['required'],bytes([8]))
        m.u.mem_write(m.state+layout['missing'],b'\x01\x00')
        m.u.mem_write(buf,pkt)
        ok=m.call('nes_native165_packet',[m.state,65535,buf,len(pkt)])
        assert bool(ok)==valid,label
        if not valid:assert m.state_value()==5
        results[label]=digest(image(m))
    return results


def first_issue(src,early):
    results={}
    for mode in ('normal','bad_E8_CRC','STOP_after_E9'):
        m=ARM(src,mode)
        m.setup()
        m.put(m.p,'nes_plan200','bank_history',2,1)
        assert m.emit(2,0,0)
        assert m.endpoint.accepted==0
        issued=m.emit(0,119,6542)
        assert bool(issued)==(not early or mode!='bad_E8_CRC')
        expected=int(early and mode!='bad_E8_CRC')
        assert m.endpoint.accepted==expected
        if expected:
            assert m.endpoint.plans==[(0,0,0),(0,119,6542)]
        if early and mode!='normal':
            before=len(m.endpoint.calls)
            assert not m.emit(0,120,6558) and len(m.endpoint.calls)==before
        assert not m.get(m.s,'nes_native_sink165','displayed') and not m.endpoint.rearmed
        results[mode]=dict(accepted=expected,displayed=False)
    return results


def main(a):
    reference=a.base/'src'
    edges=edge_states(reference)
    traces={g:poll_trace(reference,a.data,g) for g in (905,951,952,953,957)}
    modes={}
    for mode in ('receive','both'):
        src=a.build/mode/'src'
        assert edge_states(src)==edges
        costs={}
        for g,old in traces.items():
            new=poll_trace(src,a.data,g)
            assert [r[:3] for r in old]==[r[:3] for r in new]
            costs[g]=dict(base=sum(r[3] for r in old),candidate=sum(r[3] for r in new),
                          block_delta=[n[3]-o[3] for n,o in zip(new,old)])
        modes[mode]=dict(firmware=sha(src/'obj-nes-100/firmware.stm'),instructions=costs)
    first={mode:first_issue(a.build/mode/'src',mode!='receive') for mode in ('receive','first','both')}
    a.out.write_text(json.dumps(dict(edges=edges,modes=modes,first_issue=first),indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('base','build','data','out'):p.add_argument('--'+k,required=True,type=Path)
    main(p.parse_args())
