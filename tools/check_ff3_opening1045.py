"""Compare opening pixels and the FF3 PPU's write times to the board capture window."""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import struct
from pathlib import Path

from check_ff3_state_reference import DIGEST

SCRIPT = """
local events,frames=assert(io.open(WRITES,'w')),assert(io.open(FRAMES,'w'))
local frame,changes,mask=0,0,0
local masks={}
emu.addMemoryCallback(function(a,v)
 mask=v
 masks[v]=true
 if NORMALIZE and v==0x0a then return 0x0e end
end,emu.callbackType.write,0x2001,0x2001,emu.cpuType.nes,emu.memType.nesMemory)
emu.addMemoryCallback(function(a,v)
 local s=emu.getState()
 local row,dot=s['ppu.scanline'],s['ppu.cycle']
 events:write(frame,' ',row,' ',dot,'\\n')
 changes=changes+1
end,emu.callbackType.write,0,0x1fff,emu.cpuType.nes,emu.memType.nesPpuMemory)
emu.addEventCallback(function()
 local screen=emu.getScreenBuffer()
 if PIXELS and (frame==17 or frame==18 or frame==40 or frame==120 or frame==599 or frame==1799) then
  local fp=assert(io.open(PIXELS,'ab'))
  local packed={}
  for i=1,#screen do packed[i]=string.pack('<I4',screen[i] & 0xffffffff) end
  fp:write(string.pack('<I4I4',frame,#screen),table.concat(packed));fp:close()
 end
 local picture=0
 for i=2,#screen do if screen[i]~=screen[1] then picture=1;break end end
 local values={}
 for value in pairs(masks) do table.insert(values,value) end
 table.sort(values)
 frames:write(frame,' ',picture,' ',changes,' ',mask,' ',#values,'\\n')
 frame=frame+1;changes=0;masks={}
 if frame==N then events:close();frames:close();emu.stop(0) end
end,emu.eventType.endFrame)
"""


def run(out, n, normalize=False, pixels=None):
    exe=Path('C:/works/emucap/adapters/mesen2/work/mesen/bin/win-x64/Release/Mesen.exe')
    rom=next(p for p in (Path.home()/'Downloads/test').glob('Final Fantasy III*.nes')
             if hashlib.sha256(p.read_bytes()).hexdigest()==DIGEST)
    out.mkdir(exist_ok=True,parents=True)
    with tempfile.TemporaryDirectory(prefix='ff3-open-') as tmp:
        tmp=Path(tmp)
        shutil.copyfile(rom,tmp/'game.nes')
        (tmp/'trace.lua').write_text('NORMALIZE='+('true' if normalize else 'false')+'\nPIXELS='+(json.dumps((tmp/'pixels.bin').as_posix()) if pixels else 'nil')+'\nN='+str(n)+'\nWRITES='+json.dumps((tmp/'events.txt').as_posix())+
             '\nFRAMES='+json.dumps((tmp/'frames.txt').as_posix())+'\n'+SCRIPT)
        env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet')
        with (out/'opening-mesen.log').open('wb') as log:
            subprocess.run([exe,'--testRunner',tmp/'trace.lua',tmp/'game.nes','--timeout=180',
                '--doNotSaveSettings','--preferences.overrideSaveDataFolder=true',
                '--preferences.saveDataFolder='+str(tmp),'--debug.scriptWindow.allowIoOsAccess=true'],
                cwd=tmp,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=200,check=True,
                creationflags=subprocess.CREATE_NO_WINDOW)
        if pixels:
            shutil.copyfile(tmp/'pixels.bin',pixels)
        for file in ('events.txt','frames.txt'):
            shutil.copyfile(tmp/file,out/('opening-'+file))
    frames=[list(map(int,l.split())) for l in (out/'opening-frames.txt').read_text().splitlines()]
    assert len(frames)==n and any(f[1] for f in frames) and sum(f[2] for f in frames)>0
    print('reference frames',n,'nonuniform',sum(f[1] for f in frames),'CHR writes',sum(f[2] for f in frames))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('out',type=Path)
    p.add_argument('--frames',type=int,default=1800)
    p.add_argument('--compare-opening-pixels',action='store_true')
    args=p.parse_args()
    if args.compare_opening_pixels:
        assert args.frames==1800
        with tempfile.TemporaryDirectory() as tmp:
            original=Path(tmp)/'original.bin'
            normalized=Path(tmp)/'normalized.bin'
            run(args.out/'original',args.frames,pixels=original)
            run(args.out/'normalized',args.frames,normalize=True,pixels=normalized)
            data=original.read_bytes()
            assert normalized.read_bytes()==data
            at=0
            for frame in (17,18,40,120,599,1799):
                number,count=struct.unpack_from('<II',data,at)
                assert number==frame and count==256*240
                at+=8+count*4
            assert at==len(data)
            (args.out/'pixels.json').write_text(json.dumps(dict(frames=6,pixels=6*256*240,
                masks=[10,14],matched=True)))
            print('PASS 6 complete reference rasters, 368640 pixels')
    else:
        run(args.out,args.frames)
