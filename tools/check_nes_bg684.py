"""Linked BG-complete offer, with independent payload/credit checking."""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha
from check_nes_pair683 import run as old

def run(src,case):
    m=ARM(src,'normal');m.setup()
    for k,v,n in [('ending',0,1),('started',1,1),('generation',907,2),('bank_history',2,1)]:m.put(m.p,'nes_plan200',k,v,n)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    groups={'gap':[0,1,2,4,5,6],'short':list(range(5))}.get(case,list(range(9)))
    mask=sum(1<<g for g in groups);data=bytes((i*37+i//13)&255 for i in range(4096))
    m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],data)
    m.put(m.video,'nes_native_video165','map_dirty',mask,8)
    m.put(m.resident,'nes_resident211','target',0,1)
    m.u.mem_write(m.resident+m.layout['nes_resident211']['map_stale'],bytes(16))
    ops=[];payload=[];sent=retired=0;last=bytes(12)
    def exchange(tx,clock):
        nonlocal sent,retired,last
        ops.append(tx[0]);r=bytearray(len(tx))
        if tx[0]==0xe8:
            r[1:3]=bytes((0xd7,4));r[19]=crc(r[1:19],8,7,0)
        elif tx[0]==0xe1:
            assert sent-retired<4 and crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            b=tx[1:-2];assert b[:2]==bytes((2,2)) and int.from_bytes(b[2:4],'little')==sent
            at=int.from_bytes(b[10:12],'little');n=int.from_bytes(b[12:14],'little')
            assert b[16:]==data[at:at+n];payload.append((at,n));sent+=1
            last=bytes((0,b[0]))+b[2:10]+bytes((0x65,0x9a))
        elif tx[0]==0xe0:
            retired=sent;r[1:3]=bytes((0xf7,2));r[3:7]=struct.pack('>HH',sent,retired);r[7:19]=last
            r[19]=crc(r[1:19],8,7,0)^(case=='bad_credit')
        else:raise AssertionError(tx.hex())
        return bytes(r)
    m.endpoint.exchange=exchange
    assert m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,1])
    assert payload==[(0,192)] and m.get(m.s,'nes_native_sink165','map_next')==3
    if case=='cold':m.put(m.p,'nes_plan200','bank_history',0,1)
    if case in ('tile','ordinary','RLE'):
        m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes({'tile':(7,0),'ordinary':(2,3),'RLE':(9,2)}[case]))
    if case=='no_prefix':m.put(m.s,'nes_native_sink165','map_pair683',0,1)
    if case in ('credit','bad_credit'):
        sent=4;m.put(m.w,'nes_sink_window184','sent',4,2);m.put(m.s,'nes_native_sink165','sequence',4,2)
    if case=='STOP':m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
    before=len(ops)
    ok=m.call('nes_sink527_early',[m.s,m.video,m.resident,1])
    assert bool(ok)==(case not in ('STOP','bad_credit')),(case,ok,ops)
    assert 0xe8 not in ops[before:] and 0xe9 not in ops[before:]
    send=case in ('normal','credit')
    assert payload==([(0,192),(192,192)] if send else [(0,192)]),(case,payload)
    assert m.get(m.s,'nes_native_sink165','map_next')==(6 if send else 3)
    assert not m.get(m.s,'nes_native_sink165','map_pair683')
    if ok:
        m.put(m.p,'nes_plan200','ending',1,1)
        assert m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,0])
        assert b''.join(data[o:o+n] for o,n in payload)==b''.join(data[g*64:g*64+64] for g in groups)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,passed=True,packets=payload,operations=ops,final_ACK_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    prior=['pair','cold','gap','short','three','early','early_long','early_cold','early_planner','early_gap','STOP','bad_plan','credit','bad_credit','bad_identity','handoff','handoff_gap','handoff_short','handoff_tile','handoff_cold','handoff_STOP','handoff_credit']
    rows=[old(a.arm,c,handoff=True) for c in prior]
    rows += [run(a.arm,c) for c in ('normal','cold','tile','ordinary','RLE','gap','short','no_prefix','credit','bad_credit','STOP')]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows),indent=2)+'\n')
    print('PASS684',len(rows),'linked ordering, payload, credit, STOP and final ACK cases')
