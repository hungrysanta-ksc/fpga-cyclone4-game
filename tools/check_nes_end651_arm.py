"""Drive the linked END scheduler with E8 readiness and tile ownership independently varied."""
import argparse
import json
import struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha


def check(src,policy,case):
    m=ARM(src,"normal");m.setup()
    gen=955
    m.put(m.s,"nes_native_sink165","generation",gen,2)
    for k,v,n in (("generation",gen,2),("started",1,1),("poll_limit",8,4)):
        m.put(m.p,"nes_plan200",k,v,n)
    desc=bytes((1,0))+struct.pack("<HHHI",16,48,gen,37)
    if case=="mutated":
        m.put(m.p,"nes_plan200","bulk_valid",1,1)
        m.u.mem_write(m.p+m.layout["nes_plan200"]["bulk"],desc[:4]+bytes((32,0))+desc[6:])
    ops=[]
    sent=end=0
    last=bytes(12)
    def send(tx,clock):
        nonlocal sent,end,last
        op=tx[0];ops.append(op)
        r=bytearray(len(tx))
        if op==0xe8:
            r[1:4]=bytes((0xd7,4,2 if end else int(case not in ("busy","repeat") or sent)))
            r[4:6]=end.to_bytes(2,"big")
            if not end and (not sent or (case=="repeat" and ops.count(0xe8)==2)):
                r[6:18]=desc
                if case=="wrong_generation":r[12]^=1
            r[19]=crc(r[1:19],8,7,0)^(case=="CRC")
        elif op==0xe1:
            assert not sent and not end and tx[1]==7 and tx[17:21]==desc[8:]
            assert int.from_bytes(tx[-2:],"big")==crc(tx[:-2],16,0x1021,65535)
            last=bytes((0,7))+tx[3:11]+bytes((0x65,0x9a));sent=1
            m.endpoint.bulk=1
            if case=="STOP":m.endpoint.mode="STOP_after_bulk"
            if case=="ambiguous":m.endpoint.mode="ambiguous_E1"
        elif op==0xe9:
            assert sent==1 and not end and tx[1:7]==bytes((3,0,1,0x83,gen&255,gen>>8))
            assert tx[7:9]==crc(tx[4:7],16,0x1021,65535).to_bytes(2,"big")
            assert tx[9]==crc(tx[:9],8,7,0) and tx[10]==0xa5
            end=1
        elif op==0xe0:
            r[1:3]=bytes((0xf7,2));r[3:7]=struct.pack(">HH",sent,sent);r[7:19]=last
            r[19]=crc(r[1:19],8,7,0)
        else:raise AssertionError(op)
        return bytes(r)
    m.endpoint.exchange=send
    ok=m.call("nes_plan200_end",[m.p])
    entry_ops=list(ops)
    if policy=="handoff":
        assert ok and not ops and m.get(m.p,"nes_plan200","count")==1
    if ok:ok=m.call("nes_plan200_progress",[m.p,1])
    success=case in ("ok","busy","repeat")
    assert bool(ok)==bool(end)==success
    if success:
        assert not m.get(m.p,"nes_plan200","bulk_pending")
        assert ops.count(0xe1)==ops.count(0xe9)==1
        assert not m.call("nes_plan200_retire",[m.p])
        if policy=="grant" and case=="ok":assert ops[:3]==[0xe8,0xe1,0xe9]
        else:assert ops[:3]==[0xe8,0xe1,0xe8]
        if policy=="grant" and case=="repeat":assert ops[3]==0xe9
    else:
        assert not m.get(m.s,"nes_native_sink165","displayed")
        before=list(ops);assert not m.call("nes_plan200_progress",[m.p,1]) and before==ops
    return dict(case=case,first_call=entry_ops,operations=ops,END=bool(end),display=False)


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--arm",type=Path,required=True);p.add_argument("--policy",required=True);p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    rows=[check(a.arm,a.policy,c) for c in ("ok","busy","repeat","CRC","wrong_generation","mutated","STOP","ambiguous")]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/"obj-nes-100/firmware.stm"),rows=rows),indent=2)+"\n")
