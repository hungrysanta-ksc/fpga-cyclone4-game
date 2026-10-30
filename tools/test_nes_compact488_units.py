# SPDX-License-Identifier: MIT
"""Actual65816 production decoder on both banks, one/two-row compact and legacy0/3..7.

Synthetic low-plane vectors exercise the decoder ABI, not valid gameplay/HDMA
semantics. Full semantic checks and pixels are in test_nes_compact488_snes.py.
"""
import argparse,json,os,tempfile,random,struct,subprocess
from pathlib import Path
from nes_compact488 import emit_decode488,call
from nes_sinkpack181 import ShortCode
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--mesen',type=Path,default=Path(tempfile.gettempdir())/'nes-coupled165-mesen/Mesen.exe');p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'));a=p.parse_args();a.out=a.out.resolve();assert a.out.as_posix().isascii();a.out.mkdir(parents=True,exist_ok=False)
mesen=str(a.mesen.resolve())
env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']=str(a.dotnet.resolve())
cases=[]
for count in range(8):
 for bank in [0,32768]:
  d=a.out/f'rows{count}-bank{bank}';d.mkdir();rng=random.Random(488+count)
  raw=bytearray(2048)
  for tile in range(32):
   for plane in range(3):
    for row in range(count):raw[tile*64+plane*16+row*2:tile*64+plane*16+row*2+2]=rng.randbytes(2)
   for row in range(count):raw[tile*64+48+row*2]=255
  prefix=rng.randbytes(1121);tail=rng.randbytes(249)
  packed=bytes(raw[t*64+plane*16+row*2+b]for t in range(32)for plane in range(3)for row in range(count)for b in range(2))
  expected=prefix+bytes(raw)+tail if count else prefix
  wire=prefix+(packed if count<=2 else raw)+tail if count else prefix
  c=ShortCode(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0x4b,0xab)
  c.emit(0xe2,0x20);c.store(0x2100,0x80);c.store(0x4200,0);c.emit(0xc2,0x20)
  for addr,v in [(0x1236,0),(0x130,0),(0x100a,len(wire)),(0x1020,bank),(0x1240,count)]:c.emit(0xa9);c.word(v);c.absolute(0x8d,addr)
  c.emit(0xa2,0,0xa0,0xa0);c.word(0x6500+bank);c.emit(0xa9);c.word(len(wire)-1);c.emit(0x8b,0x54,0x7f,0,0xab)
  call(c,'compact488');c.branch(0x90,'bad');c.emit(0xa9,0x5a,0xa5);c.branch(0x80,'done');c.label('bad');c.emit(0xa9,0xef,0xbe);c.label('done');c.absolute(0x8d,0x100);c.emit(0x80,0xfe)
  emit_decode488(c);c.label('service');c.absolute(0xee,0x130);c.emit(0x60)
  rom=bytearray([255])*32768;code=c.finish();assert len(code)<8192;rom[:len(code)]=code;rom[8192:8192+len(wire)]=wire
  rom[0x7fc0:0x7fd5]=b'COMPACT488 ABI UNIT   '[:21];rom[0x7fd5:0x7fd9]=bytes([0x20,0,5,0]);struct.pack_into('<H',rom,0x7ffc,0x8000)
  assert len(rom)==32768;(d/'unit.sfc').write_bytes(rom);(d/'expected.bin').write_bytes(expected)
  lua='''local root=@ROOT@
local f=assert(io.open(root..'/expected.bin','rb'));local expected=f:read('*a');f:close()
emu.addMemoryCallback(function(a,v)
 if v~=0x5a then emu.stop(1);return end
 for i=0,#expected-1 do if emu.read(@BASE@+i,emu.memType.snesWorkRam)~=expected:byte(i+1)then local f=io.open(root..'/error.txt','w');f:write('canonical '..i);f:close();emu.stop(1);return end end
 local f=assert(io.open(root..'/result.json','w'));f:write('{"passed":true}');f:close();emu.stop(0)
end,emu.callbackType.write,0x100,0x100)
emu.addMemoryCallback(function()return 0 end,emu.callbackType.read,0x40000e,0x40000e)
'''.replace('@ROOT@',json.dumps(d.as_posix())).replace('@BASE@',str(0x16500+bank))
  (d/'unit.lua').write_text(lua,encoding='utf8')
  with(d/'mesen.log').open('wb')as log:r=subprocess.run([mesen,'--testRunner',str(d/'unit.lua'),str(d/'unit.sfc'),'--timeout=10','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],env=env,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(count,bank,(d/'error.txt').read_text()if(d/'error.txt').exists()else(d/'mesen.log').read_text(errors='replace')[-500:])
  assert json.loads((d/'result.json').read_text())['passed'];cases.append({'rows':count,'bank':bank,'wire_B':len(wire),'canonical_B':len(expected)})
(a.out/'result.json').write_text(json.dumps({'passed':True,'scope':__doc__,'cases':cases,'physical':False},indent=2)+'\n',encoding='utf8');print(json.dumps({'passed':True,'cases':len(cases)}))
