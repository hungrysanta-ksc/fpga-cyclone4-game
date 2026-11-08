"""Execute bounded map admission, ownership, queue reservation and STOP in linked M4."""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha

def setup(src,case,used,age,sent=100):
    m=ARM(src,'normal');m.setup();ops=[]
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bulk_pending',1,1),('bulk_valid',1,1),('bulk_until',(sent-age)&65535,2)]:m.put(m.p,'nes_plan200',k,v,n)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    for k,v,n in [('sent',sent,2),('retired',(sent-used)&65535,2)]:m.put(m.w,'nes_sink_window184',k,v,n)
    if case=='no_bulk':m.put(m.p,'nes_plan200','bulk_pending',0,1)
    if case=='error':m.put(m.p,'nes_plan200','error',3,1)
    if case=='identity':m.put(m.p,'nes_plan200','generation',908,2)
    if case=='STOP':m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
    def exchange(tx,clock):
        ops.append(tx.hex())
        if tx[0]==0xe1:assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
        # Any fallback must consult actual producer; inject invalid E8 there.
        # No completion ACK or producer credit is fabricated by this unit.
        return bytes(len(tx))
    m.endpoint.exchange=exchange
    return m,ops

def check(src,case,used=1,age=0,sent=100,mode=2):
    m,ops=setup(src,case,used,age,sent)
    before=bytes(m.u.mem_read(m.p+m.layout['nes_plan200']['bulk'],12))
    ok=m.call('nes_plan200_progress',[m.p,mode])
    fast=mode==2 and used<3 and age<3 and case not in ('no_bulk','error','identity','STOP')
    assert bool(ok)==fast,(case,used,age,ok)
    assert not ops if fast or case in ('error','identity','STOP') else len(ops)==1 and bytes.fromhex(ops[0])[0]==0xe8
    assert bytes(m.u.mem_read(m.p+m.layout['nes_plan200']['bulk'],12))==before
    assert m.get(m.p,'nes_plan200','bulk_until',2)==(sent-age)&65535
    assert m.get(m.p,'nes_plan200','bulk_pending')==int(case!='no_bulk')
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,used=used,age=age,sent=sent,mode=mode,fast=fast,ops=ops)

def suffix(src,sent):
    m,ops=setup(src,'suffix',1,0,sent);data=bytes(i%251 for i in range(192));m.u.mem_write(m.q,data)
    for offset in (2048,2240):assert m.call('packet_wire',[m.s,2,2,offset,m.q,len(data),0])
    assert len(ops)==2 and all(bytes.fromhex(x)[0]==0xe1 for x in ops)
    assert (m.get(m.w,'nes_sink_window184','sent',2)-m.get(m.w,'nes_sink_window184','retired',2))&65535==3
    assert not m.call('packet_wire',[m.s,2,2,2432,m.q,len(data),0])
    assert len(ops)==3 and bytes.fromhex(ops[-1])[0]==0xe8
    assert m.get(m.p,'nes_plan200','bulk_pending') and not m.get(m.s,'nes_native_sink165','displayed')
    return dict(sent=sent,map_packets=2,reserved_slots=1,third_requires_producer=True,token_still_owned=True)

def deferred_fault(src,case):
    m,ops=setup(src,'deferred',1,0);data=bytes(i%251 for i in range(192));m.u.mem_write(m.q,data)
    for offset in (2048,2240):assert m.call('packet_wire',[m.s,2,2,offset,m.q,len(data),0])
    def exchange(tx,clock):
        ops.append(tx.hex());r=bytearray(len(tx))
        if tx[0]==0xe8:
            r[1:4]=bytes((0xd7,4,0));r[6:18]=bytes((1,1))+struct.pack('<HHHI',0,32,907,1)
        elif tx[0]==0xe0:
            r[1:3]=bytes((0xf7,2));r[3:7]=struct.pack('>HH',101 if case=='credit' else 102,102)
            # Identity remains zero deliberately when empty: it must be checked.
        else:raise AssertionError(tx[0])
        r[19]=crc(r[1:19],8,7,0)^(tx[0]==0xe0 and case=='CRC')
        return bytes(r)
    m.endpoint.exchange=exchange
    assert not m.call('packet_wire',[m.s,2,2,2432,m.q,len(data),0])
    assert [bytes.fromhex(x)[0] for x in ops]==[0xe1,0xe1,0xe8,0xe0]
    assert m.get(m.p,'nes_plan200','bulk_pending') and not m.get(m.s,'nes_native_sink165','displayed')
    return dict(case=case,map_packets=2,window_error=m.get(m.w,'nes_sink_window184','error'),bulk_still_owned=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=[check(a.arm,'normal',u,b) for u,b in ((1,0),(2,1),(2,2),(3,2),(4,2),(2,3))]
    rows += [check(a.arm,c) for c in ('no_bulk','error','identity','STOP')]
    rows += [check(a.arm,'ordinary',mode=0),check(a.arm,'FINAL',mode=1),check(a.arm,'wrap',2,1,0)]
    r=dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,suffix=[suffix(a.arm,x) for x in (100,65535)],deferred=[deferred_fault(a.arm,c) for c in ('CRC','credit','identity')],scope='Linked ARM, two actual E1 map packets and reserved fourth credit; fallback and deferred E0 errors are rejected, not synthetic successful completion.')
    a.out.write_text(json.dumps(r,indent=2)+'\n',newline='\n');print('PASS677',len(rows),'admission,2 bounded suffix and3 deferred completion fault cases')
