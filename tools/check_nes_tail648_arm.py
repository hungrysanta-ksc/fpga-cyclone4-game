"""Execute the linked SEAL barrier against delayed ordinary and display receipts."""
import argparse
import json
import struct
from pathlib import Path
from check_nes_supply485_arm import ARM,crc,sha


def trial(src,case):
    m=ARM(src,"normal")
    m.setup()
    w="nes_sink_window184"
    full=case=="full"
    sent=65535 if case=="wrap" else 123
    retired=(sent-(4 if full else 1))&65535
    seal=bytes((3,0))+struct.pack("<HIHHHH",17,51,955,0,168,0)+bytes(168)
    tail=bytes((2,5))+struct.pack("<HIH",16,51,955)
    for name,num,width in (("sent",sent,2),("retired",retired,2),("ever_sent",1,1),("poll_limit",8,4)):
        m.put(m.w,w,name,num,width)
    m.u.mem_write(m.w+m.layout[w]["last"],tail)
    m.u.mem_write(m.q,seal)
    operations=[]
    queued=False
    after=0
    def exchange(tx,clock):
        nonlocal queued,sent,retired,after
        operations.append(tx[0])
        if tx[0]==0xe1:
            outstanding=(sent-retired)&65535
            assert not queued and 0<outstanding<4
            assert tx[1:-2]==seal and crc(tx[:-2],16,0x1021,65535)==int.from_bytes(tx[-2:],"big")
            queued=True
            sent=(sent+1)&65535
            if case=="stop":m.endpoint.mode="STOP_after_bulk";m.endpoint.bulk=1
            return bytes(len(tx))
        assert tx[0]==0xe0
        if queued:
            after+=1
            retired=(sent-1)&65535 if after==1 or case=="timeout" else sent
        elif full:
            retired=(retired+1)&65535
        else:
            raise AssertionError("redundant pre-SEAL drain")
        used=(sent-retired)&65535
        h=seal if queued and not used else tail
        ack=bytearray(bytes((int(h[0]==3),h[0]))+h[2:10]+bytes((0x65,0x9a)))
        if not used and case=="wrong_generation":ack[8]^=1
        if not used and case=="ordinary_status":ack[0]=0
        r=bytearray(20);r[1]=0xf7;r[2]=int(bool(used))|2|(4 if used==4 else 0)
        if case=="tail_fault":r[2]|=128
        r[3:7]=struct.pack(">HH",sent,retired);r[7:19]=ack
        r[19]=crc(r[1:19],8,7,0)
        if case=="bad_crc":r[19]^=1
        return bytes(r)
    m.endpoint.exchange=exchange
    args=[m.w,m.q,len(seal),m.q+300]
    ok=m.call("nes_window184_barrier",args)
    assert bool(ok)==(case in ("ok","wrap","full")) and queued and operations.count(0xe1)==1
    if ok:
        assert after==2 and bytes(m.u.mem_read(m.q+300,12))==bytes((1,3))+seal[2:10]+bytes((0x65,0x9a))
    else:
        before=len(operations)
        assert m.get(m.w,w,"error") and not m.call("nes_window184_barrier",args) and before==len(operations)
    return dict(case=case,success=bool(ok),operations=[hex(v) for v in operations],error=m.get(m.w,w,"error"))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("arm","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args()
    rows=[trial(a.arm,m) for m in ("ok","full","wrap","tail_fault","wrong_generation","ordinary_status","bad_crc","timeout","stop")]
    a.out.write_text(json.dumps(dict(firmware=sha(a.arm/"obj-nes-100/firmware.stm"),cases=rows),indent=2)+"\n")
