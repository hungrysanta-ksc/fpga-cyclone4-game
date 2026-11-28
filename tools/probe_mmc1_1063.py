"""Collect mapper writes and physical address samples for the two 256 KiB Zelda cartridges."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
from zlib import crc32

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT.parent / "probes/nes-mmc1-1063"
MESEN = Path("C:/works/emucap/adapters/mesen2/work/mesen/bin/win-x64/Release/Mesen.exe")

def capture(folder):
    OUT.mkdir(parents=True, exist_ok=True)
    summary = {}
    for number in (1, 2):
        rom = folder / f"Zelda no Densetsu {number} (K).nes"
        image = rom.read_bytes()
        assert image[:16] == bytes.fromhex("4e45531a100012000000000000000000") and len(image)==262160
        trace = OUT / f"zelda{number}.trace"
        with tempfile.TemporaryDirectory(prefix="mmc1-reference-") as directory:
            work = Path(directory)
            lua = work / "cart.lua"
            capture = (ROOT / "tests/nes-functional/cart1056.lua").read_text()
            capture = capture.replace("@OUT@", json.dumps((work/"summary").as_posix())).replace("@BUS@",json.dumps((work/"bus").as_posix()))
            capture = capture.replace('bus:write(string.format("0 %04x %02x\\n",a,v))',
                   'bus:write(string.format("0 %04x %02x %x\\n",a,v,emu.getState().masterClock))')
            capture = capture.replace("local frames=0", """local frames=0
emu.addEventCallback(function()
 emu.setInput({start=frames>=240 and frames%180<4,
               a=frames%83<4,right=frames>900 and frames%127<75},0)
end,emu.eventType.inputPolled)""")
            lua.write_text(capture)
            with (OUT / f"reference-{number}.log").open("wb") as log:
                subprocess.run([MESEN,"--testRunner","--nes.autoConfigureInput=false",
                         "--nes.port1.type=NesController",lua,rom,"--timeout=180","--enableStdout",
                         "--doNotSaveSettings","--debug.scriptWindow.allowIoOsAccess=true",
                         "--preferences.overrideSaveDataFolder=true","--preferences.saveDataFolder="+directory],
                         env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                         cwd=work,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=200,
                         creationflags=subprocess.CREATE_NO_WINDOW)
            trace.write_bytes((work/"bus").read_bytes())
            rows=(work/"summary").read_text().splitlines()
            assert rows[-1]=="END 1800"
            summary[str(number)]=dict(crc32=f"{crc32(image):08x}",frames=1800,
                picture_hashes=len(set(s.split()[-1] for s in rows if s.startswith("FRAME "))))
    (OUT/"reference.json").write_text(json.dumps(summary,indent=2))

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("folder",type=Path)
    capture(parser.parse_args().folder)
