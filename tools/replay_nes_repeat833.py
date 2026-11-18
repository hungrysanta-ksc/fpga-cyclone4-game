"""Run both links with the real packet reader and an independent WRAM oracle."""
import argparse
import json
from pathlib import Path

from nes_repeat833 import OUT, PROBES
from analyze_nes_map830 import window
from nes_raw506 import once
from replay_nes_section832 import run
from replay_nes_seal831 import after_display2572
from check_nes_game478 import ELFFile
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR


def trace_credit(cpu):
    unit=""
    spans=[]
    with (cpu.a.arm/"obj-nes-100/sd2snes.elf").open("rb") as f:
        for s in ELFFile(f).get_section_by_name(".symtab").iter_symbols():
            if s["st_info"]["type"]=="STT_FILE":unit=s.name
            if s["st_info"]["type"]!="STT_FUNC":continue
            addr=s["st_value"]&~1
            if unit=="nes_sink_window184.c" and s.name=="status":status=addr
            if unit=="nes_sink_window184.c" or s.name.startswith(("nes_window184","nes_window532")):
                spans.append((addr,addr+s["st_size"],s.name))
    def enter(u,addr,size,data):
        if cpu.generation!=909:return
        pc=(u.reg_read(UC_ARM_REG_LR)&~1)-2
        owner=next(n for a,b,n in spans if a<=pc<b)
        with (cpu.a.out/"credit833.txt").open("a") as log:
            print(cpu.clock,owner,file=log)
    cpu.u.hook_add(UC_HOOK_CODE,enter,begin=status,end=status)


def verify_rejection(folder,fault):
    status=228 if fault=="stop" else 224
    rows=window(folder)
    assert [e["g"] for e in rows if e["event"]=="reveal"]==list(range(905,909))
    assert [(e["op"],e["value"]) for e in rows if e["event"]=="ack" and e["value"]>=224]==[(9,status)]
    assert not any(line.startswith("909 ") for line in (folder/"bundle833.txt").read_text().splitlines())
    # ARM can observe the error before the video harness writes its two-frame-later snapshot.
    if (folder/"result.json").exists():
        r=json.loads((folder/"result.json").read_bytes())
        assert r["passed"] and r["commits"]==4 and r["last_status"]==status
        assert (folder/"retained.rgb").read_bytes()==(folder/"frame-908.rgb").read_bytes()
    else:
        assert (folder/"fault.json").is_file()


def replay(mode,phase,temp,budget,fixed=False,fault=None,tag=None,*,client=None,arm=None,overlay_root=OUT,on_attach=trace_credit,force_repair=False,extra_trace=None):
    client=client or OUT/"client"
    label=json.loads((client/"labels.json").read_bytes())
    tag=tag or "833"+mode+("fixed" if fixed else "")+(fault or "")
    def adapt(s):
        if fixed:s=after_display2572(s,client)
        hook="""
local function bundle833() return packet and pb(0)==9 and pb(1)==5 end
local rows833=0
local stop833=false
local trace833=assert(io.open(ROOT..'/bundle833.txt','w'))
checkedMem527(function()
 if bundle833() then rows833=0 end
end,emu.callbackType.exec,EXPAND)
checkedMem527(function()
 if bundle833() then
  rows833=rows833+1
  DAMAGE
 end
end,emu.callbackType.exec,SERVICE)
checkedMem527(function()
 if bundle833() then
  assert(rows833==6 and pw(10)==1121 and pw(12)==10)
  local dst=0x10000+word(0x1020)+0x6500+1121
  for i=0,383 do
   local row=math.floor(i/64)
   assert(rd(dst+i)==pb(16+2*math.max(0,row-1)+i%2),'expanded WRAM mismatch')
  end
  trace833:write(pw(8)..' '..rows833..' '..emu.getState().masterClock..'\\n');trace833:flush()
 end
end,emu.callbackType.exec,DONE)
"""
        hook=hook.replace("EXPAND",str(label["expand833"])).replace("DONE",str(label["done833"])).replace("SERVICE",str(label["service833"]))
        action="if rows833==2 and pw(8)==909 then stop833=true end" if fault=="stop" else ""
        hook=hook.replace("DAMAGE",action)
        if fault=="damage":
            hook+=f"checkedMem527(function() if bundle833() and pw(8)==909 and rows833==1 then local a=0x10000+word(0x7a)+62;emu.write(a,rd(a)~1,emu.memType.snesWorkRam) end end,emu.callbackType.exec,{label['check833']})\n"
        if "repair834" in label:
            hook+="local repairs834=assert(io.open(ROOT..'/repairs834.txt','w'))\n"
            hook+=f"checkedMem527(function() if bundle833() then repairs834:write(pw(8)..' '..rows833..'\\n');repairs834:flush() end end,emu.callbackType.exec,{label['repair834']})\n"
            if force_repair or fault=="damage":
                hook+=f"local altered834=false;checkedMem527(function() if bundle833() and pw(8)==909 and rows833==1 and not altered834 then altered834=true;local a=0x10000+word(0x7a)+62;emu.write(a,pb(16)~1,emu.memType.snesWorkRam) end end,emu.callbackType.exec,{label['inspect834']})\n"
        anchor="checkedMem527(function()rpc()end"
        s=once(s,anchor,hook+anchor)
        if fault:
            s=once(s,"local MODE='normal'","local MODE='833"+fault+"'")
            s=once(s,"local FAULT=905","local FAULT=909")
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if stop833 then return 128 end")
            fields={"offset":11,"length":13,"reserved":15}
            if fault in fields:
                i=fields[fault]
                s=once(s,"  if MODE=='bad_mode'",f"  if pb(0)==9 and pb(1)==5 then b[{i}]=b[{i}]~2 end\n  if MODE=='bad_mode'")
            if fault=="damage":
                # Corrupt once, even though the comparison loop revisits its PC.
                s=once(s,"and rows833==1 then local","and rows833==1 and not injected833 then injected833=true;local")
        return extra_trace(s) if extra_trace else s
    folder=temp/f"nes-tile821-demoB-jointmirror-p{phase}-{tag}"
    if mode=="base":
        assert not fixed and not fault
        run("base",phase,temp,budget,tag=tag,on_attach=on_attach)
        return
    try:
        run(mode,phase,temp,budget,fixed,arm=arm or PROBES/"nes-output823"/("link-833"+mode),
            overlay_root=overlay_root,tag=tag,client=None if fixed else client,adapt=adapt,on_attach=on_attach)
    except (AssertionError,BrokenPipeError):
        if not fault:raise
        verify_rejection(folder,fault)
    else:
        assert not fault


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("base","stock","early","mid","first","oam","front"))
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("--fixed",action="store_true")
    p.add_argument("--fault",choices=("damage","stop","offset","length","reserved"))
    p.add_argument("--tag")
    replay(**vars(p.parse_args()))
