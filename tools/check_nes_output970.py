"""Measure 907 packet service and replay earlier, wire-limited arrivals on the released 65816."""
import argparse
import json
import math
import os
import re
import shutil
import subprocess
from pathlib import Path

from check_nes_blank959 import directory, read, rows, sha
from nes_raw506 import once


def packet_path(trace, target=907):
    packets = [json.loads(line) for line in (trace / "packets.jsonl").read_text().splitlines()]
    events = [e for e in read(trace / "events.json") if e.get("opcode") == "0xe1"]
    tiles = [json.loads(line) for line in (trace / "producer.jsonl").read_text().splitlines()]
    accepted = [r for r in rows(trace / "window.csv") if r["event"] == "load"]
    retired = [r for r in rows(trace / "window.csv") if r["event"] == "ack"]
    commands, ledger = [], []
    for record, event, load, ack in zip(packets, events, accepted, retired, strict=True):
        _, arrival, wire, bulk = record
        head = bytes.fromhex(wire)
        g = int.from_bytes(head[8:10], "little")
        assert g == event["generation"] == int(load["g"]) == int(ack["g"])
        assert head[0] == event["packet_opcode"] == int(load["op"]) == int(ack["op"])
        assert load["index"] == ack["index"] and abs(arrival - event["clock"]) < 1
        if g > target:
            break
        source = 0
        if g == target:
            if head[0] == 7:
                token = int.from_bytes(head[16:20], "little")
                tile, = (t for t in tiles if t["generation"] == g and t["token"] == token)
                assert tile["kind"] == head[1] and tile["bytes"] == len(bytes.fromhex(bulk))
                source = math.ceil(tile["observed"])
            ledger.append(dict(index=int(load["index"]), op=head[0], section=head[1],
                               issue=round(event["start"]), arrive=arrival, load=int(load["clock"]),
                               ack=int(ack["clock"]), tile_observed=source))
        commands.append((g, head[0], arrival, wire, bulk, source, math.ceil(event["clock"] - event["start"])))
    assert (len(ledger), [r["op"] for r in ledger].count(7)) == {907: (23, 2), 911: (16, 3)}[target]
    return commands, ledger


def counters(folder, target=907):
    window = [r for r in rows(folder / "window.csv") if r["g"] == str(target) and r["op"] == "3"]
    def event(name):
        row, = (r for r in window if r["event"] == name)
        return [int(row[k]) for k in ("clock", "frame", "line")]
    return {name: event(name) for name in ("load", "seal", "upload165_entry", "reveal", "ack")}


def ordinary_first(commands, target, before_all_tiles):
    earlier = [p for p in commands if p[0] < target]
    frame = [p for p in commands if p[0] == target]
    obj = next(p for p in reversed(frame) if bytes.fromhex(p[3])[:2] == bytes((7, 1)))
    assert frame[-1][1] == 3
    deferred = [p for p in frame if p[1] == 7] if before_all_tiles else [obj]
    order = [p for p in frame[:-1] if p not in deferred] + deferred + [frame[-1]]
    for index, (g, op, arrival, wire, bulk, observed, duration) in enumerate(order):
        packet = bytearray.fromhex(wire)
        packet[2:4] = index.to_bytes(2, "little")
        earlier.append((g, op, arrival, packet.hex(), bulk, observed, duration))
    return earlier


def replay(temp, trace, out, mode, commands, target=907, fault=None):
    out = out.resolve()
    out.mkdir(parents=True)
    lua = (trace / "capture.lua").read_text()
    lua = once(lua, json.dumps(trace.resolve().as_posix()), json.dumps(out.as_posix(), ensure_ascii=False))
    lua = re.sub(r"^local cmds=.*$", "local cmds=assert(io.open(ROOT..'/commands.txt','rb'))", lua, count=1, flags=re.M)
    lua = re.sub(r"^local replies=.*$", "local replies={write=function()end,flush=function()end}", lua, count=1, flags=re.M)
    lua = once(lua, "MODE=='normal'and 8", f"MODE=='normal'and {target-904}")
    lua = once(lua, 'step920("consume920");consumed[', '''step920("consume920")
  local ret=assert(io.open(ROOT..'/returns970.txt','a'))
  ret:write(pw(16)+65536*pw(18),' ',emu.getState().masterClock,'\\n');ret:close()
  consumed[''')
    if fault:
        lua = once(lua, "local MODE='normal'", f"local MODE='{fault}'")
        lua = once(lua, "local FAULT=905", f"local FAULT={target}")
    lua = once(lua, "local lastPush527=0", """local lastPush527=0
local inflight=false
local duration
local busy={}
for line in io.lines(ROOT..'/busy.txt') do
 local a,b=line:match('(%d+) (%d+)');busy[#busy+1]={tonumber(a),tonumber(b)}
end
local block=1
local wires=assert(io.open(ROOT..'/wire.txt','r'))
local starts=assert(io.open(ROOT..'/starts.txt','w'))""")
    lua = once(lua, "  if operation=='PUSH'then", """  if operation=='EARLY' then
   if not inflight then
    if sent-retired>=4 then break end
    if not duration then duration=assert(tonumber(wires:read('*l'))) end
    while busy[block] and now>=busy[block][2] do block=block+1 end
    if busy[block] and now+duration>busy[block][1] then target=busy[block][2];break end
    starts:write(sequence,' ',now,' ',now+duration,' ',sent-retired,'\\n');starts:flush()
    target=now+duration;inflight=true;break
   end
   inflight=false;duration=nil;operation='PUSH'
  end
  if operation=='PUSH'then""")
    stream, durations = [], []
    last_tile = max(p[2] for p in commands if p[0] == target and p[1] == 7)
    if mode in ("ordinary", "prelude", "reserved"):
        commands = ordinary_first(commands, target, mode != "ordinary")
    busy = []
    if mode == "reserved":
        first = next(p[2] for p in commands if p[0] == target)
        busy = [(math.floor(e["start"]), math.ceil(e["clock"])) for e in read(trace / "events.json")
                if "start" in e and e.get("opcode") != "0xe1" and e["clock"] > first]
        assert busy == sorted(busy) and busy
    (out / "busy.txt").write_text("".join(f"{a} {b}\n" for a,b in busy))
    for g, op, arrival, wire, bulk, observed, duration in commands:
        # Preserve BEGIN and the entire boot. In the tail variant also preserve
        # both tile handoffs. Model a dedicated E1 bus only for the selected tail.
        early = g == target and op != 1 and (mode in ("frame", "ordinary", "prelude", "reserved") or (mode == "tail" and arrival > last_tile))
        if fault == "bad_seal" and g == target and op == 3:
            damaged = bytearray.fromhex(wire)
            damaged[8] ^= 1
            wire = damaged.hex()
        stream.append((observed if early else arrival, "EARLY" if early else "PUSH", wire, bulk))
        if early:
            durations.append(duration)
    stream.append((0, "FINISH", "", ""))
    (out / "commands.txt").write_text("".join(f"{i}\n{at}\n{op}\n{wire}\n{bulk}\n"
                                             for i, (at, op, wire, bulk) in enumerate(stream, 1)), encoding="ascii", newline="\n")
    (out / "wire.txt").write_text("".join(f"{n}\n" for n in durations))
    (out / "capture.lua").write_text(lua, encoding="utf8")
    for glob in ("client.sfc", "expected-*.bin", "map-*.bin", "colors636-*.bin"):
        for f in trace.glob(glob):
            shutil.copyfile(f, out / f.name)
    with (out / "mesen.log").open("wb") as log:
        subprocess.run([temp / "nes-bonus698-mesen/Mesen.exe", "--testRunner", out / "capture.lua", out / "client.sfc",
                        "--timeout=180", "--doNotSaveSettings", "--enableStdout", "--snes.disableFrameSkipping=true",
                        "--debug.scriptWindow.allowIoOsAccess=true", "--debug.scriptWindow.scriptTimeout=90"],
                       stdout=log, stderr=subprocess.STDOUT, timeout=200, check=True,
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ, DOTNET_ROOT="C:/works/dotnet", DOTNET_ROOT_X64="C:/works/dotnet"))
    result = read(out / "result.json")
    committed = target - int(fault is not None)
    assert result["passed"] and result["commits"] == committed - 904
    for g in range(905, committed+1):
        assert sha(out / f"frame-{g}.rgb") == sha(trace / f"frame-{g}.rgb")
    if fault:
        assert result["last_status"] == (228 if fault == "stop_decode" else 224)
        assert sha(out / "retained.rgb") == sha(trace / f"frame-{committed}.rgb")
        return dict(commits=result["commits"], status=result["last_status"], previous_screen_retained=True)
    clocks = counters(out, target)
    if mode == "control":
        assert clocks == counters(trace, target)
    return clocks


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("temp", type=Path)
    parser.add_argument("out", type=Path)
    parser.add_argument("phase", type=int, choices=(1, 2))
    parser.add_argument("mode", choices=("control", "tail", "frame", "ordinary", "prelude", "reserved"))
    parser.add_argument("--generation", type=int, choices=(907, 911), default=907)
    parser.add_argument("--fault", choices=("bad_seal", "stop_decode"))
    args = parser.parse_args()
    trace = directory(args.temp, args.phase, "966release", "cold")
    commands, ledger = packet_path(trace, args.generation)
    values = replay(args.temp, trace, args.out, args.mode, commands, args.generation, args.fault)
    print(json.dumps(values))
