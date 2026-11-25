"""Fixed source-picture sampling and title-independent OBJ directory experiments."""
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import shutil
import time

ROOT = Path(__file__).resolve().parents[1]
GAMES = {"kirby": "56901e11f6fe812e0a049c747fa0b0d6fc42a336c502ca94fb5282229853347d",
         "adventure": "9d7402da135fd1290346ccc9332836daee3a9a3cda3789999c3f86efdb5b19c2"}
POLICIES = ("low_mirror", "fold_primary", "rotated_mirror")


def rom_path(folder, game):
    return next(p for p in folder.glob("*.nes") if hashlib.sha256(p.read_bytes()).hexdigest() == GAMES[game])


def capture(exe, rom, folder):
    folder.mkdir(parents=True, exist_ok=False)
    # The native Lua file API on Windows expects an ASCII path.
    with tempfile.TemporaryDirectory(prefix="nes-cross1022-") as name:
        native = Path(name)
        script = native / "capture.lua"
        script.write_text("OUT="+json.dumps(native.as_posix())+"\n"
                          +(ROOT/"tools/capture_nes_cross1022.lua").read_text(encoding="utf8"), encoding="utf8")
        with (folder/"mesen.log").open("wb") as log:
            with subprocess.Popen([exe, "--testRunner", script, rom, "--timeout=900", "--doNotSaveSettings",
                                   "--enableStdout", "--preferences.overrideSaveDataFolder=true",
                                   f"--preferences.saveDataFolder={native}", "--debug.scriptWindow.allowIoOsAccess=true"],
                                  cwd=native, stdout=log, stderr=log, creationflags=subprocess.CREATE_NO_WINDOW,
                                  env=dict(os.environ, DOTNET_ROOT="C:/works/dotnet", DOTNET_ROOT_X64="C:/works/dotnet")) as proc:
                try:
                    for _ in range(100):
                        if (native/"reads.bin").exists() or proc.poll() is not None:
                            break
                        time.sleep(0.1)
                    if not (native/"reads.bin").exists():
                        raise RuntimeError("Mesen did not initialize Lua trace")
                    if proc.wait(timeout=920):
                        raise RuntimeError("Mesen failed; see mesen.log")
                finally:
                    if proc.poll() is None:
                        proc.kill()
        for file in ("reads.bin","windows.txt"):
            shutil.copyfile(native/file, folder/file)


def indices(tile, policy):
    low, high = tile & 127, tile >> 7
    if policy == "fold_primary":
        return low ^ high, low
    if policy == "rotated_mirror":
        high = ((high << 1) & 127) | (high >> 6)
    return low, low ^ high


def replay(records, policy):
    # Sealed, initially empty capture bank. Mirrors use available idle ports in this model.
    directory = {}
    demand = {}
    for addr, value in records:
        tile = addr >> 4
        demand[addr] = value
        p, m = indices(tile, policy)
        for slot, mirror in ((p, False), (m, True)):
            previous = directory.get(slot)
            if mirror and (m == p or previous and not previous[1]):
                continue
            if not previous or previous[:2] != (tile, mirror):
                directory[slot] = (tile, mirror, {})
            directory[slot][2][addr & 15] = value
    counts = Counter()
    for addr, value in demand.items():
        tile, lane = divmod(addr, 16)
        for alternate, slot in enumerate(indices(tile, policy)):
            entry = directory.get(slot)
            if entry and entry[:2] == (tile, bool(alternate)) and lane in entry[2]:
                assert entry[2][lane] == value
                counts["mirror" if alternate else "primary"] += 1
                break
        else:
            counts["miss"] += 1
    return counts


def analyze(rom, folder):
    data = rom.read_bytes()
    chr_data = data[16+data[4]*16384:]
    binary = (folder/"reads.bin").read_bytes()
    off = 0
    counters = [{p:Counter() for p in POLICIES} for _ in range(2)]
    totals = [Counter(), Counter()]
    for expected in range(30, 3600, 60):
        frame, n = struct.unpack_from("<II", binary, off)
        assert frame == expected
        off += 8
        records = list(struct.iter_unpack("<IB", binary[off:off+5*n]))
        assert len(records)==n and all(chr_data[a]==v for a,v in records)
        off += 5*n
        if frame <= 60:
            continue
        w = int(frame>1800)
        totals[w].update(frames=1, strokes=n, upper=sum(a>=131072 for a,v in records),
                         aliased_byte_mismatches=sum(chr_data[a & 0x1ffff]!=v for a,v in records),
                         demand=len(set(a for a,v in records)))
        for p in POLICIES:
            counters[w][p].update(replay(records,p))
    assert off==len(binary)
    windows=[list(map(int,s.split())) for s in (folder/"windows.txt").read_text().splitlines()]
    assert [(f,n) for f,c,n in windows]==[(1800,290),(3600,300)]
    result={}
    for i,window in enumerate(("1-30","30-60")):
        _,changes,observations=windows[i]
        for c in counters[i].values():
            assert sum(c.values())==totals[i]["demand"]
        result[window]=dict(totals[i],screen_changes=changes,screen_intervals=observations,policies=counters[i])
    return result


if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode",choices=("capture","report"))
    parser.add_argument("game",choices=GAMES)
    parser.add_argument("rom_dir",type=Path)
    parser.add_argument("work",type=Path)
    parser.add_argument("--mesen",type=Path)
    args=parser.parse_args()
    rom=rom_path(args.rom_dir,args.game)
    folder=args.work.resolve()/args.game
    if args.mode=="capture":
        capture(args.mesen,rom,folder)
    print(json.dumps(analyze(rom,folder),indent=2))
