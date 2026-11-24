"""Challenge checked spans, changed WRAM, arbitrary repeat fallback and partial STOP."""
import argparse
from pathlib import Path
from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once


def guard(t,phase,case):
    folder=directory(t,phase,"994both3","cold")
    cmds,_=packet_path(folder,911)
    i=next(i for i,c in enumerate(cmds) if c[0]==911 and c[1]==8)
    def edit(idx,start,replacement):
        g,op,at,wire,bulk,obs,duration=cmds[idx]
        b=bytearray.fromhex(wire);b[start:start+len(replacement)]=replacement
        cmds[idx]=g,op,at,b.hex(),bulk,obs,duration
    if case=="stop":
        cmds=cmds[:i+1]
    elif case=="span":
        edit(i,14,(384).to_bytes(2,"little"));cmds=cmds[:i+1]
    elif case=="fallback":
        edit(i,16,bytes.fromhex("13234697"))
        assert cmds[i+1][1]==4
        edit(i+1,10,(508).to_bytes(2,"little"));cmds=cmds[:i+2]
    def observe(s):
        s=once(s,"local function loaded()","""local checked994=false
local function challenge994(action,done)
 local ptr=0x10000+word(0x1020)+0x6200+176
 assert(word(0x1034)~=word(0x1032))
 for i=0,335 do
  local value=pb(16+i%4)
  if action=='fill' then emu.write(ptr+i,value~255,emu.memType.snesWorkRam)
  else assert(rd(ptr+i)==(i<done and value or value~255),'repeat byte '..i) end
 end
end
local function loaded()""")
        s=once(s,'sample516("load");reads=0','''if pw(8)==911 and pb(0)==8 then challenge994('fill',0) end
 sample516("load");reads=0''')
        if case=="stop":
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if packet and pw(8)==911 and pb(0)==8 and fillBytes545==64 then return 128 end")
        count={"stop":64,"span":0}.get(case,336)
        s=once(s,"  if uniform545() and (pb(1)~=4 or ack[1]<224) then",
               f"  if pw(8)==911 and pb(0)==8 then challenge994('check',{count});checked994=true end\n  if uniform545() and (pb(1)~=4 or ack[1]<224) then")
        if case!="changed":
            s=once(s,"if rejected then\n   local screen","if rejected then\n   assert(checked994)\n   local screen")
        else:
            s=once(s,"assert(captured==commits)","assert(captured==commits and checked994)")
        return s
    fault=None if case=="changed" else "stop_decode" if case=="stop" else case
    return replay(t,folder,t/f"nes-color994-guard-{case}-p{phase}","fixed",cmds,911,fault,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("temp",type=Path);p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("case",choices=("changed","span","stop","fallback"));a=p.parse_args();guard(a.temp,a.phase,a.case)
