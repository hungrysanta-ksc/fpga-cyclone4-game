"""Trace the 909 ACK's WRAM OAM through the next use of the same bank."""
import argparse
from pathlib import Path
from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once

def observe(s):
    lua=Path(__file__).with_suffix(".lua").read_text()
    s=once(s,"local function loaded()",lua+"\nlocal function loaded()")
    s=once(s,'sample516("load");reads=0', '''if active996 and pw(8)==911 and (pb(0)==1 or pb(1)==4) then snap996('load') end
 sample516("load");reads=0''')
    return once(s,'lastStatus=ack[1];sample516("ack",lastStatus)', '''lastStatus=ack[1];sample516("ack",lastStatus)
 if lastStatus==1 and pw(8)==909 then
  base996=0x10000+word(0x1020)+0x6200;active996=true;snap996('history')
 elseif active996 and pw(8)==911 and pb(1)==4 and pw(10)==512 then
  snap996('final');active996=false
 end''')

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    a=p.parse_args();d=directory(a.temp,a.phase,"978returned","cold")
    cmds,_=packet_path(d,911)
    replay(a.temp,d,a.temp/f"nes-oam996-trace-p{a.phase}","fixed",cmds,911,observe=observe)
