"""Check changed inactive pixels, partial STOP and a late bad HDMA row in Mesen."""
import argparse
from pathlib import Path
from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once

def test(temp,phase,case):
    src=directory(temp,phase,"991matched","cold")
    cmds,ledger=packet_path(src,911)
    allowed=next(i for i,row in enumerate(cmds) if row[0]==911 and
                 (b:=bytes.fromhex(row[3]))[:2]==bytes((2,5)) and int.from_bytes(b[10:12],"little")==1121)
    if case=="stop":
        cmds=cmds[:allowed+1]
    def observer(s):
        s=once(s,"local function loaded()", """local earlyCount991=0
local changed991=false
local function pixels991(action)
 local bank=word(0x1034);assert(bank~=word(0x1032))
 local dest=bank==0 and 0x5000 or 0x9000
 local bytes=file('expected-911.bin')
 for p=0,2 do for j=0,63 do
  local off=(j//2)*64+16*p+j%2
  local value=bytes:byte(1122+off)
  if action=='fill' then emu.write(dest+off,value~255,emu.memType.snesVideoRam)
  else assert(emu.read(dest+off,emu.memType.snesVideoRam)==value,'raw pixel '..off) end
 end end
end
local function loaded()""")
        s=once(s,"sample516('raw991',dmaLength)","if pw(8)==911 then earlyCount991=earlyCount991+1 end;sample516('raw991',dmaLength)")
        # Aligned runs install the test body at generation 911 BEGIN, so use
        # the post-observer load sample as the insertion point.
        edit="""if pw(8)==911 and pb(0)==2 and pb(1)==5 and pw(10)==1121 then
 pixels991('fill');changed991=true
end
if pw(8)==911 and pb(0)==3 then
 assert(changed991 and earlyCount991==3 and word(0x1800)==2)
 pixels991('check')
end
"""
        if case=="damage":
            edit+="if pw(8)==911 and pb(0)==3 then emu.write(0x10000+word(0x1020)+0x6961+192,255,emu.memType.snesWorkRam) end\n"
        if case=="stop":
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if changed991 and earlyCount991==1 then return 128 end")
        if case in ("stop","damage"):
            s=once(s,"if rejected then\n   local screen",f"if rejected then\n   assert(changed991 and earlyCount991=={1 if case=='stop' else 3} and word(0x1800)==0 and word(0x125a)==0)\n   local screen")
        return once(s,'sample516("load");reads=0', edit+'sample516("load");reads=0')
    fault={"changed":None,"stop":"stop_decode","damage":"damage"}[case]
    return replay(temp,src,temp/f"nes-raw991-guard-{case}-p{phase}","fixed",cmds,911,fault,observe=observer)


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("phase",type=int,choices=(1,2))
    parser.add_argument("case",choices=("stop","damage","changed"))
    args=parser.parse_args();test(args.temp,args.phase,args.case)
