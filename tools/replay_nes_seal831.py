"""Replay the independent SEAL verifier with the original or bundled sender."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once, sha
from nes_seal831 import OUT, PROBES
from replay_nes_output822 import MirrorLink
from replay_nes_tile821 import main


def run(a):
    short_sender=a.sender in ("short","splitshort")
    version=a.rom or ("short" if short_sender else "checked")
    if short_sender and version not in ("wire","short"):
        raise ValueError("The 56-byte SEAL requires the matching receiver.")
    stock=PROBES/"nes-output815/client"
    client={"stock":stock,"checked":OUT/"client","short":OUT/"client-short",
            "pad":OUT/"client-pad","wire":OUT/"client-wire","tail":OUT/"client-tail"}[version]
    link={"original":"link-826","joined":"link-830joined"}.get(a.sender,"link-831"+a.sender)
    arm = PROBES/"nes-output823"/link
    tag = "831"+a.sender+(a.rom or "")+("-guard-"+a.fault if a.fault else "")
    if a.after2572:
        assert a.sender=="original" and version in ("checked","tail") and not a.fault
        tag+="fixed"
    def inject(s):
        if a.after2572:
            # Diagnostic only. Execute the full MMC826 boot and previous
            # generations. On return of 2572's final ACK install only changed
            # executable WRAM bytes, leaving state, events and clocks intact.
            before=(PROBES/"nes-output815/client/body.bin").read_bytes()
            after=(client/"body.bin").read_bytes()
            edits=[f"emu.write({0x2000+i},{b},emu.memType.snesWorkRam)" for i,b in enumerate(after)
                   if i>=len(before) or before[i]!=b]
            s=once(s,"  lastStatus=ack[1];","  if pw(8)==908 and pb(0)==3 and ack[1]==1 then\n"+"\n".join(edits)+"\n  end\n  lastStatus=ack[1];")
        if version in ("pad","short"):
            # The monitor verifies every physical byte even on a reuse hit,
            # and permits zero DMA bytes only after the actual hit branch.
            labels=json.loads((client/"labels.json").read_bytes())
            anchor="checkedMem527(function()rpc()end"
            s=once(s,anchor,"local padHit831=false\ncheckedMem527(function()padHit831=true end,emu.callbackType.exec,"+str(labels["hit647"])+")\n"+anchor)
            s=once(s,"fillBytes545==pw(14) and fillServiced545","(fillBytes545==pw(14) or (padHit831 and fillBytes545==0 and pb(0)==5 and pb(1)==5 and pw(16)==0 and pw(10)+pw(14)==1121)) and fillServiced545")
            s=once(s,"for j=0,fillBytes545-1 do","for j=0,pw(14)-1 do")
            s=once(s,"  fillBytes545=0;fillServiced545=false","  padHit831=false;fillBytes545=0;fillServiced545=false")
        if not a.fault:
            return s
        labels=json.loads((client/"labels.json").read_bytes())
        s=once(s,"local MODE='normal'",f"local MODE='831{a.fault}'")
        s=once(s,"local FAULT=905","local FAULT=909")
        anchor="checkedMem527(function()rpc()end"
        if a.fault=="stop":
            s=once(s," if a==0x6001 then"," if a==0x6001 then\n  if packet and pw(8)==909 and pb(0)==3 then return 128 end")
        else:
            # Corrupt an independently accumulated required bit or an actual
            # second HDMA table. The sender and SEAL head remain intact.
            callback,statement={
                "coverage":("coverage212","emu.write(0x1320+word(0x1254),0,emu.memType.snesWorkRam)"),
                "high":("coverage212","emu.write(0x13a0+word(0x1254),0,emu.memType.snesWorkRam)"),
                "width":("seal","emu.write(0x120c,54,emu.memType.snesWorkRam)"),
                "table":("table181","emu.write(0x10000+word(0x70)+81,255,emu.memType.snesWorkRam)"),
            }[a.fault]
            pc=labels[callback]
            s=once(s,anchor,f"checkedMem527(function() if packet and pw(8)==909 then {statement} end end,emu.callbackType.exec,{pc})\n"+anchor)
        return once(s,"lastStatus=ack[1];sample516", """if ack[1]>=224 then
   assert(word(0x1248)==4 and word(0x124a)==0 and commits==4)
   local f=assert(io.open(ROOT..'/rejected831.txt','w'))
   f:write(string.format('%d %d %d',commits,ack[1],pw(8)));f:close()
  end
  lastStatus=ack[1];sample516""")
    with patch.object(sys,"argv",["replay","","","","","",tag,str(a.budget)]):
        boot=stock if a.after2572 else client
        try:
            main(PROBES/"nes-tile821/demo-extra01","demoB","jointmirror",a.phase,a.temp,
                 arm=arm/"src",client=boot,client_hash=sha(boot/"sink165.sfc"),
                 link_class=MirrorLink,adapt_template=inject)
        except (AssertionError,BrokenPipeError):
            if not a.fault:
                raise
            folder=a.temp/f"nes-tile821-demoB-jointmirror-p{a.phase}-{tag}"
            assert (folder/"rejected831.txt").read_text()==f"4 {228 if a.fault=='stop' else 224} 909"
            assert (folder/"fault.json").is_file()
        else:
            assert not a.fault


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("sender",choices=("original","joined","early","short","split","lateoam","splitshort"))
    p.add_argument("phase",type=int,choices=(1,2))
    p.add_argument("temp",type=Path)
    p.add_argument("budget",type=Path)
    p.add_argument("--fault",choices=("coverage","high","width","table","stop"))
    rom=p.add_mutually_exclusive_group()
    for name in ("stock","tail","pad","wire"):
        rom.add_argument("--"+name,action="store_const",dest="rom",const=name)
    p.add_argument("--after2572",action="store_true")
    run(p.parse_args())
