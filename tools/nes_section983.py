"""Time the last ARM writes to the 201/240-byte section-5 pair in 978."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from unicorn import UC_HOOK_MEM_WRITE
from unicorn.arm_const import UC_ARM_REG_R2
from check_nes_plan975 import directory, packet_path
from nes_cell977 import simulate
from nes_head980 import baseline
from replay_nes_supply905 import joint, UC_HOOK_CODE
from nes_raw506 import once


def work(mode):
    return baseline("returned").with_name("nes-section983-"+mode)


def prepare(mode):
    dest=work(mode)/"link"
    shutil.copytree(baseline("returned")/"link",dest)
    path=dest/"src/nes_native_sink165.c"
    s=path.read_text()
    s=once(s," if(!reuse){"," bool late_oam=!reuse && p->patch_count==1 && p->scroll_issued;\n if(!reuse){")
    s=once(s," if(!oam227(s,p->oam))return false;"," if(!late_oam && !oam227(s,p->oam))return false;")
    send=("  if(!packet(s,2,5,offset,joined,201))return false;" if mode=="raw" else
          "  if(!packet(s,2,5,offset+201,joined+201,240))return false;")
    s=once(s,send,send+"\n  if(late_oam && !oam227(s,p->oam))return false;")
    path.write_text(s,newline="\n")


def profile(temp, phase):
    init=joint.Runtime.__init__
    marks={}
    def install(cpu,*args):
        init(cpu,*args)
        def enter(u,pc,size,ctx):
            if cpu.generation!=911 or marks:
                return
            base=u.reg_read(UC_ARM_REG_R2)
            # One patch row. The first two fine-row bytes of each plane pair
            # in each canonical 64-byte tile form the 192-byte packed image.
            groups={tile*64+plane*16+b:"raw" for tile in range(32)
                    for plane in range(3) for b in range(2)}
            groups.update({2048+i:"table_head" if i<9 else "table_tail" for i in range(243)})
            groups.update({2292+i:"lengths" for i in range(6)})
            groups.update({6144+i:"joined_first" if i<201 else "joined_last" for i in range(441)})
            marks["planner"]=cpu.clock
            def written(u,access,address,width,value,ctx):
                if cpu.generation==911:
                    for i in range(address-base,address-base+width):
                        if i in groups:
                            marks[groups[i]]=cpu.clock
            cpu.u.hook_add(UC_HOOK_MEM_WRITE,written,begin=base,end=base+8191)
            def seal(u,pc,size,ctx):
                if cpu.generation!=911:
                    return
                marks["sink_seal"]=cpu.clock
                image=bytes(u.mem_read(base,2298))
                # The packer visits planes before tiles.
                raw=b"".join(image[tile*64+plane*16:tile*64+plane*16+2]
                             for plane in range(3) for tile in range(32))
                marks["payload"]=(raw+image[2048:2291]+image[2292:2298]).hex()
            addr=cpu.syms["nes_sink212_seal"]
            cpu.u.hook_add(UC_HOOK_CODE,seal,begin=addr,end=addr)
        addr=cpu.syms["nes_native_video211_plan"]
        cpu.u.hook_add(UC_HOOK_CODE,enter,begin=addr,end=addr)
    with patch.object(joint.Runtime,"__init__",install):
        simulate(temp,phase,"cold",True,baseline("returned"),True,tag="983profile",edition=966)
    out=directory(temp,phase,"983profile","cold")
    commands,_=packet_path(out,911)
    wire=b"".join(bytes.fromhex(c[3])[16:] for c in commands if c[:2]==(911,2)
                  and bytes.fromhex(c[3])[1]==5 and int.from_bytes(bytes.fromhex(c[3])[10:12],"little")>=1121)
    assert wire==bytes.fromhex(marks.pop("payload")) and len(wire)==441
    (out/"writes983.json").write_text(json.dumps(marks))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp",type=Path)
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("--mode",choices=("profile","raw","tables"),default="profile")
    p.add_argument("--prepare",action="store_true")
    a=p.parse_args()
    if a.mode=="profile":
        profile(a.temp,a.phase)
    elif a.prepare:
        prepare(a.mode)
    else:
        simulate(a.temp,a.phase,"cold",True,work(a.mode),True,tag="983"+a.mode,edition=966)
