"""Isolate a tail section scheduling change from early OBJ descriptor service."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch
from build_nes_trace_replay import Code
from nes_window837 import ORIGIN, OUT as OLD, PROBES, codec, pack
from nes_raw506 import once, sha
from replay_nes_window837 import MirrorLink, main, reject
from replay_nes_charge836 import trace
from replay_nes_repeat833 import replay

OUT = PROBES/"nes-pair839"
BASE = PROBES/"nes-output823/link-837palette"
ARM = BASE.parent/"link-839tail"
REFERENCE = OLD / "client-sticky"
CLIENT = OUT / "client"



def sender(gated=False):
    src = BASE / "src/nes_native_sink165.c"
    data = src.read_text()
    # Only independent sections may change order. Section 5's cursor,
    # checked bulk service, the map progress guard and SEAL stay authoritative.
    data = once(data, " bool same=same635(s,p);", """ bool same=same635(s,p);
 bool tail_first=repeated && !same && !p->map_dirty && !p->scroll_issued &&
    s->plan && s->plan->bank_history==2 &&
    ((uint32_t)(r->map_upload>>32)&0x7ffffu)==0x7ffffu;
 if(tail_first)goto section5_839;
 ordinary839:""")
    data = once(data," if(!p->scroll_issued && !span(s,5,0,p->hdma,p->hdma_size))return false;",
                " if(tail_first)goto seal839;\n section5_839:\n if(!p->scroll_issued && !span(s,5,0,p->hdma,p->hdma_size))return false;")
    data = once(data," uint8_t descriptor[168];"," if(tail_first)goto ordinary839;\n seal839: ;\n uint8_t descriptor[168];")
    if gated:
        # The progress bit belongs to the retired head. Observe it before
        # publishing the next palette, which would replace that identity.
        first=data.index(" if(!p->scroll_issued && !p->map_dirty && s->plan && s->plan->window")
        last=data.index("){",first)
        condition=data[first+4:last]
        data=once(data," bool tail_first=repeated && !same && !p->map_dirty && !p->scroll_issued &&\n    s->plan && s->plan->bank_history==2 &&\n    ((uint32_t)(r->map_upload>>32)&0x7ffffu)==0x7ffffu;",
                  " bool map_window="+condition+";\n bool tail_first=map_window && repeated && !same;")
        data=once(data," if("+condition+"){"," if(map_window){")
        palette="if(!span(s,3,0,p->cgram,512))return false;"
        data=once(data,palette,"if(!tail_first)"+palette)
        data=once(data," if(!oam227(s,p->oam))"," if(tail_first)"+palette+"\n if(!oam227(s,p->oam))")
    dest = OUT/("gated" if gated else "tail")
    dest.mkdir(parents=True,exist_ok=True)
    (dest/src.name).write_text(data,newline="\n")



def receiver():
    body=bytearray((REFERENCE/"body.bin").read_bytes())
    labels=json.loads((REFERENCE/"labels.json").read_bytes())
    c=Code(ORIGIN+len(body))
    c.labels.update(labels)
    start=c.labels["dma_retired680"]+8
    off=start-ORIGIN
    assert body[off:off+7]==bytes.fromhex("a9a58d1d60c220")
    c.label("handoff839")
    c.emit(*body[off:off+7])
    c.absolute(0x20,labels["service"]&65535)
    c.branch(0xd0,"finish839")
    c.absolute(0xad,0x1250)
    c.absolute(0xcd,0x1252)
    c.branch(0xf0,"finish839")
    # Only the accepted final OBJ range. Once its DMA returns whole526 pops
    # the range; later adjacent packets must then create a fresh descriptor.
    c.emit(0x38,0xe9,8,0,0xaa)
    c.long(0xbf,0x7e4000)
    c.emit(0x29,0,0x70,0xc9,0,0x40)
    c.branch(0xd0,"finish839")
    c.long(0xbf,0x7e4004)
    c.emit(0xc9,0x21,2)
    c.branch(0xb0,"finish839")
    c.emit(0xa8,0xe2,0x20)
    # Same latch handshake as selected526. Take a new beam sample after the
    # map and allow at most 544 bytes before the original queue/STOP check.
    c.absolute(0xad,0x4212);c.branch(0x10,"defer839")
    for prior in (True,False):
        c.absolute(0xad,0x213f if prior else 0x2137)
        c.absolute(0xad,0x213f);c.emit(0x89,0x40)
        c.branch(0xd0 if prior else 0xf0,"defer839")
    c.absolute(0xad,0x213d);c.emit(0xeb);c.absolute(0xad,0x213d);c.emit(0x29,1)
    c.branch(0xd0,"defer839");c.emit(0xeb,0xc9,225);c.branch(0x90,"defer839")
    c.emit(0xc9,238);c.branch(0xb0,"defer839")
    c.label("pair839");c.jump("map_beam_ok526")
    c.label("defer839");c.emit(0xc2,0x20)
    c.label("finish839");c.jump("no_event680")
    # Do not overwrite no_event680: non-map retirements jump directly there.
    body[off:off+7]=bytes([0x4c])+(c.labels["handoff839"]&65535).to_bytes(2,"little")+bytes(4)
    body.extend(c.finish())
    used=260+len(pack(bytes(body),0))
    with patch.object(codec,"pack",pack),patch.object(codec,"STORED",max(5056,used)):
        codec.build(PROBES/"nes-reuse635/client04",CLIENT,edit_body=lambda *_:bytes(body),
                    allow_extension=True,body_limit=8192,prefix_sizes=[0],medium_pages=True,
                    short_errors=True,boot_bytes=260,fast_backrefs=True)
    (CLIENT/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")
    info=json.loads((CLIENT/"build.json").read_bytes())
    info.update(program_bytes=used+64,physical_ROM_B=used+64,physical_free_B=5056-used)
    (CLIENT/"build.json").write_text(json.dumps(info,indent=2)+"\n")


def oracle(s):
    # For this path the real X register points at the accepted tail, while
    # the normal consumer selects the head. Verify the same independent byte
    # and post-DMA VRAM checks for both, including STOP/queue cancellation.
    label=json.loads((CLIENT/"labels.json").read_bytes())
    s=once(s,"local bytes532={}",f"""local selected839=false
checkedMem527(function()selected839=true end,emu.callbackType.exec,{label['pair839']})
checkedMem527(function()selected839=false end,emu.callbackType.exec,{label['prefix523']})
local bytes532={{}}""")
    old="  assert(not tile532 and i<=tail and (i<tail or n<=160))"
    new="""  if selected839 then
   local st=emu.getState()
   i=st['cpu.x']
   assert(not tile532 and i==tail and n>0 and n<=544 and (src&0x7000)==0x4000)
   assert(beam685.frame==st.frameCount and beam685.line>=225 and beam685.line<=237)
   assert(st.masterClock-beam685.clock<3*1364 and st['ppu.scanline']<246)
   selected839=false
  else
   assert(not tile532 and i<=tail and (i<tail or n<=160))
  end"""
    return once(s,old,new)


def fixed_pair(s):
    # Diagnostic isolation: 837 executes from reset through 2576 final ACK.
    before=(REFERENCE/"body.bin").read_bytes()
    after=(CLIENT/"body.bin").read_bytes()
    edits=[f"emu.write({8192+n},{v},emu.memType.snesWorkRam)"
           for n,v in enumerate(after) if n>=len(before) or before[n]!=v]
    mark="  lastStatus=ack[1];"
    return oracle(once(s,mark,"  if pw(8)==909 and pb(0)==3 and ack[1]==1 then\n"
                       +"\n".join(edits)+"\n  end\n"+mark))


def stop_pair(a, *, arm=BASE, tag="839stopReturn"):
    from analyze_nes_map830 import window
    from replay_nes_section832 import run
    label=json.loads((CLIENT/"labels.json").read_bytes())
    def inject(s):
        s=oracle(s)
        s=once(s,"local MODE='normal'","local MODE='839stop'")
        s=once(s,"local FAULT=905","local FAULT=910")
        s=once(s," if a==0x6001 then",""" if a==0x6001 then
  if pulse839 then
   pulse839=false;observed839=true
   local f=assert(io.open(ROOT..'/stop839.txt','w'));f:write(emu.getState().masterClock);f:close()
   return 128
  end""")
        hook=f"""checkedMem527(function()
 if word(0x1226)==910 and emu.getState()['cpu.y']==544 then pulse839=true end
end,emu.callbackType.exec,{label['pair839']})
checkedMem527(function()
 if observed839 then
  assert(not packet and word(0x1236)==1 and commits==5)
  for addr=0x14d0,0x14d8,2 do assert(word(addr)==0) end
  trace516:flush()
  local f=assert(io.open(ROOT..'/stop-return839.txt','w'))
  f:write(emu.getState().masterClock);f:close()
  emu.stop(0)
 end
end,emu.callbackType.exec,{label['stop523']})
"""
        return once(s,"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")
    try:
        run("palette",a.phase,a.temp,a.budget,arm=arm,client=CLIENT,tag=tag,adapt=inject)
    except (AssertionError,TimeoutError,OSError):
        folder=a.temp/f"nes-tile821-demoB-jointmirror-p{a.phase}-{tag}"
        rows=window(folder)
        stop=int((folder/"stop839.txt").read_text())
        assert [r["g"] for r in rows if r["event"]=="reveal"]==list(range(905,910))
        assert not any(r["event"] in ("ppu_dma","ppu_last") and r["clock"]>=stop for r in rows)
        # Empty-queue STOP has no packet identity to acknowledge.
        assert int((folder/"stop-return839.txt").read_text())>stop
        assert not any(r["event"]=="ack" and r["clock"]>=stop for r in rows)
    else:
        raise AssertionError("missed one-read STOP")


def run_trial(a):
    client=REFERENCE if a.mode=="tail" else CLIENT
    arm=BASE if a.mode=="pair" else ARM.parent/"link-839gated" if a.mode=="gated" else ARM
    a.arm="palette"
    a.temp=Path.home()/"AppData/Local/Temp"
    a.budget=Path.home()/"Downloads/nes-budget-mmc826.txt"
    tag=("839" if a.mode=="tail" else "839x")+a.mode
    if a.mode=="fixed":
        from replay_nes_section832 import run
        run("palette",a.phase,a.temp,a.budget,arm=BASE,client=REFERENCE,tag="839fixed",adapt=fixed_pair)
    elif a.mode=="stop-pair":
        stop_pair(a)
    elif a.fault in ("pulse","coverage"):
        import replay_nes_window837 as base_test
        original=base_test.run
        def checked(*args,adapt,**kwargs):
            return original(*args,adapt=adapt if client==REFERENCE else lambda text:oracle(adapt(text)),**kwargs)
        with patch.object(base_test,"run",checked):
            reject(a,client,arm,tag+a.fault)
    elif a.opening:
        with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]):
            main(PROBES/"nes-tile821/extra01","earlyB","jointmirror",a.phase,a.temp,
                 arm=arm/"src",link_class=MirrorLink,client=client,client_hash=sha(client/"sink165.sfc"),
                 adapt_template=None if client==REFERENCE else oracle)
    else:
        replay(a.arm,a.phase,a.temp,a.budget,tag=tag+(a.fault or ""),client=client,arm=arm,
               fault=a.fault,extra_trace=lambda s:trace(client,False)(s if client==REFERENCE else oracle(s)))


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mode",choices=("sender","receiver","pair","tail","both","gated-sender","gated","fixed","stop-pair"))
    p.add_argument("phase",nargs="?",type=int,choices=(1,2),default=1)
    p.add_argument("--opening",action="store_true")
    p.add_argument("--fault",choices=("pulse","coverage","damage"))
    a=p.parse_args()
    if a.mode in ("sender","gated-sender"):sender(a.mode=="gated-sender")
    elif a.mode=="receiver":receiver()
    else:run_trial(a)
