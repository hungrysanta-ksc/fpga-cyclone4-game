"""Run the translated FF3 on a private Mesen instance and verify replay after a checkpoint."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import zlib

DIGEST = "f4e33d48c474a9ac7d945d1bafcdcaf01fec9b7d78257357c574b9661ccdd1b5"


def check(exe, rom):
    data = rom.read_bytes()
    if hashlib.sha256(data).hexdigest() != DIGEST:
        raise ValueError("wrong ROM for this reference")
    with tempfile.TemporaryDirectory(prefix="ff3-state-") as tmp:
        folder = Path(tmp)
        image = folder / "ff3.nes"
        shutil.copyfile(rom, image)
        report = folder / "result.txt"
        script = folder / "check.lua"
        script.write_text("OUT="+json.dumps(report.as_posix())+"\n"+
                          Path(__file__).with_name("ff3_state_reference.lua").read_text(), encoding="utf8")
        args = [exe, "--testRunner", script, image, "--timeout=120", "--doNotSaveSettings", "--enableStdout",
                "--preferences.overrideSaveDataFolder=true", f"--preferences.saveDataFolder={folder}",
                "--debug.scriptWindow.allowIoOsAccess=true"]
        proc = subprocess.run(args, cwd=folder, env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",
                              DOTNET_ROOT_X64="C:/works/dotnet"), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                              timeout=140, creationflags=subprocess.CREATE_NO_WINDOW)
        result = report.read_text() if report.exists() else ""
        if proc.returncode or "matched_frames=60" not in result:
            raise RuntimeError(result+"\n"+proc.stdout.decode(errors="replace")[-2000:])
        return dict(oracle="Mesen",sha256=DIGEST, header=data[:16].hex(), full_crc32=f"{zlib.crc32(data):08x}",
                    payload_crc32=f"{zlib.crc32(data[16:]):08x}", **dict(s.split("=") for s in result.splitlines()))


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for key in ("exe","rom","report"):
        p.add_argument(key,type=Path)
    a=p.parse_args()
    a.report.write_text(json.dumps(check(a.exe,a.rom),indent=2)+"\n",encoding="utf8")

