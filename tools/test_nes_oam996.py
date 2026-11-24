"""Pin 978 through the 911 tail, fuse the last two OAM packets and inject faults."""
import argparse
from pathlib import Path
from build_nes_oam996 import ROM, PACKED, WORK
from check_nes_plan975 import directory, packet_path, replay
from nes_oam996 import observe
from nes_raw506 import once

CASES=("matched","damaged","highbits","partial","span","noprior")


def scripts(s,case,rom):
    s=observe(s)
    before=(PACKED/"body.bin").read_bytes()
    after=(rom/"body.bin").read_bytes()
    locs=[(0x2000+i,b) for i,b in enumerate(after) if i>=len(before) or b!=before[i]]
    # Keep the 978 boot, code placement, captures and queue unchanged until this packet.
    writes="\n".join(f" emu.write({i},{b},emu.memType.snesWorkRam)" for i,b in locs)
    edit=""
    if case in ("damaged","highbits"):
        off=212 if case=="damaged" else 543
        edit=f" emu.write(base996+{off},rd(base996+{off})~128,emu.memType.snesWorkRam)"
    s=once(s,'sample516("load");reads=0',f"""if pw(8)==911 and pb(0)==8 and pw(12)==6 then
{writes}
{edit}
 end
 sample516("load");reads=0""")
    s=once(s,"elseif active996 and pw(8)==911 and pb(1)==4 and pw(10)==512 then",
           "elseif active996 and pw(8)==911 and pb(1)==4 and pw(12)==6 then")
    if case=="partial":
        s=once(s," if a==0x6001 then", """ if a==0x6001 then
  if packet and pw(8)==911 and pb(0)==8 and pw(12)==6
   and rd(base996+193)==240 and rd(base996+177)~=240 then
    sample516('partial996',192);return 128
  end""")
    return s


def run(temp,p,case,grouped=False):
    source=directory(temp,p,"978returned","cold")
    commands,_=packet_path(source,911)
    i=next(i for i,c in enumerate(commands) if c[0]==911 and c[1]==8)
    orig=commands[i];attrs=commands[i+1]
    h=bytearray.fromhex(orig[3])
    assert h[16:]==bytes.fromhex("00f00000") and bytes.fromhex(attrs[3])[16:]==bytes(2)
    h[12:14]=(6).to_bytes(2,"little");h[14:16]=(368).to_bytes(2,"little")
    h.extend((212 if case!="span" else 214).to_bytes(2,"little"))
    if case=="noprior":
        # A shorter-than-legitimate cut forces inspection of still-live sprites.
        h[-2:]=(176).to_bytes(2,"little")
    commands[i]=(*orig[:3],h.hex(),*orig[4:])
    del commands[i+1]
    for j in range(i+1,len(commands)):
        c=commands[j]
        if c[0]!=911:continue
        b=bytearray.fromhex(c[3]);seq=int.from_bytes(b[2:4],"little")
        b[2:4]=(seq-1).to_bytes(2,"little");commands[j]=(*c[:3],b.hex(),*c[4:])
    if case!="matched":commands=commands[:i+1]
    fault=None if case=="matched" else "stop_decode" if case=="partial" else "span"
    label=("group-" if grouped else "")+case
    rom=WORK/"grouped" if grouped else ROM
    return replay(temp,source,temp/f"nes-oam996-{label}-p{p}","fixed",commands,911,fault,observe=lambda s:scripts(s,case,rom))


if __name__=="__main__":
    a=argparse.ArgumentParser(description=__doc__);a.add_argument("temp",type=Path);a.add_argument("phase",type=int,choices=(1,2));a.add_argument("case",choices=CASES)
    a.add_argument("--grouped",action="store_true")
    args=a.parse_args();run(args.temp,args.phase,args.case,args.grouped)
