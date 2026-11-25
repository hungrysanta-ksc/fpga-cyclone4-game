"""Trace selected demo pictures at their actual no-input times, including the final one."""
import argparse
import json
import os
import subprocess
from pathlib import Path
from run_nes_geometry230 import ROOT, sha
from prepare_nes_opening818 import ADVENTURE_SHA

FRAMES = (1500, 1557, 2100, 3000, 3600)


def capture(rom, mesen, out, frames=FRAMES, *, expected_sha=ADVENTURE_SHA):
    assert sha(rom) == expected_sha
    out.mkdir(parents=True, exist_ok=False)
    text = (ROOT / "tests/nes-functional/capture_geometry230.lua").read_text()
    text = text[:text.index("local function input(f)")] + text[text.index("local function screenshot(f)"):]
    text = text.replace("local p=input(f)", "local p={}")
    text = text.replace("captureFrame>=CAP_FIRST and captureFrame<=CAP_LAST", "wanted[captureFrame]")
    text = text.replace("f>=CAP_FIRST-1 and f<=CAP_LAST", "wanted[f]")
    text = text.replace("f%30==0 or (CAP_FIRST>0 and f>=CAP_FIRST and f<=CAP_LAST)", "wanted[f]")
    # Expensive debugger callbacks are attached only when a sampled frame
    # begins. They return no value and do not change game input or memory.
    a = text.index("emu.addEventCallback(")
    b = text.index("if CAP_FIRST>0 then", a)
    e = text.index("\nend\nlocal function screenshot", b)
    hooks = text[b+len("if CAP_FIRST>0 then"):e].replace("emu.addMemoryCallback(", "track(")
    text = text[:a] + """
local callbacks={}
local function track(fn, ...)
  local args={...}
  local id=emu.addMemoryCallback(fn, table.unpack(args))
  callbacks[#callbacks+1]={id,args}
end
local function attach()
""" + hooks + """
end
emu.addEventCallback(function()
  captureFrame=emu.getState().frameCount
  if wanted[captureFrame] and #callbacks==0 then attach()
  elseif not wanted[captureFrame] then
    for _,entry in ipairs(callbacks) do emu.removeMemoryCallback(entry[1],table.unpack(entry[2])) end
    callbacks={}
  end
end,emu.eventType.startFrame)
""" + text[e+5:]
    config = f"local OUT_DIR={json.dumps(out.as_posix())}\nlocal END_FRAME=3600\nlocal CAP_FIRST=1\n"
    config += "local wanted={" + ",".join(f"[{f}]=true" for f in frames) + "}\n"
    lua = out/"capture.lua"
    lua.write_text(config+text, encoding="utf8")
    with (out/"mesen.log").open("wb") as log:
        subprocess.run([mesen, "--testRunner", lua, rom, "--timeout=480", "--enableStdout",
                        "--doNotSaveSettings", "--debug.scriptWindow.allowIoOsAccess=true"],
                       cwd=out, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=510,
                       creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ, DOTNET_ROOT="C:/works/dotnet", DOTNET_ROOT_X64="C:/works/dotnet"))
    assert (out/f"frame-{max(frames):04d}.rgb").stat().st_size == 256*240*3
    assert len((out/"frames.tsv").read_text().splitlines()) == 3600
    (out/"capture.json").write_text(json.dumps(dict(exit_code=0, capture_first=min(frames),
        capture_last=max(frames), sampled=frames, rom=sha(rom), script=sha(lua), core=sha(mesen.parent/"MesenCore.dll"))))


if __name__ == "__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("rom","mesen","out"):
        p.add_argument(name,type=Path)
    p.add_argument("--frames", type=int, nargs="+", default=FRAMES)
    a=p.parse_args()
    capture(a.rom.resolve(),a.mesen.resolve(),a.out.resolve(),a.frames)
