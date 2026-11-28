"""Measure original OAM scanline occupancy during two segments of the existing route."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zlib
from prepare_cart_debug1060 import OUT
from prepare_nes_carts1056 import ROOT


def probe():
    image=(Path.home()/"Downloads/test/Battletoads v1.0 (K).nes").read_bytes()
    assert zlib.crc32(image)==0xca40be7e
    with tempfile.TemporaryDirectory(prefix="battle-oam-") as path:
        work=Path(path)
        (work/"game.nes").write_bytes(image)
        dump=work/"oam.txt"
        (work/"stage.lua").write_text("local OUTPUT="+json.dumps(dump.as_posix())+"\n"+
            (ROOT/"tests/nes-functional/battletoads_oam1060.lua").read_text())
        runner=Path("C:/works/emucap/adapters/mesen2/work/mesen/bin/win-x64/Release/Mesen.exe")
        with (OUT/"battle-oam.log").open("wb") as log:
            subprocess.run([runner,"--testRunner","--nes.autoConfigureInput=false","--nes.port1.type=NesController",
                work/"stage.lua",work/"game.nes","--timeout=180","--doNotSaveSettings","--enableStdout",
                "--debug.scriptWindow.allowIoOsAccess=true","--preferences.overrideSaveDataFolder=true",
                "--preferences.saveDataFolder="+path],cwd=work,env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",
                DOTNET_ROOT_X64="C:/works/dotnet"),stdout=log,stderr=subprocess.STDOUT,check=True,timeout=210,
                creationflags=subprocess.CREATE_NO_WINDOW)
        windows={}
        for line in dump.read_text().splitlines():
            frame,ctrl,hex_oam=line.split()
            oam=bytes.fromhex(hex_oam)
            assert len(oam)==256
            height=16 if int(ctrl)&32 else 8
            loads=[sum(top<line<=top+height for top in oam[::4]) for line in range(8,232)]
            samples=windows.setdefault(2100 if int(frame)<2160 else 6000,[])
            samples.append(max(loads))
        assert set(windows)=={2100,6000} and all(len(v)==60 for v in windows.values())
        return {k:dict(frames=len(v),over_eight=sum(n>8 for n in v),max_per_line=max(v)) for k,v in windows.items()}


if __name__=="__main__":
    result=probe()
    print(result)
    (OUT/"battle-oam.json").write_text(json.dumps(result,indent=2))
