"""Conditional 912 feasibility with real 65816 bank returns and earlier first E9."""
import argparse
import json
import math
from pathlib import Path
from check_nes_plan975 import directory, packet_path, read, replay
from nes_raw506 import once
from test_nes_banks557 import MASTER


def run(t,p,advance):
    d=directory(t,p,"978returned","cold")
    tiles=[json.loads(line) for line in (d/"producer.jsonl").read_text().splitlines()]
    tiles=[v for v in tiles if v["generation"]==912]
    assert [v["token"] for v in tiles]==list(range(31,39))
    old=dict(read(d/"returns904.json"))
    delta=round(advance*MASTER/1000)
    c,_=packet_path(d,912,expected_shape=(21,8))
    prior=[v for v in c if v[0]<912]
    frame=[v for v in c if v[0]==912]
    groups=read(d/"e9931.json")
    groups=[v for v in groups if v["g"]==912]
    assert len(groups)==2
    # Charge first valid E8 discovery lag and retain measured fill work.
    # No tile can reserve a reused bank before this replay's actual read receipt.
    ticks={}
    for v in tiles:
        n=v["token"]
        ticks[n]=round(v["observed"]-v["producer"])+ (v["producer"]-old[n-2] if n>=33 else 0)
        assert ticks[n]>=0
    fixed=[]
    for cmd in frame:
        if cmd[1]!=7:
            fixed.append(cmd)
            continue
        b=bytes.fromhex(cmd[3]);n=int.from_bytes(b[16:20],"little")
        # For each later tile require at least the associated E9 group.
        # If originally ready before the second E9, it belongs to the first.
        tile=tiles[n-31]
        e9=max(g["seal"] for g in groups if g["seal"]<=tile["producer"])
        earliest=tile["observed"]-delta if n<=32 else e9-delta
        fixed.append((*cmd[:5],math.ceil(earliest),cmd[-1]))
    out=t/f"nes-ready999-bank-{advance}-p{p}"
    def observe(s):
        s=once(s,"if sent-retired>=4 then break end","if sent-retired>=2 then break end")
        k="if not duration then duration=assert(tonumber(wires:read('*l'))) end"
        latency="{"+",".join(f"[{n}]={v}" for n,v in ticks.items())+"}"
        s=once(s,k,"""local pkt=unhex(args[1])
    if pkt:byte(1)==7 then
     local token=string.unpack('<I4',pkt,17)
     if token>=33 then
      if not bank999[token-2] or now<bank999[token-2]+("""+latency+""")[token] then break end
     end
    end
    """+k)
        s=once(s,"local lastPush527=0","local bank999={}\nlocal lastPush527=0")
        return once(s,"step920(\"consume920\")\n  local ret=", """step920("consume920")
  bank999[pw(16)+65536*pw(18)]=emu.getState().masterClock
  local ret=""")
    replay(t,d,out,"prelude",prior+fixed,912,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("advance",type=int,choices=(0,2,4))
    a=p.parse_args();run(a.temp,a.phase,a.advance)
