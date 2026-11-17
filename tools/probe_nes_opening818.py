"""Compare no-input NES openings from reset. No ROM or screenshots are distributed."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zlib


LUA = r'''
local out = @OUT@
local f = assert(io.open(out..'/frames.csv','w'))
f:write('frame,obj,changed,sample,masked,mirror\n')
local frame,mask,mirror = 0,0,-1
local sprite_enabled=false
local previous = {}
local before={data_read=0,data_write=0,render_enabled=0}
local function monitor(a,v,write)
 if a%8==7 then
  local key=write and 'data_write' or 'data_read'
  before[key]=before[key]+1
 end
 if write and a%8==1 and (v & 24)~=0 then before.render_enabled=before.render_enabled+1 end
end
local function rd(a,v) if mirror<0 then monitor(a,v,false) end end
local function wr(a,v) if mirror<0 then monitor(a,v,true) end end
emu.addMemoryCallback(rd,emu.callbackType.read,0x2000,0x3fff,emu.cpuType.nes,emu.memType.nesMemory)
emu.addMemoryCallback(wr,emu.callbackType.write,0x2000,0x3fff,emu.cpuType.nes,emu.memType.nesMemory)
local function write(a,v)
 if a==0x2001 then
  mask=v
  if (mask & 16)~=0 then sprite_enabled=true end
 elseif a%2==0 then
  if mirror<0 then
   local z=assert(io.open(out..'/reset.csv','w'))
   z:write(string.format('%d,%d,%d,%d,%d\n',frame+1,v&1,before.data_read,before.data_write,before.render_enabled));z:close()
  end
  mirror=v & 1
 end
end
emu.addMemoryCallback(write,emu.callbackType.write,0x2001,0x2001,emu.cpuType.nes,emu.memType.nesMemory)
emu.addMemoryCallback(write,emu.callbackType.write,0xa000,0xbfff,emu.cpuType.nes,emu.memType.nesMemory)
emu.addEventCallback(function()
 frame=frame+1
 local n,changed=0,0
 local current={}
 for i=0,63 do
  local a=i*4
  local y=emu.read(a,emu.memType.nesSpriteRam)
  if y<239 and sprite_enabled then
   local value=y
   for j=1,3 do value=(value<<8)|emu.read(a+j,emu.memType.nesSpriteRam) end
   current[i]=value
   n=n+1
  end
  if current[i]~=previous[i] then changed=changed+1 end
 end
 previous=current
 sprite_enabled=(mask & 16)~=0
 local h=-1
 if frame%6==0 then
  local s=emu.getScreenBuffer()
  h=0
  for i=1,#s,113 do h=(h*31+s[i]) & 0x7fffffff end
 end
 f:write(string.format('%d,%d,%d,%d,%d,%d\n',frame,n,changed,h,mask,mirror))
 if frame%300==0 then
  local p=assert(io.open(out..'/frame'..frame..'.png','wb'))
  p:write(emu.takeScreenshot());p:close()
 end
 if frame==3600 then f:close();emu.stop(0) end
end,emu.eventType.endFrame)
'''


def run(rom,mesen,out,hide_sprites=False):
    out=out.resolve()
    out.mkdir(parents=True,exist_ok=False)
    game=rom.read_bytes()
    lua=out/'measure.lua'
    lua.write_text(LUA.replace('@OUT@',json.dumps(out.as_posix(),ensure_ascii=False)),encoding='utf8')
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([mesen,'--testRunner',lua,rom,'--timeout=180','--doNotSaveSettings','--enableStdout',
                        '--debug.scriptWindow.allowIoOsAccess=true',*(['--nes.disableSprites=true'] if hide_sprites else [])],
                       stdout=log,stderr=subprocess.STDOUT,
                       cwd=out,timeout=210,check=True,creationflags=subprocess.CREATE_NO_WINDOW,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    with (out/'frames.csv').open() as f:
        rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]
    assert [r['frame'] for r in rows]==list(range(1,3601))
    windows={}
    for start,end in ((5,40),(40,55)):
        subset=rows[start*60:end*60]
        screen=[r['sample'] for r in rows[start*60-1:end*60] if r['sample']>=0]
        windows[f'{start}-{end}']=dict(frames=len(subset),mean_visible_OAM=sum(r['obj'] for r in subset)/len(subset),
            active_OAM_frames=sum(r['changed']>0 for r in subset),max_OAM=max(r['obj'] for r in subset),
            changed_screen_samples=sum(a!=b for a,b in zip(screen,screen[1:])),screen_intervals=len(screen)-1)
    reset=dict(zip(('frame','A000_bit0','before_PPUDATA_reads','before_PPUDATA_writes','before_render_enable'),
                   map(int,(out/'reset.csv').read_text().strip().split(',')),strict=True))
    data=dict(sha256=hashlib.sha256(game).hexdigest(),header=game[:16].hex(),file_crc32=f'{zlib.crc32(game):08x}',reset=reset,
              windows=windows,first_A000_frame=next((r['frame'] for r in rows if r['mirror']>=0),None),
              frames_sha256=hashlib.sha256((out/'frames.csv').read_bytes()).hexdigest())
    (out/'result.json').write_text(json.dumps(data,indent=2)+'\n')
    print(json.dumps(data))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('rom','mesen','out'):
        p.add_argument(name,type=Path)
    p.add_argument('--hide-sprites',action='store_true')
    a=p.parse_args()
    run(a.rom.resolve(),a.mesen.resolve(),a.out,a.hide_sprites)
