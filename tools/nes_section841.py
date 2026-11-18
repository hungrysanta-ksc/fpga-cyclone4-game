"""Publish a checked compact section before BG allocates its scratch."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from nes_pair839 import BASE, PROBES, REFERENCE, once, sha
import nes_admission838 as admission
import nes_raw841 as raw
import nes_pair839 as pair
from analyze_nes_map830 import window
from replay_nes_section832 import run
from replay_nes_window837 import MirrorLink, main, reject

OUT=PROBES/"nes-section841"
ARM=BASE.parent/"link-841section"


def prepare(release=False):
    dest=OUT/("patch-release" if release else "patch")
    dest.mkdir(exist_ok=True,parents=True)
    def read(name):
        return (BASE/"src"/name).read_text()
    def write(name,data):
        (dest/name).write_text(data,newline="\n")

    name="nes_native_video165.h"
    write(name,once(read(name),"bool scroll_issued;","bool scroll_issued, section841;"))
    name="nes_resident211.h"
    write(name,once(read(name),"bool (*finish_obj)","bool (*early_section)(void *);\n bool (*finish_obj)"))
    name="nes_native_sink165.h"
    write(name,once(read(name),"bool nes_scroll810(","bool nes_section841(struct nes_native_sink165 *,struct nes_native_video165 *);\nbool nes_scroll810("))
    name="nes_native_runtime165.c"
    data=once(read(name),"static bool offer527(","""static bool early_section841(void *ctx){
 struct nes_native_runtime165 *s=ctx;
 return nes_section841(&s->sink,s->video);
}
static bool offer527(""")
    write(name,once(data,"s->resident->finish_obj=finish_obj810;","s->resident->early_section=early_section841;\n  s->resident->finish_obj=finish_obj810;"))

    name="nes_planner211.c"
    data=read(name)
    a=data.index(" unsigned at=0;\n for(unsigned y=0;y<224;)")
    b=data.index(" /* No OBJ/raw",a)
    scroll=data[a:b]
    data=data[:a]+" scroll841(p);\n"+data[b:]
    a=data.index(" if(p->patch_count){\n  /* No BG allocation")
    b=data.index(" p->valid=true;",a)
    raw=data[a:b]
    palette="  for(unsigned c=0;c<64;c++)put16(p->cgram+(64+c)*2,lut[c]);"
    raw=once(raw,palette,"")
    data=data[:a]+" if(!raw841(s,p))return false;\n if(p->patch_count){\n"+palette+"\n }\n"+data[b:]
    data=once(data,"static bool build211(", "static void scroll841(struct nes_native_video165 *p){\n"+scroll+"}\n"+
              "static bool raw841(const struct nes_native165 *s,struct nes_native_video165 *p){\n"+raw+" return true;\n}\nstatic bool build211(")
    data=once(data," /* Slot0 is explicitly", """ uint64_t stale=resident->map_stale[resident->target];
 if(resident->displayed && resident->early_section && raw_count==2 && s->counts[2]>28 &&
    !(uint32_t)stale && (((uint32_t)(stale>>32)&0x7ffffu)==0x7ffffu)){
  scroll841(p);
  if(!raw841(s,p) || !resident->early_section(resident->ctx))return fail(p,7);
  /* Restore BG allocator scratch and the unpublished scroll marker. */
  memset(&p->patch,0,sizeof(p->patch));
  p->hdma_size=0;
 }
 /* Slot0 is explicitly""")
    write(name,data)
    name="nes_native_sink165.c"
    data=once(read(name),"op!=24 && op!=25","op!=24 && op!=25 && op!=26")
    data=once(data," if(op==25)op=5;"," if(op==26)op=9;\n if(op==25)op=5;")
    data=once(data,"  if(fragments>112/4 &&","  if(p->section841)return true;\n  if(fragments>112/4 &&")
    data=once(data," if(!(n&1))p->hdma[n++]=0;\n if(!packet(s,24"," if(p->section841)return true;\n if(!(n&1))p->hdma[n++]=0;\n if(!packet(s,24")
    data=once(data,"bool nes_sink212_seal(","""bool nes_section841(struct nes_native_sink165 *s,struct nes_native_video165 *p){
 uint8_t words[10],tail[9];
 unsigned n=p->hdma_size;
 if(!s->plan || s->plan->started || s->plan->bulk_pending || !n || n>239 ||
    !words836(p->patch.chr,words))return true;
 if(!(n&1))p->hdma[n++]=0;
 const uint8_t *table=(const uint8_t *)p+__builtin_offsetof(struct nes_native_video165,patch.mode);
 memcpy(tail,table+240,3);memcpy(tail+3,p->patch.size,6);
 if(!packet(s,24,5,0,p->hdma,n) || !packet_wire(s,25,5,n,zero,2,1121-n) ||
    !packet(s,26,5,1121,words,10) || !packet(s,24,5,1505,table,240) ||
    !packet(s,24,5,1745,tail,9))return false;
 p->section841=true;
 return true;
}
bool nes_sink212_seal(""")
    data=once(data," if(!p->scroll_issued && !span(s,5,0"," if(p->section841){size[5]=1754;}else{\n if(!p->scroll_issued && !span(s,5,0")
    data=once(data," uint8_t descriptor[168];"," }\n uint8_t descriptor[168];")
    data=once(data,"bool issued=repeated &&","bool issued=!p->section841 && repeated &&")
    if release:
        data=once(data," if(!p->scroll_issued && !p->map_dirty && s->plan && s->plan->window",
                  " if(!p->section841 && !p->scroll_issued && !p->map_dirty && s->plan && s->plan->window")
    write(name,data)


def observe_raw(s,client,stop=False,damage=False):
    label=json.loads((client/"labels.json").read_bytes())
    hook=f"""local rows841=assert(io.open(ROOT..'/rows841.csv','w'))
local pending841=nil
pulse841=false
checkedMem527(function()
 local g,bank=word(0x1226),word(0x1034)
 assert(not packet and bank~=word(0x1032))
 local mask=word(0x1514)
 local row=0;while mask>1 do mask=mask>>1;row=row+1 end
 local src=regs[0x4302]+256*regs[0x4303]
 local dst=2*(regs[0x2116]+256*regs[0x2117])
 assert(regs[0x4300]==1 and regs[0x4301]==24 and regs[0x4304]==127 and regs[0x4305]==64 and regs[0x4306]==0)
 assert(src==word(0x1020)+0x6961+64*row and dst==(bank==0 and 0x5000 or 0x9000)+16*(row//2)+2*(row%2))
 pending841={{g,bank,row,dst,emu.getState().masterClock,emu.getState().frameCount,emu.getState()['ppu.scanline']}}
end,emu.callbackType.exec,{label['dma841']})
checkedMem527(function()
 if pending841 then
  local t=pending841;local expected=file('expected-'..t[1]..'.bin')
  for i=0,31 do for j=0,1 do
   assert(emu.read(t[4]+i*64+j,emu.memType.snesVideoRam)==expected:byte(1122+i*64+16*(t[3]//2)+2*(t[3]%2)+j),'early raw VRAM')
  end end
  local st=emu.getState();assert(t[6]==st.frameCount and t[7]>=225 and st['ppu.scanline']<=246)
  rows841:write(table.concat(t,',')..','..st.masterClock..'\\n');rows841:flush()
  if t[1]==910 and {str(stop).lower()} then pulse841=true end
  pending841=nil
 end
end,emu.callbackType.exec,{label['complete841']})
"""
    if damage:
        hook+=f"""local damaged841=false
checkedMem527(function()
 if word(0x1226)==910 and not damaged841 then
  local addr=0x10000+regs[0x4302]+256*regs[0x4303]
  emu.write(addr,rd(addr)~1,emu.memType.snesWorkRam);damaged841=true
 end end,emu.callbackType.exec,{label['check841']})
checkedMem527(function()
 if damaged841 then local f=assert(io.open(ROOT..'/stop841.txt','w'));f:write(emu.getState().masterClock);f:close() end
end,emu.callbackType.exec,{label['defer841']})
"""
    if stop or damage:
        s=once(s," if a==0x6001 then",""" if a==0x6001 then
  if pulse841 then
   pulse841=false
   local f=assert(io.open(ROOT..'/stop841.txt','w'));f:write(emu.getState().masterClock);f:close()
   return 128
  end""")
        hook+=f"""local savedCancel841=false
local function stopped841()
 if not savedCancel841 and word(0x1236)==1 and word(0x1226)==910 then
  savedCancel841=true
  for _,addr in ipairs({{0x1502,0x1504,0x1506,0x1512,0x14d0,0x14d2,0x14d4,0x14d6}}) do assert(word(addr)==0) end
  trace516:flush();local f=assert(io.open(ROOT..'/cancel841.txt','w'));f:write(emu.getState().masterClock);f:close();emu.stop(0)
 end end
checkedMem527(stopped841,emu.callbackType.exec,{label['service_done']})
checkedMem527(stopped841,emu.callbackType.exec,{label['stop523']})
"""
    return once(admission.observe(s),"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("mode",choices=("prepare","paired-client","demo","fixed","opening","refopening","coverage","pulse","table","identity"))
    parser.add_argument("phase",type=int,nargs="?",default=1)
    parser.add_argument("--raw",action="store_true")
    parser.add_argument("--scoped",action="store_true")
    parser.add_argument("--release",action="store_true")
    parser.add_argument("--pair",action="store_true")
    parser.add_argument("--stop-row",action="store_true")
    parser.add_argument("--damage-row",action="store_true")
    a=parser.parse_args()
    a.temp=Path.home()/"AppData/Local/Temp"
    a.budget=Path.home()/"Downloads/nes-budget-mmc826.txt"
    a.arm="palette"
    tag="841"+("pair" if a.pair else "")+("releaseC" if a.release else "checkedC" if a.scoped else "rawB" if a.raw else "section")+a.mode+("stop" if a.stop_row else "damage" if a.damage_row else "")
    if a.release:ARM=BASE.parent/"link-841release"
    a.raw=a.raw or a.scoped
    client=raw.SCOPED if a.scoped else raw.CLIENT if a.raw else admission.CLIENT
    if a.pair:
        assert a.scoped
        client=OUT/"client-paired-stop"
    if a.mode=="prepare":prepare(a.release)
    elif a.mode=="paired-client":
        with patch.object(pair,"CLIENT",OUT/"client-paired-stop"),patch.object(pair,"REFERENCE",raw.SCOPED):
            pair.receiver()
    elif a.mode in ("opening","refopening"):
        if a.mode=="refopening":client=REFERENCE
        def paired_oracle(s):
            with patch.object(pair,"CLIENT",client):return pair.oracle(s)
        with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]):
            main(PROBES/"nes-tile821/extra01","earlyB","jointmirror",a.phase,a.temp,arm=ARM/"src",
                 link_class=MirrorLink,client=client,client_hash=sha(client/"sink165.sfc"),
                 adapt_template=paired_oracle if a.pair and a.mode=="opening" else None)
    elif a.mode in ("coverage","pulse"):
        a.fault=a.mode
        reject(a,client,ARM,tag)
    elif a.mode in ("table","identity"):
        change=("if pb(0)==2 and pb(1)==5 and pw(10)==1505 then b[18]=0x7f end"
                if a.mode=="table" else "if pb(0)==3 then b[9]=b[9]~1 end")
        def corrupt(s):
            s=once(s,"local MODE='normal'","local MODE='fault841'")
            s=once(s,"local FAULT=905","local FAULT=910")
            return observe_raw(once(s,"  if MODE=='bad_mode'","  "+change+"\n  if MODE=='bad_mode'"),client)
        try:
            run(a.arm,a.phase,a.temp,a.budget,arm=ARM,client=client,tag=tag,adapt=corrupt)
        except (AssertionError,BrokenPipeError):
            folder=a.temp/f"nes-tile821-demoB-jointmirror-p{a.phase}-{tag}"
            rows=window(folder)
            assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
            assert [(r["op"],r["value"]) for r in rows if r["event"]=="ack" and r["value"]>=224]==[(3,224)]
            records=(folder/"admission838.txt").read_text().splitlines()
            assert any(v.startswith("910 record838 ") for v in records)==(a.mode=="identity")
            assert not any(v.startswith("910 reuse838 ") for v in records)
        else:
            raise AssertionError("bad table or identity was displayed")
    else:
        fixed=a.mode=="fixed"
        adapt=admission.isolated if fixed else admission.observe
        if a.raw:
            def adapt(s):
                if fixed:
                    before=(REFERENCE/"body.bin").read_bytes();after=(client/"body.bin").read_bytes()
                    writes=[f"emu.write({8192+i},{v},emu.memType.snesWorkRam)" for i,v in enumerate(after) if i>=len(before) or v!=before[i]]
                    s=once(s,"  lastStatus=ack[1];","  if pw(8)==909 and pb(0)==3 and ack[1]==1 then\n"+"\n".join(writes)+"\n  end\n  lastStatus=ack[1];")
                if a.pair:
                    with patch.object(pair,"CLIENT",client):s=pair.oracle(s)
                return observe_raw(s,client,a.stop_row,a.damage_row)
        try:
            run(a.arm,a.phase,a.temp,a.budget,arm=ARM,client=REFERENCE if fixed else client,tag=tag,adapt=adapt)
        except (AssertionError,OSError,TimeoutError):
            if not(a.stop_row or a.damage_row):raise
            f=a.temp/f"nes-tile821-demoB-jointmirror-p{a.phase}-{tag}"
            tick=int((f/"stop841.txt").read_text())
            assert int((f/"cancel841.txt").read_text())>=tick
            rows=window(f)
            assert not any(r["event"] in ("ppu_dma","ppu_last","reveal") and r["clock"]>=tick for r in rows)
            assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
        else:
            assert not(a.stop_row or a.damage_row)
