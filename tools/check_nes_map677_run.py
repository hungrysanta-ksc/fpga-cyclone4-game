"""Check completed-bulk ownership and checked queue credit through a warm map run."""
import argparse,json,struct
from pathlib import Path
from check_nes_map677 import setup
from check_nes_supply485_arm import crc,sha

def run(src,case,sent=101):
    m,ops=setup(src,case,2,1,sent)
    m.put(m.p,'nes_plan200','bank_history',0 if case=='cold' else 2,1)
    m.put(m.w,'nes_sink_window184','ever_sent',1,1)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],bytes((2,1 if case=='last_tile' else 2))+struct.pack('<HIH',1,1,907))
    count=0;max_pending=0
    def exchange(tx,clock):
        nonlocal count,max_pending
        ops.append(tx.hex());r=bytearray(len(tx))
        if tx[0]==0xe8:return bytes(r) # fallback intentionally rejects invalid producer response
        if tx[0]==0xe1:
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
            max_pending=max(max_pending,1+((m.get(m.w,'nes_sink_window184','sent',2)-m.get(m.w,'nes_sink_window184','retired',2))&65535))
            return bytes(r)
        assert tx[0]==0xe0;count+=1
        accepted=m.get(m.w,'nes_sink_window184','sent',2)
        retired=m.get(m.p,'nes_plan200','bulk_until',2) if count==1 and case!='identity' else accepted
        used=(accepted-retired)&65535
        r[1:3]=bytes((0xf7,2|int(bool(used))|(4 if used==4 else 0)))
        r[3:7]=struct.pack('>HH',(accepted-int(case=='credit'))&65535,retired)
        last=bytes(m.u.mem_read(m.w+m.layout['nes_sink_window184']['last'],10))
        r[7:19]=bytes((0,last[0]))+last[2:10]+bytes((0x65,0x9a))
        if case=='identity':r[10]^=1
        r[19]=crc(r[1:19],8,7,0)^(case=='CRC' or case=='lateCRC' and count>1)
        return bytes(r)
    m.endpoint.exchange=exchange
    mode=1 if case=='FINAL' else 0 if case=='ordinary' else 2
    ok=m.call('nes_plan200_progress',[m.p,mode]);positive=case in ('normal','lateCRC','STOP_later')
    assert bool(ok)==positive,(case,ok,ops)
    if positive:
        assert len(ops)==1 and bytes.fromhex(ops[0])[0]==0xe0
        assert not m.get(m.p,'nes_plan200','bulk_pending') and m.get(m.p,'nes_plan200','bulk_valid')
        data=bytes(i%251 for i in range(192));m.u.mem_write(m.q,data);issued=0
        for i in range(7):
            if case=='STOP_later' and i==1:m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
            ok=m.call('packet_wire',[m.s,2,2,2048+192*i,m.q,len(data),0])
            if not ok:break
            issued+=1
        assert issued=={'normal':7,'lateCRC':3,'STOP_later':1}[case],(case,issued)
        assert not any(bytes.fromhex(x)[0] in (0xe8,0xea) for x in ops)
        assert max_pending<=4
    else:
        assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,sent=sent,operations=[bytes.fromhex(x)[0] for x in ops],max_pending=max_pending,
        plan_error=m.get(m.p,'nes_plan200','error'),window_error=m.get(m.w,'nes_sink_window184','error'),final_ACK_required=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    rows=[run(a.arm,c) for c in ('normal','lateCRC','STOP_later','CRC','credit','identity','STOP','error','cold','last_tile','FINAL','ordinary')]
    rows.append(run(a.arm,'normal',65535))
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope='Actual M4; modeled independently checked E0 completion/credit. Seven map E1s with four-credit cap, no fabricated display ACK.'),indent=2)+'\n',newline='\n')
    print('PASS677 run',len(rows),'ownership/credit/STOP/CRC/cold/wrap cases')
