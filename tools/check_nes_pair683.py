"""Real linked map producer/window; modeled checked consumer and ROM producer."""
import argparse,json,struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha

def run(src,case,early_pair=False,handoff=False):
    m=ARM(src,'normal');m.setup()
    for k,v,n in [('ending',int(case!='early_planner' and not case.startswith('handoff')),1),('started',1,1),('generation',907,2),('bank_history',0 if case in ('cold','early_cold','handoff_cold') else 2,1)]:m.put(m.p,'nes_plan200',k,v,n)
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    data=bytes((i*37+i//13)&255 for i in range(4096))
    m.u.mem_write(m.video+m.layout['nes_native_video165']['map'],data)
    groups={'gap':[0,1,2,4,5,6],'short':[0,1,2,3,4],'three':[0,1,2,3,4,5,6,7,8],
            'early_long':list(range(9)), 'early_gap':[0,1,2,4,5,6],
            'handoff_gap':[0,1,2,4,5,6],'handoff_short':list(range(5)),
            'credit':list(range(18)),'bad_credit':list(range(18)),'bad_identity':list(range(18))}.get(case,list(range(6)))
    mask=sum(1<<i for i in groups);ops=[];payload=[];sent=retired=0;last=bytes(12);queries=[]
    if case in ('early_credit','early_bad_credit','handoff_credit'):
        sent=3
        m.put(m.w,'nes_sink_window184','sent',3,2);m.put(m.w,'nes_sink_window184','ever_sent',1,1)
        m.put(m.s,'nes_native_sink165','sequence',3,2)
    def exchange(tx,clock):
        nonlocal sent,retired,last
        ops.append(tx[0]);r=bytearray(len(tx))
        if tx[0]==0xe8:
            queries.append(len(payload));r[1:3]=bytes((0xd7,4));r[19]=crc(r[1:19],8,7,0)^(case=='bad_plan')
        elif tx[0]==0xe1:
            assert sent-retired<4 and crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            b=tx[1:-2];assert b[0]==2 and b[1]==2 and int.from_bytes(b[2:4],'little')==sent
            at=int.from_bytes(b[10:12],'little');n=int.from_bytes(b[12:14],'little')
            assert b[16:]==data[at:at+n]
            payload.append((at,n));sent+=1;last=bytes((0,b[0]))+b[2:10]+bytes((0x65,0x9a))
            if case in ('STOP','early_STOP','handoff_STOP'):m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
        elif tx[0]==0xe0:
            retired=sent;r[1:3]=bytes((0xf7,2));r[3:7]=struct.pack('>HH',sent,retired);r[7:19]=last
            if case=='bad_identity':r[10]^=1
            r[19]=crc(r[1:19],8,7,0)^(case in ('bad_credit','early_bad_credit'))
        else:raise AssertionError(tx.hex())
        return bytes(r)
    m.endpoint.exchange=exchange
    early=case.startswith(('early','handoff'))
    ok=m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,int(early)])
    if case.startswith('handoff'):
        assert ok and payload==[(0,192)] and m.get(m.s,'nes_native_sink165','map_next')==3
        assert m.get(m.s,'nes_native_sink165','map_pair683')
        m.put(m.p,'nes_plan200','ending',1,1)
        if case=='handoff_tile':m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes((7,0)))
        ok=m.call('map527',[m.s,m.video,mask&0xffffffff,mask>>32,0]);early=False
        assert not m.get(m.s,'nes_native_sink165','map_pair683')
    if case=='bad_identity':
        # Credit consumes the FPGA-checked retire count; the complete identity
        # is compared by the existing drain/through boundary, not credit().
        assert ok
        ok=m.call('nes_window184_drain',[m.w,m.q])
    positive=case not in ('STOP','bad_plan','bad_credit','bad_identity','early_STOP','early_bad_credit','handoff_STOP')
    assert bool(ok)==positive,(case,ok,ops,payload)
    expected={'pair':[0],'cold':[0,1],'gap':[0,1],'short':[0,1],'three':[0,2],
              'early':[],'STOP':[0],'bad_plan':[0],'credit':[0,2,4],'bad_credit':[0,2,4],
              'bad_identity':[0,2,4]}.get(case,[])
    if (early_pair or handoff) and not early:
        expected=list(range(6 if case in ('credit','bad_identity') else 5 if case=='bad_credit' else 3 if case=='three' else 1 if case in ('STOP','bad_plan') else 2))
    if case.startswith('handoff'):expected=[1] if case in ('handoff_gap','handoff_short','handoff_tile','handoff_cold') else []
    assert queries==expected,(case,queries,expected)
    if positive:
        actual=b''.join(data[o:o+n] for o,n in payload)
        early_count=6 if early_pair and case in ('early','early_long','early_credit') else 3
        expected_bytes=b''.join(data[g*64:g*64+64] for g in (groups[:early_count] if early else groups))
        assert actual==expected_bytes
        if early:assert m.get(m.s,'nes_native_sink165','map_next')==early_count
    if case=='STOP':assert len(payload)==1
    if case=='handoff_STOP':assert len(payload)==1
    if case in ('early_STOP','early_bad_credit'):assert len(payload)==1 and m.get(m.s,'nes_native_sink165','map_next')==3
    if case=='bad_plan':assert not payload
    if case=='bad_credit':assert len(payload)==4
    if case=='bad_identity':assert len(payload)==6
    # Submitting/retiring map cannot authorize final display or EA.
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,passed=True,producer_queries_before_packet=queries,packets=payload,operations=ops,
                independent_payload_checked=True,final_ACK_required=True,instructions=m.instructions)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--early-pair',action='store_true');p.add_argument('--handoff',action='store_true');a=p.parse_args()
    cases=['pair','cold','gap','short','three','early','early_long','early_cold','early_planner','early_gap','STOP','bad_plan','credit','bad_credit','bad_identity']
    if a.early_pair:cases+=['early_STOP','early_credit','early_bad_credit']
    if a.handoff:cases+=['handoff','handoff_gap','handoff_short','handoff_tile','handoff_cold','handoff_STOP','handoff_credit']
    rows=[run(a.arm,c,a.early_pair,a.handoff) for c in cases]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows),indent=2)+'\n')
    print('PASS683',len(rows),'linked map ordering/credit/STOP/CRC/identity cases')
