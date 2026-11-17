"""Compare all no-input pictures to a background-only reference and locate natural split-crossing sprites."""
import csv
import io
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from PIL import Image
from prepare_nes_opening818 import ADVENTURE_SHA
from run_nes_geometry230 import sha

LUA = r"""
local png=assert(io.open("frames.bin","wb"))
local meta=assert(io.open("info.csv","w"))
local mask,last,dot=0,0,-1
emu.addMemoryCallback(function(a,v)
 if a%8~=1 then return end
 if mask~=v and v==14 then
  local s=emu.getState()
  if s["ppu.scanline"]==192 then dot=s["ppu.cycle"] end
 end
 mask=v
end,emu.callbackType.write,0x2000,0x3fff,emu.cpuType.nes,emu.memType.nesMemory)
emu.addEventCallback(function()
 last=last+1
 local img=emu.takeScreenshot()
 -- takeScreenshot returns the preceding completed picture at endFrame.
 if last>1 then png:write(string.pack("<I4",#img),img) end
 if last==3601 then png:close();meta:close();emu.stop(0);return end
 local crossing={}
 local height=emu.getState()["ppu.control.largeSprites"] and 16 or 8
 for i=0,63 do
  local top=emu.read(i*4,emu.memType.nesSpriteRam)+1

  if top<192 and top+height>193 then crossing[#crossing+1]=i end
 end
 meta:write(last,",",dot,",",#crossing,"\n")
 dot=-1

end,emu.eventType.endFrame)
"""

def collect(rom,mesen,root):
    assert sha(rom)==ADVENTURE_SHA
    for mode in ("normal","bg"):
        d=root/mode
        d.mkdir(parents=True,exist_ok=False)
        script=d/"capture.lua"
        script.write_text(LUA.replace('"frames.bin"', json.dumps((d/"frames.bin").as_posix())).replace('"info.csv"', json.dumps((d/"info.csv").as_posix())))
        with (d/"run.log").open("wb") as log:
            subprocess.run([mesen,"--testRunner",script,rom,"--timeout=360","--doNotSaveSettings",
                "--enableStdout","--debug.scriptWindow.allowIoOsAccess=true",
                *(["--nes.disableSprites=true"] if mode=="bg" else [])],cwd=d,stdout=log,stderr=subprocess.STDOUT,
                env=dict(os.environ,DOTNET_ROOT="C:/works/dotnet",DOTNET_ROOT_X64="C:/works/dotnet"),
                creationflags=subprocess.CREATE_NO_WINDOW,check=True,timeout=380)

def review(root):
    from PIL import ImageChops
    a=list(csv.reader((root/"normal/info.csv").open()))
    b=list(csv.reader((root/"bg/info.csv").open()))
    assert a==b and len(a)==3600
    def picture(f):
        size,=struct.unpack("<I",f.read(4))
        assert size>0
        im=Image.open(io.BytesIO(f.read(size))).convert("RGB")
        assert im.size==(256,240)
        return im
    crossing=[]
    below=[]
    dots=set()
    n=0
    changes=[0,0]
    prev=None
    with (root/"normal/frames.bin").open("rb") as normal,(root/"bg/frames.bin").open("rb") as hidden:
        for i,d,c in a:
            i,d,c=map(int,(i,d,c))
            im,bg=picture(normal),picture(hidden)
            if im is None or bg is None:
                assert i==1 and im is None and bg is None
                continue
            if prev is not None and im.tobytes()!=prev:
                if 301<=i<=2400:changes[0]+=1
                if 2401<=i<=3300:changes[1]+=1
            prev=im.tobytes()
            if d<0:continue
            n+=1
            dots.add(d)
            dif=ImageChops.difference(im,bg)
            if dif.crop((0,193,256,232)).getbbox():below.append(i)
            if c and dif.crop((0,192,256,193)).getbbox():crossing.append(i)
        assert not normal.read(1) and not hidden.read(1)
    print(dict(split=n,dots=sorted(dots),below=below[:10],crossing=crossing[:12],changed=changes))
    (root/"result.json").write_text(json.dumps(dict(frames=3600,split=n,dots=sorted(dots),
        bg_mismatch_frames=below,crossing=crossing,changed_reference_frames=changes)))
    assert n and not below

if __name__=="__main__":
    rom,mesen,root=[Path(s).resolve() for s in sys.argv[1:]]
    collect(rom,mesen,root)
    review(root)
