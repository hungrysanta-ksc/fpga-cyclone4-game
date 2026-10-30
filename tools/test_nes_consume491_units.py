# SPDX-License-Identifier: MIT
"""Actual65816 bounded word expansion: patterns, lengths, banks and STOP prefixes."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from nes_sinkpack181 import ShortCode
from nes_consume491 import emit_repeat491,call

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['out','mesen']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--dotnet',type=Path,default=Path('C:/works/dotnet'));a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(exist_ok=False)
    assert a.out.as_posix().isascii()
    cases=[{'n':n,'word':word,'dest':dest,'stop':stop}for n in [2,4,64,66,240,4096]for word in [0,65535,0x1234]for dest in [0,0x8000]for stop in [0,1,2]]
    c=ShortCode(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0x4b,0xab)
    c.emit(0xe2,0x20);c.store(0x2100,0x80);c.store(0x4200,0);c.emit(0xc2,0x20)
    for i,q in enumerate(cases):
        c.emit(0xe2,0x20);c.store(0x102,i);c.store(0x2183,1);c.emit(0xc2,0x20)
        for addr,v in [(0x120c,q['n']),(0x7a,q['dest']),(0x2181,q['dest']),(0x1236,0),(0x130,0)]:c.emit(0xa9);c.word(v);c.absolute(0x8d,addr)
        call(c,'repeat491');c.emit(0xe2,0x20);c.store(0x100,0x5a);c.emit(0xc2,0x20)
    c.emit(0x80,0xfe);emit_repeat491(c)
    c.label('service');c.absolute(0xee,0x130);c.emit(0xe2,0x20);c.absolute(0xad,0x104);c.branch(0xf0,'service_ok');c.absolute(0xcd,0x130);c.branch(0xd0,'service_ok');c.store(0x1236,1)
    c.label('service_ok');c.emit(0xc2,0x20,0x60)
    code=c.finish();rom=bytearray([255])*32768;assert len(code)<30000;rom[:len(code)]=code
    rom[0x7fc0:0x7fd5]=b'CONSUME491 RLE UNIT   '[:21];rom[0x7fd5:0x7fd9]=bytes([0x20,0,5,0]);struct.pack_into('<H',rom,0x7ffc,0x8000);(a.out/'unit.sfc').write_bytes(rom)
    lua=r'''local root=@ROOT@
local cases=@CASES@
local case,reads,done=nil,{},0
local function fail(s)local f=assert(io.open(root..'/error.txt','w'));f:write(s);f:close();emu.stop(1)end
emu.addMemoryCallback(function(a,v)
 case=cases[v+1];reads={};for i=0,4097 do emu.write(0x10000+case.dest+i,0xa5,emu.memType.snesWorkRam)end
 emu.write(0x104,case.stop,emu.memType.snesWorkRam)
end,emu.callbackType.write,0x102,0x102)
emu.addMemoryCallback(function(a,v)reads[a]=true;if a==0x400010 then return case.word%256 else return math.floor(case.word/256)end end,emu.callbackType.read,0x400010,0x400011)
emu.addMemoryCallback(function(a,v)
 if v~=0x5a or not reads[0x400010]or not reads[0x400011]then fail('encoded word ownership');return end
 local n=case.n;if case.stop==1 then n=2 elseif case.stop==2 then n=math.min(n,66)end
 for i=0,4097 do local want=i<n and(i%2==0 and case.word%256 or math.floor(case.word/256))or 0xa5
  if emu.read(0x10000+case.dest+i,emu.memType.snesWorkRam)~=want then fail('case '..done..' byte '..i);return end
 end
 done=done+1;if done==#cases then local f=assert(io.open(root..'/result.json','w'));f:write('{'..'"passed":true,"cases":'..done..'}');f:close();emu.stop(0)end
end,emu.callbackType.write,0x100,0x100)
'''.replace('@ROOT@',json.dumps(a.out.as_posix())).replace('@CASES@','{'+','.join('{n=%d,word=%d,dest=%d,stop=%d}'%(q['n'],q['word'],q['dest'],q['stop'])for q in cases)+'}')
    (a.out/'unit.lua').write_text(lua);env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']=str(a.dotnet)
    with(a.out/'mesen.log').open('wb')as log:r=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(a.out/'unit.lua'),str(a.out/'unit.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'],env=env,cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=70,creationflags=subprocess.CREATE_NO_WINDOW)
    assert r.returncode==0,(r.returncode,(a.out/'error.txt').read_text()if(a.out/'error.txt').exists()else'')
    result=json.loads((a.out/'result.json').read_text());assert result['passed'] and result['cases']==len(cases);print(json.dumps(result))
