"""Coalesce an accepted map across one pending 16B BG descriptor on the 978 receiver."""
import argparse
import json
import subprocess
from pathlib import Path
from unittest.mock import patch
import boot_nes_column854 as boot
import nes_page963
from build_nes_trace_replay import Code
from nes_blank959 import ORIGIN, LOADER_SOURCE
from nes_hdma990 import BASE, PACKED
from nes_raw506 import once

ROM=BASE.parent/"nes-map997"/"rom"
SITE=0x7e2919


def build():
    labels=json.loads((PACKED/"labels.json").read_bytes())
    body=bytearray((PACKED/"body.bin").read_bytes())
    c=Code(ORIGIN+len(body));c.labels.update(labels)
    def imm(op,n):
        c.emit(op);c.word(n)
    c.label("small_bg997");imm(0xc9,0x5000);c.branch(0xd0,"other997")
    c.absolute(0x4c,0x291e)
    c.label("other997");imm(0xc9,0);c.branch(0xd0,"last997")
    c.long(0xbf,0x7e4004);imm(0xc9,16);c.branch(0xd0,"last997")
    c.emit(0xa5,0x70);imm(0x29,0x7000);imm(0xc9,0x5000);c.branch(0xd0,"last997")
    c.absolute(0xec,0x1252);c.branch(0x90,"last997");c.branch(0xf0,"last997")
    # BG destination must be disjoint from either bank's map. Only inspect
    # the preceding descriptor when it too is pending and nonempty.
    c.long(0xbf,0x7e4002);imm(0x29,0x7fff);imm(0xc9,0x1ff1);c.branch(0xb0,"last997")
    c.long(0xbf,0x7e3ff8);imm(0x29,0x7000);imm(0xc9,0x5000);c.branch(0xd0,"last997")
    c.long(0xbf,0x7e3ffc);c.branch(0xf0,"last997")
    c.emit(0x8a,0x38);imm(0xe9,8);c.emit(0xaa)
    # Existing checks still require exact source/destination adjacency and
    # bounded total length before modifying the descriptor.
    c.label("last997");c.jump("merge532")
    i=SITE-ORIGIN;assert body[i:i+5]==bytes.fromhex("c90050d015")
    body[i:i+3]=bytes([0x4c])+(c.labels["small_bg997"]&65535).to_bytes(2,"little")
    body.extend(c.finish())
    with patch.object(boot,"STORED",5600):
        boot.build(LOADER_SOURCE,ROM,bytes(body),c.labels,compact_mvn=True,minimum=2,short_pairs=True)


def observe(s,mode):
    source='''assert(x==tail-8 and x>=word(0x1252) and (word(0x4000+tail)&0x7000)==0x5000)'''
    target='''assert(x==tail-8 and x>=word(0x1252))
  if (word(0x4000+tail)&0x7000)~=0x5000 then
   local bg=word(0x4002+tail);local start=word(0x4002+x)
   assert((word(0x4000+tail)&0x7000)==0 and word(0x4004+tail)==16)
   assert((word(0x70)&0x7000)==0x5000 and (word(0x4000+x)&0x7000)==0x5000)
   assert(bg+16<=start or bg>=word(0x72)+word(0x74))
   sample516('cross997',word(0x4004+x)+word(0x74))
  end'''
    s=once(s,source,target)
    if mode=="matched":
        old=(PACKED/"body.bin").read_bytes();new=(ROM/"body.bin").read_bytes()
        code=",".join(str(v) for v in new[len(old):])
        off=SITE-ORIGIN
        site=",".join(str(v) for v in new[off:off+3])
        s=once(s,'sample516("load");reads=0',f'''if pw(8)==907 and pb(0)==1 then
 local extra={{{code}}};for i,v in ipairs(extra) do emu.write({ORIGIN+len(old)-0x7e0000}-1+i,v,emu.memType.snesWorkRam) end
 local j={{{site}}};for i,v in ipairs(j) do emu.write(0x2918+i,v,emu.memType.snesWorkRam) end
 elseif pw(8)==908 and pb(0)==1 then
 local j={{0xc9,0,0x50}};for i,v in ipairs(j) do emu.write(0x2918+i,v,emu.memType.snesWorkRam) end
 end
 sample516("load");reads=0''')
    return s


def run(temp,phase,mode):
    popen=subprocess.Popen
    def launch(cmd,*a,**kw):
        if "--testRunner" in cmd:
            f=Path(cmd[cmd.index("--testRunner")+1])
            f.write_text(observe(f.read_text(encoding="utf8"),mode),encoding="utf8",newline="\n")
        return popen(cmd,*a,**kw)
    with patch.object(nes_page963,"PACKED",PACKED if mode=="matched" else ROM),patch.object(subprocess,"Popen",launch):
        nes_page963.simulate(temp,phase,"cold",True,BASE,True,tag="997"+mode,edition=966)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("mode",choices=("build","matched","static"))
    p.add_argument("temp",type=Path,nargs="?");p.add_argument("phase",type=int,nargs="?",choices=(1,2))
    a=p.parse_args()
    if a.mode=="build":build()
    else:run(a.temp,a.phase,a.mode)
