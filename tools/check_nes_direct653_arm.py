"""Check the original STM32 decoder on actual D1 bytes, bad extents and cold retry."""
import argparse
import json
from pathlib import Path
from check_nes_game478 import Machine
from check_nes_fault641 import digest

def check(a):
    m=Machine(a.arm,bytes(128))
    state=m.layout["nes_native165"]
    def reset():m.call("nes_native165_reset",[m.state])
    def submit(token,block):
        addr=0x2001b000;m.u.mem_write(addr,bytes(block))
        return m.call("nes_native165_packet",[m.state,token,addr,len(block)])
    rows=(a.guards/"blocks.txt").read_text().splitlines()
    recovery=[bytes.fromhex(r.split()[1])[:-2] for r in rows]
    for corrupt in ("start","generation","count","duplicate","short"):
        reset();bad=bytearray(recovery[0]);token=65535
        if corrupt=="duplicate":assert submit(token,bad)
        elif corrupt=="short":bad.pop()
        else:bad[{"start":13,"generation":15,"count":16}[corrupt]]^=1 if corrupt!="count" else 16
        assert not submit(token,bad)
        reset()
        for i,block in enumerate(recovery):assert submit((token+i)&65535,block)
        values=bytes(m.u.mem_read(m.state+state["maps"],198))
        assert values==b"".join(((0x5411^(i*113))&32767).to_bytes(2,"little") for i in range(99))
    block=bytearray.fromhex(json.loads((a.rtl/"sender.json").read_text())["955"][0]["wire"])
    for name,offset in (("decoded_crc",20),("extent",17),("generation",15)):
        reset();bad=bytearray(block);bad[offset]^=1
        assert not submit(0,bad) and not submit(0,block)
        reset();assert submit(0,block)
    return dict(firmware=digest(a.arm/"obj-nes-100/firmware.stm"),raw_cold_cells=99,raw_POP_wrap=True,
        original_rejections=["start","generation","count","duplicate","short"],compact_rejections=["decoded_crc","extent","generation"])
if __name__=="__main__":
    p=argparse.ArgumentParser()
    for k in ("arm","guards","rtl","out"):p.add_argument("--"+k,type=Path,required=True)
    a=p.parse_args();a.out.write_text(json.dumps(check(a),indent=2)+"\n")
