# SPDX-License-Identifier: MIT
"""Same MMC509 calendar and producer. Verify WRAM and VRAM at each actual display."""
import argparse
import json
import shutil
from pathlib import Path
import test_nes_raw506_joint as joint
from test_nes_service509_schedule import Calendar
from nes_transfer512 import legacy_packets
from nes_transfer512_rpc import PipeLink

MAP_ORACLE = """
   local expected=file('map-'..pw(8)..'.bin')
   local wb=0x10000+word(0x1020)+0x5000
   local vb=word(0x1020)==0 and 0x6000 or 0xa000
   for i=0,4095 do
    assert(rd(wb+i)==expected:byte(i+1),'map WRAM '..pw(8)..' '..i)
    assert(emu.read(vb+i,emu.memType.snesVideoRam)==expected:byte(i+1),'map VRAM '..pw(8)..' '..i)
   end
"""

def run_schedule(a, instrument=None):
    a.out=a.out.resolve()
    a.frames,a.cpi,a.spi_us,a.rom_stride,a.rom_phase,a.start=12,2,0,48,0,a.start_clock
    a.candidate=a.capture_gate=True
    joint.Link=PipeLink
    joint.encode=legacy_packets
    emit=joint.lua_rpc
    def observe(args):
        emit(args)
        for g in range(905,917):
            shutil.copyfile(a.capture/f"frame{g}/expected-map.bin",a.out/f"map-{g}.bin")
        path=a.out/"capture.lua"
        text=path.read_text()
        anchor="   local hdma=file('expected-'..pw(8)..'.bin')"
        assert text.count(anchor)==1
        text=text.replace(anchor,MAP_ORACLE+anchor)
        if instrument:text=instrument(text,a)
        path.write_text(text,encoding="utf8")
    joint.lua_rpc=observe
    joint.run(a)
    report=json.loads((a.out/"joint.json").read_text())
    report["parameters"]["ROM_calendar"]=Calendar(a.calendar).summary
    report["map_WRAM_VRAM_verified"]=12
    (a.out/"joint.json").write_text(json.dumps(report,indent=2)+"\n")

if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    for name in ("arm","data","fixture","plans","client","mesen","out","calendar","driver503","capture"):
        p.add_argument("--"+name,type=Path,required=True)
    p.add_argument("--start-clock",type=int,default=3000000)
    a=p.parse_args()
    run_schedule(a)
