"""Replay missing, partial and damaged ranges; check the actual inactive WRAM."""
import argparse
from pathlib import Path

from check_nes_plan975 import directory, packet_path, replay
from nes_raw506 import once

FAULTS=("missing_raw","partial_raw","damage","stop_decode","stop_pending","bad_seal")


def u16(b,at):
    return int.from_bytes(b[at:at+2],"little")


def verify(temp,phase,mode,fault):
    src=directory(temp,phase,"990"+mode,"cold")
    ref=directory(temp,phase,"978returned","cold")
    reference,_=packet_path(ref,911)
    canonical=b"".join(b[16:] for a in reference if (b:=bytes.fromhex(a[3]))[0:2]==b'\2\5' and
                       u16(b,8)==911 and u16(b,10)>=1121)
    assert len(canonical)==441
    cmds,_=packet_path(src,911,expected_shape=(17 if mode=="late" else 16,3))
    raw,= [i for i,a in enumerate(cmds) if a[0]==911 and
           (b:=bytes.fromhex(a[3]))[:2]==b'\2\5' and u16(b,10)==1121 and u16(b,12) in (6,192)]
    if fault=="stop_pending":
        table,= [i for i,a in enumerate(cmds) if a[0]==911 and
                 (b:=bytes.fromhex(a[3]))[:2]==bytes((2,5)) and u16(b,10)==1313]
        cancel=next(i for i in range(table+1,raw) if cmds[i][1]==7)
    last=bytearray.fromhex(cmds[-1][3])
    assert last[0]==3
    if fault in ("missing_raw","partial_raw"):
        gen,op,at,wire,bulk,obs,elapsed=cmds[raw]
        b=bytearray.fromhex(wire)
        if fault=="missing_raw":
            last[2:4]=b[2:4]; b=last
        else:
            b[12:14]=(190).to_bytes(2,"little");del b[-2:]
        cmds=cmds[:raw]+[(gen,b[0],at,b.hex(),bulk,obs,elapsed)]
    if fault=="stop_pending":cmds=cmds[:cancel+1]
    out=temp/f"nes-hdma990-check-{mode}-p{phase}-{fault}"
    if fault=="stop_pending":out=out.with_name(out.name+"4")
    def observe(lua):
        (out/"canonical.bin").write_bytes(canonical)
        inject="""
 if pw(8)==911 and pb(0)==2 and pb(1)==5 and pw(10)==1121 and (pw(12)==192 or pw(12)==6) then
  assert(word(0x1800)==1,'raw arrived without table')
  local base=0x10000+word(0x1020)+0x6500+1313
  local expected=file('canonical.bin')
  for i=0,248 do assert(rd(base+i)==expected:byte(193+i),'table WRAM '..i) end
 end"""
        if fault in ("damage","stop_decode"):
            inject+="""
 if pw(8)==911 and pb(0)==3 then
  assert(word(0x1800)==0 and word(0x108a)==1562)
  local at=0x10000+word(0x1020)+0x6500+1121
  local expected=file('canonical.bin')
  for i=0,440 do assert(rd(at+i)==expected:byte(i+1),'complete WRAM '..i) end
 """+("emu.write(at+192,255,emu.memType.snesWorkRam)" if fault=="damage" else "")+"\n end"
        if fault=="missing_raw":
            inject+="\n if pw(8)==911 and pb(0)==3 then assert(word(0x1800)==1) end"
        if fault=="stop_pending":
            lua=once(lua,"if pb(0)==7 then assert(lastStatus==0 and reads==#tile,'early bulk ACK')end",
                     """if pb(0)==7 then
   if pendingSTOP990 and pw(8)==FAULT and lastStatus==0xe4 then assert(word(0x1800)==0)
   else assert(lastStatus==0 and reads==#tile,'early bulk ACK')end
  end""")
            lua=once(lua,"local firstPoll","local pendingSTOP990=false\nlocal firstPoll")
            lua=once(lua," if a==0x6001 then",""" if a==0x6001 then
  if packet and pw(8)==FAULT and pb(0)==7 and word(0x1800)==1 then pendingSTOP990=true end
  if pendingSTOP990 then return 128 end""")
            lua=once(lua,"local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb'","local screen=emu.getScreenBuffer();assert(pendingSTOP990);local f=assert(io.open(ROOT..'/retained.rgb'")
        lua=once(lua,"packet=requests[index];sample516","packet=requests[index]\n"+inject+"\n sample516")
        return once(lua,"if rejected then\n   local screen",
                    "if rejected then\n   assert(word(0x1800)==0,'partial table survived abort')\n   local screen")
    return replay(temp,src,out,"fixed",cmds,911,"stop_decode" if fault=="stop_pending" else fault,observe=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path);p.add_argument("phase",type=int)
    p.add_argument("mode");p.add_argument("fault",choices=FAULTS)
    a=p.parse_args();verify(a.temp,a.phase,a.mode,a.fault)
