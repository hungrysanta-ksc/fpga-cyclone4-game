"""Measure the end of the packet queue, actual PPU writes, and native render-off intervals."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess

from check_nes_demos968 import GAMES
from check_nes_output970 import packet_path, replay
from nes_display1010 import ROOT, once
from read_nes_frame900 import BLANK, PERIOD


def run_client(temp, out, phase):
    trace = temp / f"nes-tile821-obj-jointmirror-p{phase}-978returned-cold-pair"
    packets = [bytes.fromhex(json.loads(row)[2]) for row in (trace/"packets.jsonl").read_text().splitlines()]
    target = [p for p in packets if int.from_bytes(p[8:10], "little") == 912]
    commands, _ = packet_path(trace, 912, expected_shape=(len(target), sum(p[0] == 7 for p in target)))

    def observe(script):
        anchor = 'if dmaRemaining==1 then sample516("ppu_last") end'
        return once(script, anchor, '''
   if regs[0x4304]==0x7f then
    if dmaRemaining==dmaLength then sample516("first1011",a) end
    if dmaRemaining==1 then sample516("last1011",a) end
   end
   ''' + anchor)

    replay(temp, trace, out, "fixed", commands, 912, observe=observe)
    return client_boundaries(out, phase)


def client_boundaries(out, phase):
    package = json.loads((ROOT/"analysis/trial1010-package.json").read_bytes())
    assert hashlib.sha256((out/"client.sfc").read_bytes()).hexdigest() == package["client"]
    base = json.loads((ROOT/"analysis/demo-loss1009-results.json").read_bytes())["replay978"][str(phase)]
    result = {}
    with (out/"window.csv").open() as f:
        rows = list(csv.DictReader(f))
    for gen, expected in base.items():
        frame = [r for r in rows if r["g"] == gen]
        seal, = [r for r in frame if r["event"] == "load" and r["op"] == "3"]
        retire, = [r for r in frame if r["event"] == "ack" and int(r["index"]) == int(seal["index"])-1]
        first = next(r for r in frame if r["event"] == "first1011" and int(r["clock"]) >= int(seal["clock"]))
        last = next(r for r in reversed(frame) if r["event"] == "last1011")
        show, = [r for r in frame if r["event"] == "reveal"]
        ack, = [r for r in frame if r["event"] == "ack" and r["op"] == "3"]
        clocks = [int(r["clock"]) for r in (retire, seal, first, last, show, ack)]
        assert clocks == sorted(clocks)
        assert all(225 <= int(r["line"]) <= 261 for r in (first, last, show))
        assert [clocks[i] for i in (1, 3, 4, 5)] == [expected[k] for k in ("SEAL_header", "last_dma", "show", "final_ACK")]
        result[gen] = dict(retired_op=int(retire["op"]), retired_section=int(retire["section"]),
                           retire_seal_first_last_show_ack=clocks, first_port=int(first["value"]),
                           last_port=int(last["value"]), first_last_show_frame=[int(r["frame"]) for r in (first,last,show)])
    return result


NATIVE = """
local out=assert(io.open(@PATH@,'w'))
local pad={a=false,b=false,start=false,select=false,up=false,down=false,left=false,right=false}
local mask,enabled,frame=0,false,0
emu.addMemoryCallback(function(a,v)
 if a%8==1 then mask=v; if (mask&24)~=0 then enabled=true end end
end,emu.callbackType.write,0x2000,0x3fff,emu.cpuType.nes,emu.memType.nesMemory)
emu.addEventCallback(function()
 frame=frame+1
 emu.setInput(pad,0);emu.setInput(pad,1)
 if not enabled then
  local screen=emu.getScreenBuffer()
  assert(#screen==256*240)
  local flat=true
  for i=2,#screen do if screen[i]~=screen[1] then flat=false;break end end
  out:write(frame,' ',flat and 1 or 0,'\\n')
 end
 enabled=(mask&24)~=0
 if frame==3720 then out:write('END ',frame,'\\n');out:close();emu.stop(0) end
end,emu.eventType.endFrame)
"""


def run_native(temp, rom, out):
    digest = hashlib.sha256(rom.read_bytes()).hexdigest()
    assert digest == GAMES["Adventure Island IV"]
    out.mkdir(parents=True)
    log = out/"frames.txt"
    script = out/"native.lua"
    script.write_text(NATIVE.replace("@PATH@", json.dumps(log.as_posix(), ensure_ascii=False)), encoding="utf8")
    mesen = temp/"nes-bonus698-mesen/Mesen.exe"
    with (out/"mesen.log").open("wb") as f:
        subprocess.run([mesen, "--testRunner", script, rom, "--timeout=150", "--doNotSaveSettings",
                        "--enableStdout", "--preferences.overrideSaveDataFolder=true", f"--preferences.saveDataFolder={out}",
                        "--debug.scriptWindow.allowIoOsAccess=true"], cwd=out, stdout=f, stderr=subprocess.STDOUT,
                       timeout=165, check=True, creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ, DOTNET_ROOT="C:/works/dotnet", DOTNET_ROOT_X64="C:/works/dotnet"))
    rows = log.read_text().splitlines()
    assert rows.pop() == "END 3720"
    intervals = []
    for row in rows:
        frame, flat = map(int, row.split())
        if intervals and frame == intervals[-1][1]+1:
            intervals[-1][1] = frame
            intervals[-1][2] += flat
        else:
            intervals.append([frame, frame, flat])
    assert any(a <= 1550 <= b for a,b,_ in intervals), "known opening transition was not detected"
    return dict(rom_sha256=digest, mesen_sha256=hashlib.sha256(mesen.read_bytes()).hexdigest(),
                frames=3720, render_off_first_last_uniform_count=intervals)


def physical():
    hw = json.loads((ROOT/"analysis/display1010-hardware.json").read_bytes())
    tick = hw["fpga_tick_ms"]
    result = []
    for trial, run in enumerate(hw["runs"], 1):
        for key in ("1411", "1443", "1453", "1511"):
            if key not in run["targets"]:
                continue
            row = run["targets"][key]
            distance = row["seal_to_show_ms"]
            # Publication can be anywhere in blank. Allow a full tick for timestamp subtraction.
            result.append(dict(trial=trial, reference=int(key), generation=row["generation"],
                tile_to_seal_ms=row["tile_to_seal_ms"], seal_to_show_ms=distance,
                seal_to_publication_blank_start_min_ms=max(0, distance-tick-BLANK),
                prev_blank_closed_before_seal_min_ms=max(0, PERIOD-BLANK-distance-tick),
                prev_blank_remaining_at_seal_max_ms=max(0, distance+tick-(PERIOD-BLANK)),
                tile_lead_before_prev_blank_start_min_ms=max(0, row["last_tile_to_show_ms"]-tick-PERIOD-BLANK)))
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("temp", type=Path)
    p.add_argument("out", type=Path)
    p.add_argument("rom", type=Path)
    p.add_argument("report", type=Path)
    args = p.parse_args()
    out = args.out.resolve()
    result = dict(native=run_native(args.temp, args.rom.resolve(), out/"native"), physical=physical(),
                  phases={phase:run_client(args.temp, out/f"phase{phase}", phase) for phase in (1,2)})
    args.report.write_text(json.dumps(result, indent=2)+"\n", encoding="utf8")
