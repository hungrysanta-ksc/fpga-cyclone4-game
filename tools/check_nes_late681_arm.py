"""Linked M4: query BG during warm map runs; retain OBJ credit-only priority."""
import argparse,json,struct
from pathlib import Path
from check_nes_handoff678 import Handoff
from check_nes_supply485_arm import crc,sha


def check(src,case):
    m=Handoff(src,'normal');m.setup();kind=int(case=='OBJ');sent=2
    for k,v,n in [('ending',1,1),('started',1,1),('generation',907,2),('bank_history',2,1),('bulk_valid',1,1)]:m.put(m.p,'nes_plan200',k,v,n)
    old=bytes((1,kind))+struct.pack('<HHHI',32,32 if case=='BG_nonzero' else 0,907,1)
    m.u.mem_write(m.p+m.layout['nes_plan200']['bulk'],old)
    for k,v,n in [('sent',sent,2),('retired',sent-1,2),('ever_sent',1,1),('wait',m.callback|1,4)]:m.put(m.w,'nes_sink_window184',k,v,n)
    last=bytes((2,2))+struct.pack('<HIH',1,1,907)
    m.u.mem_write(m.w+m.layout['nes_sink_window184']['last'],last)
    m.put(m.s,'nes_native_sink165','sequence',2,2)
    if case=='STOP':m.endpoint.mode='STOP_after_bulk';m.endpoint.bulk=1
    def exchange(tx,clock):
        m.ops.append(tx[0]);r=bytearray(len(tx))
        if tx[0]==0xe8:
            r[1:3]=bytes((0xd7,4));r[6:18]=bytes((1,0))+struct.pack('<HHHI',48,32,907,2)
            r[19]=crc(r[1:19],8,7,0)^(case=='CRC')
        elif tx[0]==0xe0:
            r[1:3]=bytes((0xf7,2));r[3:7]=struct.pack('>HH',sent,sent)
            r[7:19]=bytes((0,2))+last[2:]+bytes((0x65,0x9a));r[19]=crc(r[1:19],8,7,0)
        elif tx[0]==0xe1:
            assert tx[1:3]==bytes((7,0)) and tx[17:21]==struct.pack('<I',2)
            assert crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],'big')
        else:raise AssertionError(tx.hex())
        return bytes(r)
    m.endpoint.exchange=exchange;ok=m.call('nes_plan200_progress',[m.p,2])
    assert bool(ok)==(case in ('BG','BG_nonzero','OBJ')),(case,ok,m.ops)
    assert m.ops=={'BG':[0xe8,0xe0,0xe1],'BG_nonzero':[],'OBJ':[],'CRC':[0xe8],'STOP':[]}[case],(case,m.ops)
    assert m.reasons==([4] if case=='BG' else []),(case,m.reasons)
    assert not m.get(m.s,'nes_native_sink165','displayed')
    assert not m.call('nes_plan200_retire',[m.p]) and not m.endpoint.rearmed
    return dict(case=case,success=bool(ok),operations=m.ops,input_callbacks=m.reasons,final_ACK_required=True)


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--arm',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--zero-boundary',action='store_true');a=p.parse_args()
    rows=[check(a.arm,c) for c in (('BG','BG_nonzero','OBJ','CRC','STOP') if a.zero_boundary else ('BG','OBJ','CRC','STOP'))]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows),indent=2)+'\n')
    print('PASS681',len(rows),'linked BG/OBJ/CRC/STOP warm-map cases')
