"""Execute the exact long-play service bytes on a native65816; modeled bus/pad."""
import argparse,json,os,subprocess
from pathlib import Path
from build_nes_trace_replay import Code
from nes_raw506 import sha

LUA=r'''
local ROOT=@ROOT@
local function memory(cb,...)
 return emu.addMemoryCallback(function(...)
  local ok,v=pcall(cb,...)
  if not ok then local f=assert(io.open(ROOT..'/error.txt','w'));f:write(tostring(v));f:close();emu.stop(1)end
  return v
 end,...)
end
local MASK=@MASK@
local MODE=@MODE@
local samples=0;local pads={};local stage=-1;local acks=0;local dma=0;local loops=0
local function finish()
 local expected=MASK&0x3030==0x3030 and MODE=='valid'
 assert((stage==126)==expected,'exit decision')
 assert(acks==0 and dma==0,'exit manufactured ACK/DMA')
 if MODE=='valid' or MODE=='stop' then assert(pads[1]==(MASK&255) and pads[2]==(MASK>>8),'pad forwarding '..table.concat(pads,',')..' samples='..samples)
 else assert(#pads==0,'invalid sample forwarded')end
 local f=assert(io.open(ROOT..'/result.json','w'))
 f:write(string.format('{"passed":true,"stage":%d,"samples":%d,"pad_bytes":%d,"ACK":%d,"DMA":%d}',stage,samples,#pads,acks,dma));f:close();emu.stop(0)
end
emu.addMemoryCallback(function()return MODE=='stop' and 128 or 0 end,emu.callbackType.read,0x6001)
emu.addMemoryCallback(function()
 samples=samples+1
 if MODE=='blank' then return 128 end
 if MODE=='busy' or (MODE=='second_busy' and samples>1) then return 1 end
 return 0
end,emu.callbackType.read,0x4212)
emu.addMemoryCallback(function()return MASK&255 end,emu.callbackType.read,0x4218)
emu.addMemoryCallback(function()return MASK>>8 end,emu.callbackType.read,0x4219)
emu.addMemoryCallback(function(a,v)pads[#pads+1]=v end,emu.callbackType.write,0x6002,0x6003)
emu.addMemoryCallback(function(a,v)stage=v;if v==90 then finish()end end,emu.callbackType.write,0x7000)
emu.addMemoryCallback(function()acks=acks+1 end,emu.callbackType.write,0x601c)
emu.addMemoryCallback(function()dma=dma+1 end,emu.callbackType.write,0x420b)
emu.addMemoryCallback(function()loops=loops+1;if loops==1000 then finish()end end,emu.callbackType.exec,@WAIT@)
'''

def run(a):
    assert str(a.out.resolve()).isascii(),'Mesen Lua test output must use an ASCII path'
    a.out.mkdir(parents=True,exist_ok=False)
    body=(a.client/'body.bin').read_bytes();labels=json.loads((a.client/'labels.json').read_text())
    # Fixture enters production WRAM body directly; packed reset loader is
    # not executed in this test. Byte identity is asserted before every run.
    c=Code(0x7e3900);c.emit(0xc2,0x30);c.absolute(0x9c,0x1236);c.absolute(0x9c,0x1238);c.absolute(0x20,labels['service']&65535);c.emit(0xe2,0x20);c.store(0x7000,90);c.emit(0x80,0xfe)
    blob=body+bytes(0x1900-len(body))+c.finish()
    b=Code(0x8000);b.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b)
    b.emit(0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x30,0xa9);b.word(len(blob)-1);b.emit(0xa2,0,0x81,0xa0,0,0x20,0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab);b.long(0x5c,0x7e3900)
    rom=bytearray((a.client/'sink165.sfc').read_bytes());rom[:0x7fc0]=bytes([255])*0x7fc0;rom[:len(b.finish())]=b.finish();rom[0x100:0x100+len(blob)]=blob
    rom[0x7ffc:0x7ffe]=(0x8000).to_bytes(2,'little');(a.out/'fixture.sfc').write_bytes(rom)
    cases=[('none',0,'valid'),('ordinary',0xcf0f,'valid'),('combo',0x3030,'valid'),('extra',0xffff,'valid')]
    cases += [(f'missing{bit}',0x3030^(1<<bit),'valid') for bit in (4,5,12,13)]
    cases += [(mode,0x3030,mode) for mode in ('blank','busy','second_busy','stop')]
    results=[]
    for name,mask,mode in cases:
        folder=(a.out/name).resolve();folder.mkdir();script=LUA
        for k,v in dict(ROOT=json.dumps(folder.as_posix()),MASK=mask,MODE=json.dumps(mode),WAIT=labels['exit_wait693']).items():script=script.replace('@'+k+'@',str(v))
        script+='\nemu.addMemoryCallback(function()\n'
        script+=f' for i=0,{len(body)-1} do assert(emu.read(0x2000+i,emu.memType.snesWorkRam)==string.byte(BODY,i+1),"body mismatch")end\n'
        script+='end,emu.callbackType.exec,0x7e3900)\n'
        script=script.replace('emu.addMemoryCallback(function','memory(function')
        script=script.replace('return memory(function','return emu.addMemoryCallback(function',1)
        # Lua reads immutable original bytes only to verify the copied fixture.
        (folder/'body.bin').write_bytes(body)
        script='local f=assert(io.open('+json.dumps((folder/'body.bin').as_posix())+',"rb"));local BODY=f:read("*a");f:close()\n'+script
        (folder/'test.lua').write_text(script,encoding='utf8')
        with (folder/'mesen.log').open('wb') as log:
            r=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(folder/'test.lua'),str((a.out/'fixture.sfc').resolve()),'--timeout=5','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=folder,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),stdout=log,stderr=subprocess.STDOUT,timeout=20,creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(name,(folder/'mesen.log').read_text(errors='replace'),(folder/'error.txt').read_text() if (folder/'error.txt').exists() else '')
        results.append(dict(case=name,mask=mask,**json.loads((folder/'result.json').read_text())))
        print('CPU693',name,'PASS',flush=True)
    r=dict(passed=True,scope=__doc__,client=sha(a.client/'sink165.sfc'),body=sha(a.client/'body.bin'),cases=results)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
