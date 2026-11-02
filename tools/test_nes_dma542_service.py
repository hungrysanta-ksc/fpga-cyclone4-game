# SPDX-License-Identifier: MIT
"""Run emitted raw service against busy/latched joypad and STOP hardware reads."""
import argparse,json,os,struct,subprocess
from pathlib import Path
from nes_sinkpack181 import ShortCode
from nes_native_local165 import call
from nes_dma542 import raw_emitter

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('out','mesen'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
    cases=[dict(latched=l,busy=b,stop=s) for l in (0,1) for b in (0,1) for s in (0,1)]
    c=ShortCode(0x8000)
    c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,255,31,0x9a,0xa9,0,0,0x5b,0x4b,0xab)
    for i,q in enumerate(cases):
        c.emit(0xe2,0x20);c.store(0x100,i);c.store(0x1238,q['latched'])
        c.emit(0xc2,0x20);c.absolute(0x9c,0x1236);call(c,'raw_service489');c.emit(0x08,0xe2,0x20,0x68);c.absolute(0x8d,0x101)
    c.emit(0x80,0xfe)
    raw_emitter()(c)
    # Exact production service source, including STOP latch and autojoy publication.
    text=(Path(__file__).parent/'build_nes_sink165.py').read_text()
    start=text.index(" c.label('service');")
    end=text.index(' for values,pos',start)
    def lda(addr):c.absolute(0xad,addr)
    def sta(addr):c.absolute(0x8d,addr)
    def cond(op,label):c.emit(op^0x20,3);c.jump(label)
    exec(compile('\n'.join(line[1:] for line in text[start:end].splitlines()),'production-service','exec'),dict(c=c,lda=lda,sta=sta,cond=cond))
    image=bytearray([255])*32768;code=c.finish();image[:len(code)]=code
    image[0x7fc0:0x7fd5]=b'DMA542 SERVICE'.ljust(21,b' ');image[0x7fd5:0x7fd9]=bytes([0x20,0,5,0])
    struct.pack_into('<H',image,0x7ffc,0x8000);(a.out/'unit.sfc').write_bytes(image)
    lua=r'''local root=@ROOT@
local cases=@CASES@
local q,done,reads,writes=nil,0,0,0
local function check(ok,why)if not ok then local f=assert(io.open(root..'/error.txt','w'));f:write(why);f:close();emu.stop(1);error(why)end end
emu.addMemoryCallback(function(_,v)q=cases[v+1];reads=0;writes=0 end,emu.callbackType.write,0x100)
emu.addMemoryCallback(function()return q.stop*128 end,emu.callbackType.read,0x6001)
emu.addMemoryCallback(function()return 128+q.busy end,emu.callbackType.read,0x4212)
emu.addMemoryCallback(function(addr)reads=reads+1;return addr==0x4218 and 0x53 or 0xa6 end,emu.callbackType.read,0x4218,0x4219)
emu.addMemoryCallback(function(addr,v)writes=writes+1;check(v==(addr==0x6002 and 0x53 or 0xa6),'pad value')end,emu.callbackType.write,0x6002,0x6003)
emu.addMemoryCallback(function(_,v)
 local capture=q.latched==0 and q.busy==0
 check((v&1)==1-q.stop and (v&0x20)==0,'carry or accumulator width')
 check(emu.read(0x1236,emu.memType.snesWorkRam)==q.stop,'STOP latch')
 check(reads==(capture and 2 or 0) and writes==reads,'pad ownership')
 check(emu.read(0x1238,emu.memType.snesWorkRam)==((q.latched==1 or capture) and 1 or 0),'pad latch')
 done=done+1;if done==#cases then local f=assert(io.open(root..'/result.json','w'));f:write('{"passed":true,"cases":'..done..'}');f:close();emu.stop(0)end
end,emu.callbackType.write,0x101)
'''.replace('@ROOT@',json.dumps(a.out.as_posix())).replace('@CASES@','{'+','.join('{latched=%d,busy=%d,stop=%d}'%(q['latched'],q['busy'],q['stop']) for q in cases)+'}')
    (a.out/'unit.lua').write_text(lua)
    with (a.out/'mesen.log').open('wb') as log:
        subprocess.run([str(a.mesen.resolve()),'--testRunner',str(a.out/'unit.lua'),str(a.out/'unit.sfc'),'--timeout=60','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=a.out,stdout=log,stderr=subprocess.STDOUT,timeout=70,creationflags=subprocess.CREATE_NO_WINDOW,check=True,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'))
    result=json.loads((a.out/'result.json').read_text());assert result['passed'] and result['cases']==len(cases)
    print(result)
