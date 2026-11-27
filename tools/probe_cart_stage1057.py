import json
import os
from pathlib import Path
import subprocess
import tempfile

from prepare_nes_carts1056 import ROOT
OUT=ROOT.parent/"probes/nes-carts1057"
def vrc_rows(image,trace):
    chr_rom=image[16+image[4]*16384:]
    with (OUT/"rows.txt").open("w") as rows:
        for record in trace.read_text().splitlines():
            offset,expected=(int(x,16) for x in record.split())
            assert expected==chr_rom[offset]
            base=offset & ~8
            rows.write(f"{offset:x} {expected:x} {chr_rom[base]:x} {chr_rom[base+8]:x}\n")

if __name__=="__main__":
    OUT.mkdir(exist_ok=True)
    for mapper,name in [(7,"Battletoads v1.0 (K)"),(21,"WaiwaiWorld 2 (K)")]:
        with tempfile.TemporaryDirectory(prefix="nes-stage-") as folder:
            work=Path(folder)
            (work/"game.nes").write_bytes((Path.home()/"Downloads/test"/(name+".nes")).read_bytes())
            lua=(ROOT/"tests/nes-functional/cart_stage1057.lua").read_text()
            (work/"stage.lua").write_text(lua.replace("@OUT@",json.dumps((work/"stage.txt").as_posix()))
                .replace("@PATTERN@",json.dumps((work/"pattern.txt").as_posix()))
                .replace("@IMAGE@",json.dumps((work/"screen-").as_posix())))
            runner=Path("C:/works/emucap/adapters/mesen2/work/mesen/bin/win-x64/Release/Mesen.exe")
            with (OUT/f"mesen-{mapper}.log").open("wb") as log:
                subprocess.run([runner,"--testRunner","--nes.autoConfigureInput=false","--nes.port1.type=NesController",
                    work/"stage.lua",work/"game.nes","--timeout=180",
                    "--doNotSaveSettings","--enableStdout","--debug.scriptWindow.allowIoOsAccess=true",
                    "--preferences.overrideSaveDataFolder=true","--preferences.saveDataFolder="+folder],
                    cwd=work,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                    stdout=log,stderr=subprocess.STDOUT,check=True,timeout=210,creationflags=subprocess.CREATE_NO_WINDOW)
            (OUT/f"stage-{mapper}.txt").write_bytes((work/"stage.txt").read_bytes())
            (OUT/f"pattern-{mapper}.txt").write_bytes((work/"pattern.txt").read_bytes())
            if mapper==21:
                vrc_rows((work/"game.nes").read_bytes(),work/"pattern.txt")
            for image in work.glob("screen-*.ppm"):
                (OUT/f"screen-{mapper}-{image.stem[7:]}.ppm").write_bytes(image.read_bytes())
