"""Run four fixed local cartridges without input; publish measurements, never ROM data."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile

from check_nes_opening818 import admission


GAMES = {
    "Adventure Island IV": "9d7402da135fd1290346ccc9332836daee3a9a3cda3789999c3f86efdb5b19c2",
    "Kirby": "56901e11f6fe812e0a049c747fa0b0d6fc42a336c502ca94fb5282229853347d",
    "Ikari III": "be21ed877a49659b97bd460f218a1227825132f43c3d5f907fd904ca411680fc",
    "Youkai Douchuuki": "9761843ac9ce003564eac0d935cde5d0e04e999c4397a9415e7fec3dde2cf421",
}
LUA = """
local f=assert(io.open(@OUT@,'w'))
local frame,previous,total,changes,intervals=0,nil,0,0,0
local high_prg,high_chr=0,0
local released={a=false,b=false,start=false,select=false,up=false,down=false,left=false,right=false}
emu.addEventCallback(function()
  emu.setInput(released,0);emu.setInput(released,1)
  frame=frame+1
  if frame%6~=0 then return end
  local screen=emu.getScreenBuffer()
  local hash=0
  for i=1,#screen,113 do hash=(hash*31+screen[i]) & 0x7fffffff end
  if frame>60 then
    intervals=intervals+1
    if hash~=previous then changes=changes+1 end
    local upper=false
    for a=0x8000,0xe000,0x2000 do
      local p=emu.convertAddress(a,emu.memType.nesMemory,emu.cpuType.nes)
      if p and p.memType==emu.memType.nesPrgRom and p.address>=0x40000 then upper=true end
    end
    if upper then high_prg=high_prg+1 end
    upper=false
    for a=0,0x1c00,0x400 do
      local p=emu.convertAddress(a,emu.memType.nesPpuMemory,emu.cpuType.nes)
      if p and p.memType==emu.memType.nesChrRom and p.address>=0x20000 then upper=true end
    end
    if upper then high_chr=high_chr+1 end
    for i=0,63 do
      if emu.read(i*4,emu.memType.nesSpriteRam)<239 then total=total+1 end
    end
  end
  previous=hash
  if frame==1800 or frame==3600 then
    f:write(string.format('%d %d %d %d %d %d\\n',frame,changes,intervals,total,high_prg,high_chr))
    total,changes,intervals=0,0,0
    high_prg,high_chr=0,0
  end
  if frame==3600 then f:close();emu.stop(0) end
end,emu.eventType.endFrame)
"""


def observe(rom, mesen, folder):
    folder.mkdir()
    samples = folder / "samples.txt"
    script = folder / "sample.lua"
    script.write_text(LUA.replace("@OUT@", json.dumps(samples.as_posix(), ensure_ascii=False)), encoding="utf8")
    subprocess.run([mesen, "--testRunner", script, rom, "--timeout=150", "--doNotSaveSettings",
                    "--preferences.overrideSaveDataFolder=true", f"--preferences.saveDataFolder={folder}",
                    "--debug.scriptWindow.allowIoOsAccess=true"], cwd=folder,
                   creationflags=subprocess.CREATE_NO_WINDOW, timeout=165, check=True,
                   env=dict(os.environ, DOTNET_ROOT="C:/works/dotnet", DOTNET_ROOT_X64="C:/works/dotnet"))
    lines = [list(map(int, line.split())) for line in samples.read_text().splitlines()]
    if [(line[0], line[2]) for line in lines] != [(1800, 290), (3600, 300)]:
        raise ValueError("incomplete 3600-frame demo")
    return {window: dict(changed_samples=changed, intervals=count, mean_oam_y_below_239=round(total / count, 2),
                         upper_PRG_mapped=high_prg, upper_CHR_mapped=high_chr)
            for window, (_, changed, count, total, high_prg, high_chr) in zip(("1-30", "30-60"), lines, strict=True)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("roms", "mesen", "arm_src", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[1]
    firmware = args.arm_src / "obj-nes-100" / "firmware.stm"
    firmware_hash = hashlib.sha256(firmware.read_bytes()).hexdigest()
    if firmware_hash != json.loads((repo/"analysis/trial966-package.json").read_bytes())["firmware"]:
        raise ValueError("MMC966 final link required")
    matches = {}
    for path in args.roms.glob("*.nes"):
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest in GAMES.values():
            matches[digest] = path.resolve()
    results = {}
    with tempfile.TemporaryDirectory(prefix="nes-demo968-") as temp:
        for game, digest in GAMES.items():
            rom = matches[digest]
            raw = rom.read_bytes()
            h = raw[:16]
            if h[:4] != b"NES\x1a" or len(raw) != 16 + h[4]*16384 + h[5]*8192 or h[6]&4:
                raise ValueError(f"{game}: unexpected layout")
            loader = admission(args.arm_src, raw, 966)
            if (loader["error"], loader["program"], loader["read_B"]) != (
                    (0, True, len(raw)) if game == "Adventure Island IV" else (2, False, 16)):
                raise ValueError(f"{game}: MMC966 loader result changed: {loader}")
            results[game] = dict(sha256=digest, header=h.hex(), mapper=(h[7]&240)|(h[6]>>4),
                                 PRG_KiB=h[4]*16, CHR_KiB=h[5]*8, battery=bool(h[6]&2),
                                 mmc966_loader=loader, reference_windows=observe(rom, args.mesen, Path(temp)/digest[:8]))
    report = dict(firmware_sha256=firmware_hash, mesen_sha256=hashlib.sha256(args.mesen.read_bytes()).hexdigest(),
                  games=results)
    args.output.write_bytes((json.dumps(report, indent=2)+"\n").encode())


if __name__ == "__main__":
    main()
