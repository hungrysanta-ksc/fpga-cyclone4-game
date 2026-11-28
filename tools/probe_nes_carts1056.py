"""Inspect user-supplied cartridges and run the local Mesen reference without distributing ROMs."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "probes/nes-carts1056"
GAMES = ("Moai Kun (K)", "Battletoads v1.0 (K)", "WaiwaiWorld 2 (K)", "Dragon Quest IV (K1.2)")

def probe(mesen, folder):
    OUT.mkdir(exist_ok=True)
    report = {}
    for i,game in enumerate(GAMES):
        rom = (folder / (game + ".nes")).read_bytes()
        h = rom[:16]
        assert h[:4]==b"NES\x1a" and len(rom)==16+16384*h[4]+8192*h[5]
        with tempfile.TemporaryDirectory(prefix="cart1056-") as tmp:
            d = Path(tmp)
            (d/"game.nes").write_bytes(rom)
            (d/"trace.lua").write_text((ROOT/"tests/nes-functional/cart1056.lua").read_text()
                                      .replace("@OUT@", json.dumps((d/"trace").as_posix()))
                                      .replace("@BUS@", json.dumps((d/"bus").as_posix())))
            with (OUT/f"mesen-{i}.log").open("wb") as log:
                subprocess.run([mesen,"--testRunner",d/"trace.lua",d/"game.nes","--timeout=160",
                                "--doNotSaveSettings","--enableStdout","--debug.scriptWindow.allowIoOsAccess=true",
                                "--preferences.overrideSaveDataFolder=true","--preferences.saveDataFolder="+tmp],
                               cwd=d,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=200,
                               creationflags=subprocess.CREATE_NO_WINDOW,
                               env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"))
            lines=(d/"trace").read_text().splitlines()
            assert lines[-1]=="END 1800"
            shutil.copyfile(d/"trace",OUT/f"registers-{i}.txt")
            shutil.copyfile(d/"bus",OUT/f"mapper-{(h[6]>>4)|(h[7]&240)}.hex")
        report[game]=dict(mapper=(h[6]>>4)|(h[7]&240),header=h.hex(),sha256=hashlib.sha256(rom).hexdigest(),
                          prg=h[4]*16384,chr_rom=h[5]*8192,samples=[s for s in lines if s.startswith("FRAME ")])
    (OUT/"reference.json").write_text(json.dumps(report,indent=2))

if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("mesen",type=Path)
    p.add_argument("folder",type=Path)
    a=p.parse_args()
    probe(a.mesen,a.folder)
