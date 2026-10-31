# SPDX-License-Identifier: MIT
"""Replay the saved MMC509 calendar commands and observe the unchanged 65816."""
import argparse
import csv
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def replace_once(source, old, new):
    if source.count(old) != 1:
        raise ValueError(f"Unexpected Lua instrumentation anchor: {old}")
    return source.replace(old, new)


def observe(source, fixture, out, labels, body):
    # Keep the original ARM targets and compare each reconstructed reply to its archived bytes.
    source = replace_once(source, f'local ROOT="{fixture.as_posix()}"',
                          f'local ROOT="{out.as_posix()}"\nlocal ORIGINAL="{fixture.as_posix()}"')
    begin = source.index("local function nextCommand()")
    end = source.index("\nnextCommand()\n", begin)
    source = source[:begin] + """local stream=assert(io.open(ROOT..'/rpc.txt','r'))
local expectedReply
local differences=assert(io.open(ROOT..'/sync-differences.csv','w'))
differences:write('sequence,target,original,replay\\n')
local function nextCommand()
 sequence=sequence+1;target=tonumber(assert(stream:read('*l')))
 operation=assert(stream:read('*l'));args={stream:read('*l'),stream:read('*l')}
 expectedReply=unhex(assert(stream:read('*l')))
end""" + source[end:]
    source = replace_once(source, "local f=assert(io.open(ROOT..'/reply.tmp','w'))", """local parts={}
  local f={write=function(_,s)table.insert(parts,s)end,close=function()end}""")
    source = replace_once(source, "assert(os.rename(ROOT..'/reply.tmp',ROOT..'/reply-'..sequence..'.txt'))", """local actual=table.concat(parts)
  if actual~=expectedReply then
   local saved,tail=expectedReply:match('^(%d+)\\n(.*)$')
   local current,tail2=actual:match('^(%d+)\\n(.*)$')
   -- Permit only the two pinned, status-only replies known to predate their
   -- target. All retired identities and events must agree, and replay is causal.
   local allowed=operation=='SYNC' and (sequence==4463 or sequence==7572)
   if not (allowed and tonumber(saved)<target and tonumber(current)>=target and tail==tail2 and tail:match("^%d+%s+%x+%s*$")) then
    local f=assert(io.open(ROOT..'/mismatch.txt','w'));f:write(sequence,'\\n',expectedReply,actual);f:close()
    finished=true;emu.stop(1);return
   end
   differences:write(string.format('%d,%d,%d,%d\\n',sequence,target,saved,current))
  end
  if finished then
   local count=assert(io.open(ROOT..'/replies.txt','w'));count:write(sequence);count:close()
   differences:close()
  end""")
    source = replace_once(source, "local function loaded()", """local log511=assert(io.open(ROOT..'/trace.csv','w'))
log511:write('generation,index,op,section,event,clock,scanline,value\\n')
local function record(name,value)
 if packet then
  local state=emu.getState()
  log511:write(string.format('%d,%d,%d,%d,%s,%d,%d,%d\\n',pw(8),index,pb(0),pb(1),name,state.masterClock,state['ppu.scanline'],value or 0))
 end
end
local function loaded()""")
    source = replace_once(source, "packet=requests[index];reads=0;",
                          "packet=requests[index];record('load');reads=0;")
    source = replace_once(source, "lastStatus=ack[1]", "lastStatus=ack[1];record('ack',lastStatus)")
    source = replace_once(source, "local function write(a,v)", "local remaining511=0\nlocal function write(a,v)")
    source = replace_once(source, "  if visible then", """  if remaining511>0 then
   remaining511=remaining511-1
   if remaining511==0 then record('ppu_last') end
  end
  if visible then""")
    source = replace_once(source, ";dmaRemaining=dmaLength", """;dmaRemaining=dmaLength
  if packet then assert(remaining511==0);remaining511=dmaLength;record('dma_start',dmaLength) end""")
    base = 0x7e2000
    # Each selected call uses an intra-bank JSR. Log its return at the caller,
    # including the RTS, so wait intervals can be separated from register setup.
    hooks = []
    for name in ("compact489", "validate181", "coverage212", "wait169"):
        target = labels[name]
        opcode = bytes([0x20]) + (target & 0xffff).to_bytes(2, "little")
        sites = [i for i in range(len(body)) if body.startswith(opcode, i)]
        if not sites:
            raise ValueError(f"Missing JSR for {name}")
        hooks.append((target, name))
        hooks.extend((base + i + 3, name + "_return") for i in sites)
    hooks.extend((labels[name], name) for name in ("seal", "upload165_entry", "final212"))
    lines = [f"emu.addMemoryCallback(function()record('{name}')end,emu.callbackType.exec,{pc})"
             for pc, name in hooks]
    source = replace_once(source, "local sequence=0;", "\n".join(lines) + "\nlocal sequence=0;")
    return replace_once(source, "f:close();emu.stop(0)", "f:close();log511:close();emu.stop(0)")


def replay(fixture, client, mesen, out):
    selected = json.loads((ROOT / "analysis/service509-verification.json").read_text())
    assert sha(fixture / "joint.json") == selected["boot_trace_sensitivity_vs506"]["candidate_SHA256"]
    joint = json.loads((fixture / "joint.json").read_text())
    assert joint["passed"] and joint["client_SHA256"] == sha(client / "sink165.sfc") == sha(fixture / "client.sfc")
    body = (client / "body.bin").read_bytes()
    assert body in (fixture / "client.sfc").read_bytes()
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(fixture / "client.sfc", out / "client.sfc")
    for expected in fixture.glob("expected-*.bin"):
        shutil.copyfile(expected, out / expected.name)
    commands = len(list(fixture.glob("command-*.txt")))
    archive = json.loads((ROOT.parent / "probes/nes-service509/archive01/inventory.json").read_text())
    with (out / "rpc.txt").open("w", encoding="ascii", newline="\n") as stream:
        for i in range(1, commands + 1):
            command, reply = (fixture / f"{kind}-{i}.txt" for kind in ("command", "reply"))
            for path in (command, reply):
                assert sha(path) == archive["calendar02/" + path.name]["SHA256"]
            lines = command.read_text().splitlines()
            assert 2 <= len(lines) <= 4
            stream.writelines(s + "\n" for s in lines + [""] * (4 - len(lines)))
            stream.write(reply.read_text().encode("ascii").hex() + "\n")
    lua = observe((fixture / "capture.lua").read_text(encoding="utf8"), fixture, out,
                  json.loads((client / "labels.json").read_text()), body)
    (out / "capture.lua").write_text(lua, encoding="utf8")
    env = dict(os.environ, DOTNET_ROOT="C:/works/dotnet", DOTNET_ROOT_X64="C:/works/dotnet")
    with (out / "mesen.log").open("wb") as log:
        subprocess.run([str(mesen), "--testRunner", str(out / "capture.lua"), str(out / "client.sfc"),
                        "--timeout=720", "--doNotSaveSettings", "--enableStdout",
                        "--snes.disableFrameSkipping=true", "--debug.scriptWindow.allowIoOsAccess=true",
                        "--debug.scriptWindow.scriptTimeout=90"], cwd=out, env=env, stdout=log,
                       stderr=subprocess.STDOUT, timeout=735, creationflags=subprocess.CREATE_NO_WINDOW, check=True)
    assert json.loads((out / "result.json").read_text()) == json.loads((fixture / "result.json").read_text())
    assert int((out / "replies.txt").read_text()) == commands
    with (out / "sync-differences.csv").open() as log:
        differences = list(csv.DictReader(log))
    assert [int(row["sequence"]) for row in differences] == [4463, 7572]
    for frame in joint["frames"]:
        name = f"frame-{frame['generation']}.rgb"
        assert sha(out / name) == sha(fixture / name), name
    print(f"PASS: {commands} replies checked (2 timing corrections), {len(joint['frames'])} identical screens and ACK clocks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("fixture", "client", "mesen", "out"):
        parser.add_argument("--" + name, required=True, type=Path)
    args = parser.parse_args()
    replay(*(p.resolve() for p in (args.fixture, args.client, args.mesen, args.out)))
