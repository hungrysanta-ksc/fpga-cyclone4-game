"""Replay the first two cold generations from the partially written OAM image."""
import argparse
import csv
from pathlib import Path
from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once


def run(t,p):
    interrupted=t/f"nes-oam996-partial-p{p}"
    with (interrupted/"oam996.csv").open() as f:
        saved={int(r["address"]):int(r["value"]) for r in csv.DictReader(f) if r["event"]=="final"}
    assert sorted(saved)==list(range(176,544))
    d=directory(t,p,"996tail","cold")
    all_cmds,_=packet_path(d,911,expected_shape=(15,3))
    cmds=[c for c in all_cmds if c[0]<=906]
    assert not any(bytes.fromhex(c[3])[12]==6 for c in cmds if c[1]==8)
    def observe(s):
        buf=",".join(str(saved[i]) for i in range(176,544))
        return once(s,'sample516("load");reads=0', f"""if pw(8)==905 and pb(0)==1 then
 local residue={{{buf}}}
 for i,v in ipairs(residue) do emu.write(0x16200+175+i,v,emu.memType.snesWorkRam) end
 for i=0,543 do emu.write(0x1e200+i,0xa5,emu.memType.snesWorkRam) end
 end
 sample516("load");reads=0""")
    return replay(t,d,t/f"nes-oam996-cold-p{p}","fixed",cmds,906,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args();run(a.temp,a.phase)
