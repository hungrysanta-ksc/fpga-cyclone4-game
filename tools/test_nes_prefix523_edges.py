# SPDX-License-Identifier: MIT
"""Exercise the prefix's maximum transfer on the real 65816 and PPU beam."""
import argparse
import csv
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess

from nes_prefix523 import build, emit, packet, upload
from nes_raw506 import once
from test_nes_output489_snes import LUA


def pace_beam(c):
    c.absolute(0xad,0x1226);c.emit(0xc9);c.word(906);c.branch(0xd0,'unpaced523')
    c.emit(0xe2,0x20);c.label('pace523');c.absolute(0xad,0x605f);c.branch(0xf0,'pace523')
    c.emit(0xc2,0x20);c.label('unpaced523')


def run(a):
    a.out.mkdir(parents=True, exist_ok=False)
    client = a.out / "paced"
    build(client, emitter=lambda c: emit(c, pace_beam), fill=True, packet_edit=packet, upload_edit=upload)
    labels = json.loads((client / "labels.json").read_text())
    packets = []
    bulk = 0
    pattern = bytes(range(256)) * 8
    for line in (a.trace / "packets.jsonl").read_text().splitlines():
        _, _, body, tile = json.loads(line)
        body, tile = bytearray.fromhex(body), bytes.fromhex(tile)
        if body[0] == 7 and int.from_bytes(body[8:10], "little") == 906:
            assert body[1] == 0
            bulk += 1
            # The second disjoint range closes the first 2 KiB BG command.
            offset, tile = (0, pattern) if bulk == 1 else (2080, pattern[:16])
            struct.pack_into("<H", body, 10, offset)
            struct.pack_into("<H", body, 14, len(tile))
        packets.append((body, tile))
        if bulk == 2:
            break
    assert bulk == 2
    wait_probe = """
local entered,lastLine,firstClock=false,-1,0
local beamFile=assert(io.open(ROOT..'/beam.csv','w'))
beamFile:write('event,clock,line,frame\\n')
local function beam(name)
 local state=emu.getState()
 beamFile:write(string.format('%s,%d,%d,%d\\n',name,state.masterClock,state['ppu.scanline'],state.frameCount))
 beamFile:flush()
end
emu.addMemoryCallback(function()
 local state=emu.getState();local line=state['ppu.scanline']
 if line~=lastLine then lastLine=line;firstClock=state.masterClock end
 if line==@LINE@ and state.masterClock-firstClock>=900 then
  entered=true;beam('released');return 1
 end
 return 0
end,emu.callbackType.read,0x605f)
if @STALE@ then
 emu.addMemoryCallback(function() if entered then return 0 end end,emu.callbackType.read,0x213f)
end
emu.addMemoryCallback(function() if entered then beam('issue') end end,emu.callbackType.exec,@ISSUE@)
"""
    results = {}
    for case, target in dict(active=224, early=225, last=232, late=233, high=256, stale=230).items():
        folder = a.out / case
        folder.mkdir()
        (folder / "requests.bin").write_bytes(b"".join(struct.pack("<H",len(body))+body for body,_ in packets))
        for i, (_, data) in enumerate(packets, 1):
            if data:
                (folder / f"tile-{i:04d}.bin").write_bytes(data)
        shutil.copyfile(a.trace / "expected-905.bin", folder / "expected-905.bin")
        shutil.copyfile(client / "sink165.sfc", folder / "client.sfc")
        s = once(LUA, "local function loaded()", wait_probe + "\nlocal function loaded()")
        s = once(s,"   dmaRemaining=dmaRemaining-1", """   if entered and dmaRemaining==1 then beam('last_write') end
   dmaRemaining=dmaRemaining-1""")
        s = once(s,"  assert(captured==commits)", """  assert(captured==commits and entered and not rejected)
  assert(word(0x1032)==0 and word(0x1034)==1 and word(0x1250)==16)
  assert(word(0x1252)==(@ISSUED@ and 8 or 0),'wrong retire cursor')
  if @ISSUED@ then for i=0,2047 do assert(emu.read(0xc000+i,emu.memType.snesVideoRam)==i%256,'wrong DMA data') end end""")
        fields = dict(ROOT=json.dumps(folder.as_posix()),MODE='"normal"',TOTAL=len(packets),FRAMES=1,
                      SCHEDULE='"continuous"',START=3000000,FAULT=906,COMPACT='true',POISON='false',
                      ISSUE=labels["issue523"],LINE=target,STALE=str(case=="stale").lower(),
                      ISSUED=str(case in ("early","last")).lower())
        for key, value in fields.items():
            s = s.replace("@"+key+"@",str(value))
        (folder / "capture.lua").write_text(s,encoding="utf8")
        with (folder / "mesen.log").open("wb") as log:
            subprocess.run([str(a.mesen),"--testRunner",str(folder/"capture.lua"),str(folder/"client.sfc"),
                            "--timeout=120","--doNotSaveSettings","--enableStdout","--snes.disableFrameSkipping=true",
                            "--debug.scriptWindow.allowIoOsAccess=true","--debug.scriptWindow.scriptTimeout=90"],
                           env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                           cwd=folder,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=135,
                           creationflags=subprocess.CREATE_NO_WINDOW)
        with (folder/"beam.csv").open() as f:
            events=list(csv.DictReader(f))
        issued = case in ("early","last")
        assert [e["event"] for e in events] == (["released","issue","last_write"] if issued else ["released"])
        if issued:
            assert events[1]["frame"]==events[2]["frame"] and int(events[2]["line"])>=225
        results[case]=events
        print(case,events,flush=True)
    (a.out/"edges.json").write_text(json.dumps(results,indent=2)+"\n")


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("mesen","trace","out"):
        p.add_argument("--"+name,type=Path,required=True)
    a=p.parse_args()
    a.out=a.out.resolve()
    run(a)
