"""Replay 912 with a real nonadjacent OBJ join and a free priority-order control."""
import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path

from build_nes_trace_replay import Code
from check_nes_blank959 import directory, sha
from nes_blank959 import ORIGIN
from nes_hdma990 import PACKED
from nes_raw506 import once


def join_body():
    # Entered after successful SEAL checks, before the raw descriptor is appended.
    # Last and fourth-last must be adjacent in both spaces, and the intervening
    # two writes must lie wholly outside the merged destination. Retired entries
    # are excluded. Existing STOP, beam and DMA budget checks run on the result.
    labels = json.loads((PACKED/"labels.json").read_bytes())
    start = labels["upload165_entry"]
    data = (PACKED/"body.bin").read_bytes()
    assert data[start-ORIGIN:start-ORIGIN+3] == bytes.fromhex("ad4012")
    c = Code(ORIGIN + len(data))
    def imm(n):
        c.emit(0xc9); c.word(n)
    c.absolute(0xad,0x1250); c.emit(0x38); c.absolute(0xed,0x1252)
    imm(32); c.branch(0xb0,"enough"); c.jump("done"); c.label("enough")
    c.absolute(0xad,0x1250); c.emit(0x38,0xe9,32,0,0xaa)
    # Begin in OBJ staging ($4xxx or $Cxxx); the second range must
    # continue both source and destination exactly.
    c.long(0xbf,0x7e4000); c.emit(0x29,0,0x70); imm(0x4000); c.branch(0xf0,"obj"); c.jump("done"); c.label("obj")
    for field in (0,2):
        c.long(0xbf,0x7e4000+field); c.emit(0x18); c.long(0x7f,0x7e4004)
        c.branch(0xb0,"done"); c.long(0xdf,0x7e4018+field); c.branch(0xd0,"done")
    # Exclusive end in Y, lower bound in the immutable descriptor itself.
    c.long(0xbf,0x7e401a); c.emit(0x18); c.long(0x7f,0x7e401c)
    c.branch(0xb0,"done"); c.emit(0xa8)
    for off in (8,16):
        c.emit(0x98); c.long(0xdf,0x7e4002+off)
        c.branch(0x90,f"clear{off}"); c.branch(0xf0,f"clear{off}")
        c.long(0xbf,0x7e4002+off); c.emit(0x18); c.long(0x7f,0x7e4004+off)
        c.branch(0xb0,"done"); c.long(0xdf,0x7e4002)
        c.branch(0xf0,f"clear{off}"); c.branch(0xb0,"done")
        c.label(f"clear{off}")
    c.long(0xbf,0x7e4004); c.emit(0x18); c.long(0x7f,0x7e401c)
    imm(2049); c.branch(0xb0,"done"); c.long(0x9f,0x7e4004)
    c.absolute(0xad,0x1250); c.emit(0x38,0xe9,8,0); c.absolute(0x8d,0x1250)
    c.label("done"); c.absolute(0xad,0x1240); c.emit(0x60)
    return start,c.base,c.finish()


def boundary_guard(labels, address):
    c=Code(address)
    c.absolute(0xec,0x103a)
    c.branch(0xb0,"group")
    c.absolute(0x20,labels["service"]&65535)
    c.branch(0xf0,"next")
    c.absolute(0x4c,labels["cancel169"]&65535)
    c.label("next"); c.absolute(0x4c,labels["upload_loop212"]&65535)
    c.label("group"); c.absolute(0x4c,labels["group538"]&65535)
    return c.finish()


def instrument(lua, mode):
    anchor = "packet=requests[index];sample516(\"load\");"
    if mode in ("join","fresh","freshjoin","guardjoin"):
        pc, dest, body = join_body()
        writes = {}
        if mode in ("join","freshjoin","guardjoin"):
            writes.update({pc:bytes((0x20,dest&255,dest>>8&255)),dest:body})
        if mode=="guardjoin":
            labels=json.loads((PACKED/"labels.json").read_bytes())
            entry=labels["raw_advance489"]+9
            code=(PACKED/"body.bin").read_bytes()
            assert code[entry-ORIGIN:entry-ORIGIN+8]==bytes.fromhex("ec 3a 10 90 b7 4c 0c 2b")
            guard=dest+len(body)
            writes[entry]=bytes((0x4c,guard&255,guard>>8&255))
            writes[guard]=boundary_guard(labels,guard)
        if mode in ("fresh","freshjoin"):
            # Budget oracle: force the stock serviced fresh-blank wait before
            # the entire group, preserving its actual transfer and STOP costs.
            labels=json.loads((PACKED/"labels.json").read_bytes())
            original=(PACKED/"body.bin").read_bytes()
            pos=labels["group538"]+16
            assert original[pos-ORIGIN:pos-ORIGIN+2]==bytes.fromhex("f0 6b")
            writes[pos]=b"\x80"
            pos=ORIGIN+original.index(bytes.fromhex("20 ec 38"), labels["prepare665"]-ORIGIN,labels["prepare665"]-ORIGIN+28)
            assert original[pos-ORIGIN:pos-ORIGIN+3]==bytes.fromhex("20 ec 38")
            writes[pos+1]=(labels["wait169"]&65535).to_bytes(2,"little")
        patch = []
        for address, data in writes.items():
            patch += [f"emu.write({address+i-0x7e0000},{v},emu.memType.snesWorkRam)" for i,v in enumerate(data)]
        lua = once(lua,anchor,anchor+"if pb(0)==3 and pw(8)==912 then "+";".join(patch)+" end;")
    # At group entry, the checked raw descriptor has been appended. Record once.
    priority = mode in ("priority","rawfirst")
    hook = """
local inspected1000=false
checkedMem527(function()
 if inspected1000 or not packet or pw(8)~=912 or pb(0)~=3 then return end
 inspected1000=true
 local f=assert(io.open(ROOT..'/descriptors.txt','w'))
 local list={}
 for i=word(0x1252),word(0x1250)-8,8 do
  f:write(word(0x4000+i),' ',word(0x4002+i),' ',word(0x4004+i),'\\n')
  local item={}
  for b=0,7 do item[#item+1]=rd(0x4000+i+b) end
  list[#list+1]=item
 end
 f:close()
 PRIORITY
end,emu.callbackType.exec,0x7e2b0c)
"""
    action = """
 assert(#list==9 and word(0x1252)==0 and word(0x4034)==32 and word(0x403c)==128)
 -- Move the last two OBJ ranges to the front. Raw stays last because its
 -- handler has a different PPU addressing mode. This permutation is free.
 for i,old in ipairs({7,8,1,2,3,4,5,6,9}) do
  for j,v in ipairs(list[old]) do emu.write(0x4000+(i-1)*8+j-1,v,emu.memType.snesWorkRam) end
 end
""" if priority else ""
    if mode == "rawfirst":
        action = action.replace("{7,8,1,2,3,4,5,6,9}","{9,7,8,1,2,3,4,5,6}")
    mark = "checkedMem527(function()sample516('upload165_entry')end,emu.callbackType.exec,8268414)"
    return once(lua,mark,mark+"\n"+hook.replace("PRIORITY",action))


def run(temp, phase, mode, fault=None, earliest_begin=False):
    src = temp/f"nes-ready999-bank-0-p{phase}"
    out = temp/(f"nes-dma1000-{mode}-p{phase}" + ("-"+fault if fault else "") + ("-begin" if earliest_begin else ""))
    out.mkdir()
    lua = once((src/"capture.lua").read_text(), json.dumps(src.as_posix()), json.dumps(out.as_posix()))
    if fault:
        lua=once(lua,"local MODE='normal'",f"local MODE='{'stop_raw' if fault=='stop_join' else fault}'")
        lua=once(lua,"local FAULT=905","local FAULT=912")
    if fault=="stop_join":
        lua=once(lua,"regs[0x4305]==64 and regs[0x4306]==0 then rawTransfers","regs[0x4305]==160 and regs[0x4306]==1 then rawTransfers")
    (out/"capture.lua").write_text(instrument(lua,mode),encoding="utf-8")
    for pattern in ("commands.txt","wire.txt","busy.txt","client.sfc","map-*.bin","expected-*.bin","colors636-*.bin"):
        for f in src.glob(pattern):
            shutil.copyfile(f,out/f.name)
    if earliest_begin:
        baseline=directory(temp,phase,"978returned","cold")
        events=json.loads((baseline/"events.json").read_bytes())
        commit=max(e["clock"] for e in events if e.get("opcode")=="0xd2" and e.get("input_generation")==912)
        begin,=(e for e in events if e.get("opcode")=="0xe1" and e["generation"]==912 and e["packet_opcode"]==1)
        # Give ARM a prepared BEGIN exactly after the last D2. Keep the whole
        # measured BEGIN transaction and every later E9 eligibility / bank return.
        from math import ceil
        earliest=ceil(commit+begin["clock"]-begin["start"])
        log=out/"commands.txt"
        lines=log.read_text().splitlines()
        i,=(i for i in range(3,len(lines),5) if lines[i][:2]=="01" and bytes.fromhex(lines[i])[8:10]==(912).to_bytes(2,"little"))
        assert lines[i-1]=="PUSH" and earliest<int(lines[i-2])
        lines[i-2]=str(earliest)
        log.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")
    if fault=="bad_seal":
        log=out/"commands.txt"
        lines=log.read_text().splitlines()
        target=[i for i in range(3,len(lines),5) if lines[i][:2]=="03" and bytes.fromhex(lines[i])[8:10]==(912).to_bytes(2,"little")]
        i,=target
        packet=bytearray.fromhex(lines[i])
        packet[8]^=1
        lines[i]=packet.hex()
        log.write_text("\n".join(lines)+"\n",encoding="ascii",newline="\n")
    with (out/"mesen.log").open("wb") as log:
        subprocess.run([temp/"nes-bonus698-mesen/Mesen.exe","--testRunner",out/"capture.lua",
                        out/"client.sfc","--timeout=180","--doNotSaveSettings","--enableStdout",
                        "--snes.disableFrameSkipping=true","--debug.scriptWindow.allowIoOsAccess=true",
                        "--debug.scriptWindow.scriptTimeout=90"],stdout=log,stderr=subprocess.STDOUT,
                       env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                       creationflags=subprocess.CREATE_NO_WINDOW,timeout=200,check=True)
    result=json.loads((out/"result.json").read_bytes())
    assert result["passed"] and result["commits"]==(7 if fault else 8)
    if fault:
        assert result["last_status"]=={"bad_seal":224,"stop_raw":228,"stop_join":228}[fault]
        assert sha(out/"retained.rgb")==sha(src/"frame-911.rgb")
    for g in range(905,905+result["commits"]):
        assert sha(out/f"frame-{g}.rgb")==sha(src/f"frame-{g}.rgb")
    if fault!="bad_seal":
        assert (out/"descriptors.txt").stat().st_size


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp",type=Path)
    parser.add_argument("phase",type=int,choices=(1,2))
    parser.add_argument("mode",choices=("control","priority","rawfirst","join","fresh","freshjoin","guardjoin"))
    parser.add_argument("--fault",choices=("stop_raw","stop_join","bad_seal"))
    parser.add_argument("--earliest-begin",action="store_true")
    parser.add_argument("--recorded",action="store_true")
    a=parser.parse_args()
    if a.recorded:
        from check_nes_output970 import packet_path,replay
        assert not (a.earliest_begin or a.fault)
        t=a.temp.resolve()
        src=directory(t,a.phase,"978returned","cold")
        cmds,_=packet_path(src,912,expected_shape=(21,8))
        replay(t,src,t/f"nes-dma1000-{a.mode}-p{a.phase}-recorded","fixed",cmds,912,
               observe=lambda lua: instrument(lua,a.mode))
    else:
        run(a.temp.resolve(),a.phase,a.mode,a.fault,a.earliest_begin)
