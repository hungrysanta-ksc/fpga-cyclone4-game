# SPDX-License-Identifier: MIT
"""Call the exact linked mark212 bytes with bitmap carries, duplicate units and both banks."""
import argparse
import json
import os
from pathlib import Path
import subprocess

from nes_sinkpack181 import ShortCode


def run(client, mesen, out):
    out.mkdir(parents=True,exist_ok=False)
    labels=json.loads((client/'labels.json').read_text())
    body=(client/'body.bin').read_bytes()
    shim=ShortCode(0x2000+len(body))
    shim.label('again');shim.emit(0xe2,0x20);shim.store(0x100,1)
    shim.emit(0xc2,0x30);shim.absolute(0xae,0x102);shim.absolute(0x20,labels['mark212']&65535)
    shim.emit(0x08,0xe2,0x20,0x68);shim.absolute(0x8d,0x101);shim.branch(0x80,'again')
    shim.finish()
    image=body+shim.data
    c=ShortCode(0x8000)
    c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b)
    c.emit(0xa9);c.word(len(image)-1);c.emit(0xa2,0,0x90,0xa0,0,0x20,0x54,0x7e,0x00,0x4b,0xab)
    c.emit(0x5c);c.word(shim.base);c.emit(0x7e)
    rom=bytearray((client/'sink165.sfc').read_bytes())
    rom[:len(c.data)]=c.data;rom[0x1000:0x1000+len(image)]=image;rom[0x7ffc:0x7ffe]=bytes([0,128])
    (out/'test.sfc').write_bytes(rom)
    lua=r"""local root=@ROOT@
local mem=emu.memType.snesWorkRam
local function put(a,v) emu.write(a,v&255,mem);emu.write(a+1,v>>8,mem)end
local cases={}
for bank=0,1 do for sec=0,2 do
 local unit=({16,32,64})[sec+1];local extent=({1024,128,64})[sec+1]
 for _,span in ipairs({{0,1},{7,3},{8,8},{15,17},{extent-3,3},{0,4096//unit}})do
  for _,dup in ipairs({-1,0,span[2]-1})do
   cases[#cases+1]={bank,sec,unit,span[1],span[2],dup}
  end
 end
end end
local done=0;local expected={}
local function check(v)
 if not v then local f=assert(io.open(root..'/failure.txt','w'));f:write(done+1);f:close();emu.stop(1);error('unit failed')end
end
emu.addMemoryCallback(function()
 local q=cases[done+1];local bank,sec,unit,start,n,dup=table.unpack(q)
 put(0x102,sec*2);put(0x1200,sec==2 and 2 or 7);put(0x120a,start*unit);put(0x120c,n*unit)
 put(0x1034,bank);put(0x1020,bank*32768);put(0x1250,0);put(0x1252,0);put(0x1254,bank*152)
 expected={};for i=0x127f,0x1450 do expected[i]=0xa5 end
 for i=0,151 do expected[0x1280+i]=0 end
 local first=({0,1024,1152})[sec+1]+start
 local function mark(base,bit)
  local a=base+bit//8;expected[a]=expected[a]|(1<<(bit%8))
 end
 if dup>=0 then mark(0x1280,first+dup)end
 for a,v in pairs(expected)do emu.write(a,v,mem)end
 for j=0,n-1 do if j==dup then break end
  mark(0x1280,first+j);mark(0x1320+bank*152,first+j)
 end
end,emu.callbackType.write,0x100)
emu.addMemoryCallback(function(_,flags)
 local ok=cases[done+1][6]<0
 check((flags&0x30)==0 and ((flags&1)==1)==ok)
 for a,v in pairs(expected)do check(emu.read(a,mem)==v)end
 check(emu.read(0x1250,mem)==(ok and 8 or 0))
 done=done+1;if done==#cases then local f=assert(io.open(root..'/cases.json','w'));f:write(done);f:close();emu.stop(0)end
end,emu.callbackType.write,0x101)
"""
    script=out/'test.lua'
    script.write_text(lua.replace('@ROOT@',json.dumps(out.as_posix())))
    with (out/'mesen.log').open('wb') as log:
        subprocess.run([str(mesen), '--testRunner', str(script),str(out/'test.sfc'),'--timeout=45','--doNotSaveSettings',
                        '--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=out,stdout=log,stderr=subprocess.STDOUT,
                       env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),
                       creationflags=subprocess.CREATE_NO_WINDOW,timeout=55,check=True)
    assert json.loads((out/'cases.json').read_text())==108


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();run(a.client,a.mesen.resolve(),a.out.resolve())
