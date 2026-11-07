"""Exercise the actual early OAM writer, including its SPI STOP boundary and receipt identity."""
import argparse
import json
from pathlib import Path
from check_nes_supply485_arm import ARM, crc, sha


def check(src, mode):
    m = ARM(src,"normal")
    m.setup()
    for key, value, size in (("plan",m.p,4),("displayed",1,1),("serial",8,4)):
        m.put(m.s,"nes_native_sink165",key,value,size)
    m.put(m.p,"nes_plan200","quiet_map",1,4)
    m.put(m.p,"nes_plan200","bulk_pending",int(mode=="bulk"),1)
    m.put(m.s,"nes_native_sink165","ack635",6,4)
    m.u.mem_write(m.s+m.layout["nes_native_sink165"]["ack635"]+4,(0 if mode=="cold" else 7).to_bytes(4,"little"))
    m.put(m.video,"nes_native_video165","generation",906 if mode=="foreign" else 907,2)
    m.put(m.video,"nes_native_video165","valid",1,1)
    m.u.mem_write(m.video+m.layout["nes_native_video165"]["oam"],bytes(range(112)))
    if mode=="different":
        m.u.mem_write(m.video+m.layout["nes_native_video165"]["cgram"],b"\x10")
    if mode=="STOP":
        m.endpoint.mode="STOP_after_bulk"
        m.endpoint.bulk=1
    issued=[]
    def send(tx, clock):
        assert len(tx)==135 and tx[:3]==bytes((0xe1,9,4)) and int.from_bytes(tx[-2:],"big")==crc(tx[:-2],16,0x1021,65535)
        assert tx[17:-2]==bytes(range(112))+(7).to_bytes(4,"little")
        issued.append(tx.hex())
        return bytes(len(tx))
    m.endpoint.exchange=send
    ok=m.call("nes_offer646",[m.s,m.video])
    assert bool(ok)==(mode!="STOP")
    assert m.get(m.s,"nes_native_sink165","early_oam646")==int(mode=="positive")
    assert len(issued)==int(mode=="positive")
    if mode=="positive":
        assert m.call("nes_offer646",[m.s,m.video])==1 and len(issued)==1
    assert not m.call("nes_plan200_retire",[m.p])
    return dict(case=mode,issued=len(issued),offer_ok=ok,grant_is_final_ACK=False)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("--src",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    a=p.parse_args()
    rows=[check(a.src,m) for m in ("positive","cold","bulk","foreign","different","STOP")]
    a.out.write_text(json.dumps(dict(firmware=sha(a.src/"obj-nes-100/firmware.stm"),cases=rows),indent=2)+"\n")
