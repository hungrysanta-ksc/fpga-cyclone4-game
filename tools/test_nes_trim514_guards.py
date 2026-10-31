# SPDX-License-Identifier: MIT
"""Replay actual producer packets on the assembled 65816; inject faults at map validation."""
import argparse
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from test_nes_output489_snes import LUA
from test_nes_trim514_schedule import MAP_ORACLE

SETUP = """
local function bank_image(bank,video)
 local bytes={}
 for i=0,4095 do
  local v=video and emu.read((bank==0 and 0x6000 or 0xa000)+i,emu.memType.snesVideoRam)
              or rd(0x15000+0x8000*bank+i)
  bytes[i+1]=string.char(v)
 end
 return table.concat(bytes)
end
local validating,trigger,partial,visibleBefore,targetBefore=false,false,false,nil,nil
local function save_maps()
 for b=0,1 do
  for _,v in ipairs({false,true})do
   local name=string.format('%s-%d.bin',v and 'vram' or 'wram',b)
   local f=assert(io.open(ROOT..'/'..name,'wb'));f:write(bank_image(b,v));f:close()
  end
 end
end
if MODE=='normal' then
 for b=0,1 do for _,v in ipairs({false,true})do
  local data=file(string.format('initial-%s-%d.bin',v and 'vram' or 'wram',b))
  for i=0,4095 do emu.write((v and (b==0 and 0x6000 or 0xa000) or (0x15000+b*0x8000))+i,data:byte(i+1),v and emu.memType.snesVideoRam or emu.memType.snesWorkRam)end
 end end
 emu.write(0x1260,1,emu.memType.snesWorkRam);emu.write(0x1261,1,emu.memType.snesWorkRam)
end
emu.addMemoryCallback(function()validating=true end,emu.callbackType.exec,@EDGE@)
"""
LOADED = """
 if pw(8)==FAULT and not trigger then
  local op=pb(0)
  if op==10 then partial=true end
  if MODE=='cold_partial' and op==10 then
   local crc=65535
   for i=pw(10)-8,pw(10)-1 do
    crc=crc~(rd(0x15000+i)<<8)
    for bit=0,7 do crc=((crc<<1)~((crc&0x8000)~=0 and 0x1021 or 0))&65535 end
   end
   packet=packet:sub(1,14)..string.pack('<I2',crc)..packet:sub(17)
  end
  if MODE=='cold_missing' and op==3 then
   for i=0,7 do emu.write(0x13b0+i,255,emu.memType.snesWorkRam)end
  end
  if (op==10 and MODE~='stop_final') or (op==3 and (MODE=='cold_missing' or MODE=='stop_final')) then
   trigger=true
   if MODE=='stop_final' then assert(partial,'no partial record before final STOP')end
   local bank=(pw(8)-905)&1
   if MODE=='omitted_corrupt' then
    local at,len=pw(10),pw(12);local omitted=at%64>0 and (at//64*64) or (at+len)
    local address=0x15000+bank*0x8000+omitted
    emu.write(address,rd(address)~1,emu.memType.snesWorkRam)
   end
   visibleBefore=bank_image(1-bank,true);targetBefore=bank_image(bank,false)
  end
 end
"""
FAILED = """
   assert(trigger and rd(0x1260)==0 and rd(0x1261)==0,'STOP/fault did not retire both histories')
   local bank=(FAULT-905)&1
   assert(bank_image(1-bank,true)==visibleBefore,'previous visible map changed')
   assert(bank_image(bank,false)==targetBefore,'rejected map wrote destination')
   if MODE=='stop_check' then assert(validating and lastStatus==0xe4,'STOP was not observed at check')end
   save_maps()
"""
def main(a):
    rows=[]
    for l in (a.trace/'packets.jsonl').read_text().splitlines():
        _,_,b,t=json.loads(l)
        b=bytes.fromhex(b)
        if int.from_bytes(b[8:10],'little')>907:
            break
        rows.append((b,bytes.fromhex(t)))
    assert rows[-1][0][0]==3 and rows[-1][0][8:10]==struct.pack('<H',907)
    a.out.mkdir(parents=True,exist_ok=False)
    results={}
    for mode in ('cold_partial','cold_missing','bad_crc','omitted_corrupt','wrong_section','unaligned','overspan','stop_check','stop_final','normal'):
        d=a.out/mode
        d.mkdir()
        fixture=list(rows)
        cold=mode.startswith('cold')
        fault=905 if cold else 907
        frames=2 if mode=='normal' else 3
        if frames==2:
            fixture=[r for r in fixture if int.from_bytes(r[0][8:10],'little')<907]
        if cold or mode in ('bad_crc','wrong_section','unaligned','overspan'):
            for i,(packet,tile) in enumerate(fixture):
                op,section=packet[:2]
                if cold and section==2 and op in (2,4):
                    at,n,span=struct.unpack_from('<3H',packet,10)
                    raw=packet[16:] if op==2 else packet[16:18]*(span//2)
                    if len(raw)<128:continue
                    p=bytearray(packet[:16])
                    cut=8 if mode=='cold_partial' else 64
                    p[0]=10 if cut==8 else 2
                    struct.pack_into('<3H',p,10,at+cut,len(raw)-cut,0)
                    fixture[i]=bytes(p)+raw[cut:],tile
                    break
                if op==10:
                    p=bytearray(packet)
                    if mode=='bad_crc':p[14]^=1
                    elif mode=='wrong_section':p[1]=3
                    elif mode=='unaligned':p[10]|=1
                    else:
                        struct.pack_into('<HH',p,10,8,192)
                        p[16:]=bytes(192)
                    fixture[i]=bytes(p),tile
                    break
            else:raise AssertionError('fault packet not found')
        (d/'requests.bin').write_bytes(b''.join(struct.pack('<H',len(b))+b for b,_ in fixture))
        for i,(_,tile) in enumerate(fixture,1):
            if tile:(d/f'tile-{i:04d}.bin').write_bytes(tile)
        for g in range(905,908):
            for prefix in ('map','expected'):
                shutil.copyfile(a.trace/f'{prefix}-{g}.bin',d/f'{prefix}-{g}.bin')
        shutil.copyfile(a.client/'sink165.sfc',d/'client.sfc')
        if mode=='normal':
            for name in ('vram','wram'):
                for bank in (0,1):
                    shutil.copyfile(a.out/f'stop_final/{name}-{bank}.bin',d/f'initial-{name}-{bank}.bin')
        lua=LUA.replace('local function loaded()',SETUP+'\nlocal function loaded()')
        lua=lua.replace(' if MODE~=',LOADED+'\n if MODE~=',1)
        lua=lua.replace('  if COMPACT and packet', "  if MODE=='stop_check' and trigger and validating then return 128 end\n  if COMPACT and packet",1)
        lua=lua.replace("   local hdma=file(",MAP_ORACLE+"   local hdma=file(",1)
        lua=lua.replace("   local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb'",FAILED+"   local screen=emu.getScreenBuffer();local f=assert(io.open(ROOT..'/retained.rgb'")
        edge=json.loads((a.client/'labels.json').read_text())['edge_byte514']
        for key,val in dict(ROOT=json.dumps(d.as_posix()),MODE=json.dumps(mode),TOTAL=len(fixture),FRAMES=frames,
                            SCHEDULE='"continuous"',START=3000000,FAULT=fault,POISON='false',COMPACT='true',EDGE=edge).items():
            lua=lua.replace('@'+key+'@',str(val))
        (d/'capture.lua').write_text(lua,encoding='utf8')
        with (d/'mesen.log').open('wb') as log:
            run=subprocess.run([str(a.mesen),'--testRunner',str(d/'capture.lua'),str(d/'client.sfc'),'--timeout=120',
                                '--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true',
                                '--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],
                               env=dict(os.environ,DOTNET_ROOT=str(a.dotnet)),cwd=d,stdout=log,stderr=subprocess.STDOUT,
                               timeout=135,creationflags=subprocess.CREATE_NO_WINDOW)
        assert run.returncode==0,(mode,(d/'mesen.log').read_text(errors='replace')[-1800:])
        results[mode]=json.loads((d/'result.json').read_text())
        assert results[mode]['passed']
        if mode!='normal':
            for name in ('vram','wram'):
                for bank in (0,1):
                    assert (d/f'{name}-{bank}.bin').stat().st_size==4096
            if not cold:
                assert (d/'retained.rgb').read_bytes()==(d/'frame-906.rgb').read_bytes(),mode
        print(mode,results[mode]['commits'],results[mode]['last_status'],flush=True)
    (a.out/'guards.json').write_text(json.dumps(results,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('trace','client','out','mesen'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'))
    a=p.parse_args();a.out=a.out.resolve();a.client=a.client.resolve();main(a)
