# SPDX-License-Identifier: MIT
"""Private actual-ROM scene/PPUMASK reference; not the transplanted FPGA core."""
from pathlib import Path
import argparse, json, subprocess
from nes_game147 import ROM_SHA, sha


def lua(out):
    return '''local count=0
local OUT="OUTPATH"
local f=assert(io.open(OUT..'/writes.tsv','w'))
emu.addMemoryCallback(function(a,v)
 local s=emu.getState()
 f:write(string.format('%d %d %d %04x %02x\\n',count,s['ppu.scanline'],s['ppu.cycle'],a,v))
end,emu.callbackType.write,0x2000,0x2007,emu.cpuType.nes,emu.memType.nesMemory)
emu.addEventCallback(function()
 emu.setInput({start=(count>=30 and count<34) or (count>=90 and count<96),right=count>=400 and count<420,up=count>=450 and count<470,a=count>=500 and count<506},0)
end,emu.eventType.inputPolled)
emu.addEventCallback(function()
 count=count+1;f:flush()
 if count==130 or count==350 or count==430 or count==480 or count==550 or count==600 or count==650 or count==700 then
  local p=assert(io.open(OUT..'/frame-'..count..'.png','wb'));p:write(emu.takeScreenshot());p:close()
 end
 if count==700 then f:close();emu.stop(0)end
end,emu.eventType.endFrame)
'''.replace('OUTPATH',out.as_posix())


def main():
    p=argparse.ArgumentParser()
    for n in ['rom','mesen','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();assert sha(a.rom)==ROM_SHA
    a.out.mkdir(parents=True)
    (a.out/'capture.lua').write_text(lua(a.out),encoding='utf8')
    with (a.out/'mesen.log').open('wb') as f:
        r=subprocess.run([str(a.mesen),'--testRunner',str(a.out/'capture.lua'),str(a.rom),'--timeout=120','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW,timeout=150)
    assert r.returncode==0,(a.out/'mesen.log').read_text(errors='replace')
    for n in [130,350,430,480,550,600,650,700]:assert (a.out/f'frame-{n}.png').stat().st_size>100
    writes=[]
    for line in (a.out/'writes.tsv').read_text().splitlines():
        f,y,x,a0,v=line.split();writes.append([int(f),int(y),int(x),int(a0,16),int(v,16)])
    masks=[w for w in writes if w[3]==0x2001]
    visible=[w for w in masks if 8<=w[1]<232 and 1<=w[2]<=256]
    summary=dict(completed=True,rom_sha256=ROM_SHA,mesen_sha256=sha(a.mesen),
        core_sha256=sha(a.mesen.parent/'MesenCore.dll'),frames=700,
        pad='START30..33/90..95, RIGHT400..419, UP450..469, A500..505; release between',
        first_visible_mask_write=visible[0],visible_mask_writes=len(visible),
        source_sha256=sha(Path(__file__)),trace_sha256=sha(a.out/'writes.tsv'),
        scope=__doc__,scene_confirmation_required=True)
    (a.out/'result.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))


if __name__=='__main__':main()
