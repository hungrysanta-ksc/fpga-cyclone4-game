"""Measure a bounded accepted-map DMA after the held SEAL passes its checks."""
import argparse
import json
import sys
from unittest.mock import patch

import nes_palette846 as arm
from nes_window837 import ORIGIN, PROBES, codec, pack
from build_nes_trace_replay import Code
from nes_raw506 import once

OUT = PROBES / "nes-sealdma847"
REFERENCE = arm.base.section.REFERENCE
CLIENT = OUT / "client"
SCOPE = 0x1516


def build(parent=REFERENCE):
    body = bytearray((parent / "body.bin").read_bytes())
    labels = json.loads((parent / "labels.json").read_bytes())
    c = Code(ORIGIN + len(body)); c.labels.update(labels)

    def hook(name, expected, target, opcode=0x4c):
        i = labels[name] - ORIGIN
        expected = bytes.fromhex(expected)
        assert body[i:i+len(expected)] == expected
        body[i:i+len(expected)] = bytes([opcode]) + (c.labels[target]&65535).to_bytes(2,"little") + bytes([0xea])*(len(expected)-3)

    # No admission state is inferred from a queued command. The caller only
    # reaches local165_entry after SEAL identity, semantics and coverage pass.
    c.label("checked847")
    c.emit(0xa9,1,0); c.absolute(0x8d,SCOPE)
    c.absolute(0x20,labels["prefix523"]&65535)
    c.absolute(0x9c,SCOPE)
    c.emit(0xe2,0x20); c.store(0x1025,1); c.emit(0xc2,0x20,0x60)
    hook("local165_entry","e220a9018d2510c22060","checked847")

    c.label("head847")
    c.absolute(0xad,0x6000); c.emit(0x29,1); c.branch(0xf0,"allow847")
    c.absolute(0xad,SCOPE); c.branch(0xf0,"defer847")
    # Only this already-validated SEAL may hold the queue during the map
    # transfer. An ordinary head never gets this exception. STOP is tested
    # by the original priority524 immediately before this entry.
    c.absolute(0xad,0x1200); c.emit(0xc9,3); c.branch(0xd0,"defer847")
    c.absolute(0xad,0x1201); c.branch(0xd0,"defer847")
    c.long(0xbf,0x7e4001); c.emit(0x29,0x70,0xc9,0x50); c.branch(0xd0,"defer847")
    c.label("allow847"); c.jump("grant524")
    c.label("defer847"); c.jump("skip8_523")
    hook("ready524","ad00602901d056","head847")
    for name in ("begin","invalidate635"):
        i=labels[name]-ORIGIN
        expected=body[i:i+3].hex()
        assert body[i] in (0x9c,0x20,0x4c), (name,expected)
        c.label(name+"847"); c.absolute(0x9c,SCOPE)
        c.emit(*bytes.fromhex(expected),0x60)
        hook(name,expected,name+"847",0x20)
    body.extend(c.finish())
    used=260+len(pack(bytes(body),0))
    with patch.object(codec,"pack",pack),patch.object(codec,"STORED",max(5056,used)):
        codec.build(PROBES/"nes-reuse635/client04",CLIENT,edit_body=lambda *_:bytes(body),
                    allow_extension=True,body_limit=8192,prefix_sizes=[0],medium_pages=True,
                    short_errors=True,boot_bytes=260,fast_backrefs=True)
    (CLIENT/"labels.json").write_text(json.dumps(c.labels,indent=2)+"\n")
    (CLIENT/"cost.json").write_text(json.dumps(dict(ROM_bytes=used+64,limit=5120,WRAM_B=2,
        extra_body_B=len(body)-len((parent/"body.bin").read_bytes()),
        parent_SHA256=arm.base.section.sha(parent/"sink165.sfc")),indent=2)+"\n")


def observe(s, fixed=False, fault=None):
    labels=json.loads((CLIENT/"labels.json").read_bytes())
    if 'pair839' in labels:
        with patch.object(arm.base.section.pair,'CLIENT',CLIENT):
            s=arm.base.section.pair.oracle(s)
        s=arm.base.section.observe_raw(s,CLIENT,False,False)
    if fixed:
        before=(REFERENCE/"body.bin").read_bytes(); after=(CLIENT/"body.bin").read_bytes()
        edits=[f"emu.write({8192+i},{v},emu.memType.snesWorkRam)" for i,v in enumerate(after)
               if i>=len(before) or before[i]!=v]
        edits.append(f"emu.write({SCOPE},0,emu.memType.snesWorkRam)")
        edits.append(f"emu.write({SCOPE+1},0,emu.memType.snesWorkRam)")
        s=once(s,"  lastStatus=ack[1];","  if pw(8)==909 and pb(0)==3 and ack[1]==1 then\n"+
               "\n".join(edits)+"\n  end\n  lastStatus=ack[1];")
    # Keep per-byte source, inactive VRAM, receipt and final-image assertions.
    # Only replace the empty-head assertion for the checked SEAL scope.
    s=once(s,"assert(not packet and not pending526",f"""assert((not packet or
  (pb(0)==3 and pb(1)==0 and word({SCOPE})==1 and checked847==pw(8))) and not pending526""")
    hook=f"""local checked847=nil
local trace847=assert(io.open(ROOT..'/seal847.txt','w'))
checkedMem527(function()
 if packet then
  checked847=pw(8)
  trace847:write(string.format('%d checked %d\\n',pw(8),emu.getState().masterClock));trace847:flush()
 end
end,emu.callbackType.exec,{labels['checked847']})
checkedMem527(function()
 if packet and word({SCOPE})==1 then
  assert(pb(0)==3 and checked847==pw(8))
  local x=emu.getState()['cpu.x']
  assert((word(0x4000+x)&0x7000)==0x5000)
  trace847:write(string.format('%d map %d %d\\n',pw(8),emu.getState().masterClock,regs[0x4305]+256*regs[0x4306]));trace847:flush()
 end
end,emu.callbackType.exec,{labels['grant524']})
"""
    # The scope variable must precede the existing DMA observer closure.
    s=once(s,"local accepted526,copied526=", "local checked847=nil\nlocal accepted526,copied526=")
    hook=hook.replace("local checked847=nil\n","")
    if fault:
        s=once(s,"local MODE='normal'",f"local MODE='847{fault}'")
        s=once(s,"local FAULT=905","local FAULT=910")
        if fault=="stop":
            hook+=f"""local pulse847=false
checkedMem527(function()
 if packet and pw(8)==910 and word({SCOPE})==1 then pulse847=true end
end,emu.callbackType.exec,{labels['priority524']})
"""
            # Define pulse847 before bus-read closures, not merely before RPC.
            hook=hook.replace("local pulse847=false\n","")
            s=once(s,"local MODE='847stop'","local pulse847=false\nlocal MODE='847stop'")
            s=once(s," if a==0x6001 then",""" if a==0x6001 then
  if pulse847 then
   pulse847=false
   local f=assert(io.open(ROOT..'/stop847.txt','w'));f:write(emu.getState().masterClock);f:close()
   return 128
  end""")
        elif fault=="coverage":
            hook+=f"""checkedMem527(function()
 if packet and pw(8)==910 and pb(0)==3 then emu.write(0x1320+word(0x1254),0,emu.memType.snesWorkRam) end
end,emu.callbackType.exec,{labels['coverage212']})
"""
        elif fault=="identity":
            s=once(s,"  if MODE=='bad_mode'","  if pb(0)==3 then b[5]=b[5]~1 end\n  if MODE=='bad_mode'")
        elif fault=="table":
            hook+=f"""checkedMem527(function()
 if packet and pw(8)==910 and pb(0)==3 then
  emu.write(0x10000+word(0x1020)+0x6500,255,emu.memType.snesWorkRam)
 end
end,emu.callbackType.exec,{labels['validate181']})
"""
        else:
            raise ValueError(fault)
        s=once(s,"  lastStatus=ack[1];",f"""  if pw(8)==910 and ack[1]>=224 then
   assert(word({SCOPE})==0,'scope leaked past cancellation')
  end
  lastStatus=ack[1];""")
    return once(s,"checkedMem527(function()rpc()end",hook+"checkedMem527(function()rpc()end")


def run(phase, fixed, fault=None, raw=False):
    tag="847"+('raw' if raw else '')+(fault or ("fixed" if fixed else "boot"))
    with patch.object(arm.base.replay,"TraceLink",arm.base.Trace):
        try:
            arm.base.replay.run("palette",phase,arm.base.TEMP,arm.base.BUDGET,arm=arm.link("queued"),
                client=REFERENCE if fixed else CLIENT,tag=tag,adapt=lambda s:observe(s,fixed,fault),on_attach=arm.watch)
        except (AssertionError,BrokenPipeError):
            if not fault:raise
            from analyze_nes_map830 import window
            folder=arm.base.TEMP/f"nes-tile821-demoB-jointmirror-p{phase}-{tag}"
            rows=window(folder)
            assert [r['g'] for r in rows if r['event']=='reveal']==list(range(905,910))
            errors=[r for r in rows if r['event']=='ack' and r['value']>=224]
            assert [(r['g'],r['op'],r['value']) for r in errors]==[(910,3,228 if fault=='stop' else 224)]
            if fault=='stop':
                tick=int((folder/'stop847.txt').read_text())
                assert not any(r['clock']>=tick and r['event'] in ('ppu_dma','ppu_last','reveal') for r in rows)
            else:
                assert not (folder/'seal847.txt').read_text().strip()
            print('PASS847',fault,phase)
        else:
            assert not fault,'injected fault accepted'


def opening(phase):
    section=arm.base.section
    with patch.object(sys,'argv',['replay','','','','','', '847opening',str(arm.base.BUDGET)]):
        section.main(PROBES/'nes-tile821/extra01','earlyB','jointmirror',phase,arm.base.TEMP,
                     arm=arm.link('queued')/'src',link_class=section.MirrorLink,
                     client=CLIENT,client_hash=section.sha(CLIENT/'sink165.sfc'),
                     adapt_template=observe)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("mode",choices=("build","fixed","boot","opening","stop","coverage","identity","table"));p.add_argument("phase",type=int,nargs="?",default=1)
    p.add_argument('--raw',action='store_true')
    a=p.parse_args()
    if a.raw:CLIENT=OUT/'client-raw'
    if a.mode=='build':build(arm.base.CLIENT if a.raw else REFERENCE)
    elif a.mode=='opening':opening(a.phase)
    else:run(a.phase,a.mode not in ('boot',),None if a.mode in ('boot','fixed') else a.mode,a.raw)
