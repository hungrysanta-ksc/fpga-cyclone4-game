"""Execute the new advisory status and immutable-fill handoff on linked Cortex M4."""
import argparse,json,struct
from pathlib import Path
from check_nes_handoff678 import Handoff,run as prior
from check_nes_supply485_arm import crc,sha


def check(src,case):
    m=Handoff(src,'normal');m.setup();sent=2
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bank_history',2,1),('bulk_valid',1,1)]:m.put(m.p,'nes_plan200',k,v,n)
    old=bytes((1,0))+struct.pack('<HHHI',16,0,907,1)
    m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],old)
    for k,v,n in [('sent',sent,2),('retired',sent-1,2),('ever_sent',1,1),('wait',m.callback|1,4)]:m.put(m.w,'nes_sink_window184',k,v,n)
    last=bytes((5,5))+struct.pack('<HIH',1,1,907)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    m.put(m.s,'nes_native_sink165','sequence',2,2)
    def exchange(tx,clock):
        m.ops.append(tx[0]);r=bytearray(len(tx))
        if tx[0]==0xe8:
            r[1:3]=bytes((0xd7,4));r[6:18]=bytes((1,1))+struct.pack('<HHHI',32,32,907,2)
            r[19]=crc(r[1:19],8,7,0)
        elif tx[0]==0xe0:
            flags={'absent':2,'live':11,'no_ACK':8,'reserved':26}.get(case,10)
            r[1:3]=bytes((0xf7,flags));r[3:7]=struct.pack('>HH',sent,sent)
            r[7:19]=bytes((0,5))+last[2:]+bytes((0x65,0x9a))
            if case=='identity':r[10]^=1
            if case=='credit':r[6]=1
            if case=='fake_final':r[7]=1
            r[19]=crc(r[1:19],8,7,0)^(case=='CRC')
            if case=='STOP':m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
        elif tx[0]==0xe1:
            assert tx[1]==7 and tx[2]==1
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
        else:raise AssertionError(tx.hex())
        return bytes(r)
    m.endpoint.exchange=exchange
    ok=m.call('nes_plan200_progress',[m.p,0])
    assert bool(ok)==(case in ('present','absent')),(case,ok,m.ops)
    assert m.reasons==([4] if case=='absent' else []),(case,m.reasons)
    assert (0xe1 in m.ops)==bool(ok)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,passed=bool(ok),operations=m.ops,input_callbacks=m.reasons,final_ACK_still_required=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    cases=[check(a.arm,c) for c in ('present','absent','live','no_ACK','reserved','identity','credit','fake_final','CRC','STOP')]
    old=[prior(a.arm,c) for c in ('normal','cold','last_tile','repeat','generation','bad_E8_CRC','credit','identity','bad_E0_CRC','failed_input','STOP_after_input','single_BG','single_OBJ','multi_OBJ')]
    old.append(prior(a.arm,'normal',65535));old += [prior(a.arm,c,flush=True) for c in ('normal','last_tile','STOP_after_input')]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),progress=cases,prior=old),indent=2)+'\n')
    print('PASS680 ARM',len(cases),'new and',len(old),'retained cases')
