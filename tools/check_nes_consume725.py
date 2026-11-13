"""Native725 parser-owned/idle DMA arbitration, real beam, STOP and retirement.

Fixture supplies already-validated metadata at the production bulk entry.
Full header/CRC validation is covered by the independent full replay.
"""
import argparse,json,os,subprocess
from pathlib import Path
from build_nes_trace_replay import Code
from nes_raw506 import sha

LUA=r'''
local ROOT=@ROOT@;local CASE=@CASE@;local LINE=@LINE@;local H=@H@;local LENGTH=@LENGTH@
local ram=emu.memType.snesWorkRam;local vr=emu.memType.snesVideoRam
local started=false;local dma=0;local count=0;local stopping=CASE=='stop';local done=false;local failed=false;local first,last=nil,nil
local entryClock=0;local latchClock=0;local latchH=0;local latchLine=0;local mdmaClock=0
local function rd(a)return emu.read(a,ram)end
local function word(a)return rd(a)+256*rd(a+1)end
local function put(a,v)emu.write(a,v&255,ram);emu.write(a+1,(v>>8)&255,ram)end
local f=assert(io.open(ROOT..'/body.bin','rb'));local body=f:read('*a');f:close()
local function cb(fn,...)
 return emu.addMemoryCallback(function(...)
  if failed or done then return end
  local ok,v=pcall(fn,...);if ok then return v end
  failed=true
  local f=assert(io.open(ROOT..'/error.txt','w'));f:write(tostring(v));f:close();emu.stop(1)
 end,...)
end
local function finish(stop)
 if done then return end;done=true
 local expected=CASE=='owned' or CASE=='late_stop' or CASE=='idle_empty'
 local want=expected and (LINE>=249 and math.min(LENGTH,1152) or LENGTH) or 0
 assert(count==want,'DMA bytes '..count..'/'..want..' latch '..latchLine..':'..latchH..' entry '..entryClock..' latchClock '..latchClock)
 assert(dma==(want>0 and 1 or 0),'DMA count')
 assert(word(0x1228)==1,'owner not restored')
 assert(stop==(CASE=='stop' or CASE=='late_stop'),'STOP decision')
 assert(word(0x1220)==11 and word(0x1248)==9,'ACK changed')
 assert(word(0x1032)==0,'display bank changed')
 if want>0 then
  assert(first.frame==last.frame and first.line>=225 and last.line<262,'VBlank overrun')
  if want==LENGTH then assert(word(0x1250)==word(0x1252),'whole retire')
  else assert(word(0x4000)==0xd000+want and word(0x4002)==0xa000+want and word(0x4004)==LENGTH-want,'partial retire')end
 end
 for i=0,LENGTH-1 do
  assert(emu.read(0xa000+i,vr)==(i<want and (i*37+9)%256 or 165),'VRAM content '..i)
  assert(emu.read(0x6000+i,vr)==90,'active bank mutated')
 end
 for i=1,#body do assert(rd(0x1fff+i)==body:byte(i),'production body changed')end
 local f=assert(io.open(ROOT..'/result.json','w'));f:write(string.format('{"passed":true,"DMA_B":%d,"STOP":%s,"line":%d,"last_line":%d,"entry_clock":%d,"latch_clock":%d,"latch_h":%d,"latch_line":%d,"mdma_clock":%d}',count,tostring(stop),first and first.line or -1,last and last.line or -1,entryClock,latchClock,latchH,latchLine,mdmaClock));f:close();emu.stop(0)
end
cb(function()
 local st=emu.getState()
 -- The fixture copy may itself finish late in frame0. Align only after a
 -- complete frame, otherwise a requested early252 h can already be past.
 if not started and st.frameCount>=2 and st['ppu.scanline']==LINE and st['memoryManager.hClock']>=H then
  started=true;entryClock=st.masterClock
  for i=0x1000,0x14ff do emu.write(i,0,ram)end
  put(0x1024,CASE=='cold' and 0 or 1);put(0x1020,0x8000);put(0x1034,CASE=='active' and 0 or 1)
  put(0x1228,1);put(0x1220,11);put(0x1226,956);put(0x1248,9)
  put(0x1200,0x107);put(0x1202,11);put(0x1208,956);put(0x120c,32);put(0x120e,32)
  put(0x1250,8);put(0x1252,0);put(0x4000,0xd000);put(0x4002,0xa000);put(0x4004,LENGTH)
  if CASE=='tile' then put(0x4000,0xc000);put(0x4002,0x8000)end
  for i=0,LENGTH-1 do emu.write(0x1d000+i,(i*37+9)%256,ram);emu.write(0xa000+i,165,vr);emu.write(0x6000+i,90,vr)end
  put(0x3901,@ENTRY@&65535)
 end
end,emu.callbackType.exec,0x7e3900)
cb(function()return stopping and 128 or 0 end,emu.callbackType.read,0x6001)
cb(function()return CASE=='idle_empty' and 0 or 1 end,emu.callbackType.read,0x6000)
cb(function()return 1 end,emu.callbackType.read,0x4218,0x4219)
cb(function()local st=emu.getState();latchClock=st.masterClock;latchH=st['memoryManager.hClock'];latchLine=st['ppu.scanline']end,emu.callbackType.read,0x2137)
cb(function(a,v)
 assert(started and v==1,'unexpected DMA')
 dma=dma+1;mdmaClock=emu.getState().masterClock
 if CASE=='late_stop' then stopping=true end
end,emu.callbackType.write,0x420b)
cb(function()
 local st=emu.getState();local stamp={line=st['ppu.scanline'],frame=st.frameCount,clock=st.masterClock}
 first=first or stamp;last=stamp;count=count+1
end,emu.callbackType.write,0x2118,0x2119)
cb(function(a,v)error(string.format('unexpected ACK/receipt %x=%x PC=%x state=%x started=%s',a,v,emu.getState()['cpu.pc'],word(0x1228),tostring(started)))end,emu.callbackType.write,0x6010,0x601c)
cb(function()finish(false)end,emu.callbackType.exec,@DATA@)
cb(function()finish(true)end,emu.callbackType.exec,@STOP@)
emu.addEventCallback(function()if emu.getState().frameCount>4 then error('timeout')end end,emu.eventType.endFrame)
'''

def run(a):
    a.out=a.out.resolve();assert str(a.out).isascii();a.out.mkdir(parents=True,exist_ok=False)
    body=(a.client/'body.bin').read_bytes();labels=json.loads((a.client/'labels.json').read_text())
    after=json.loads((a.client/'build.json').read_text()).get('after_payload',False)
    c=Code(0x7e3900);c.jump('loop');c.labels['loop']=0x7e3900
    c.label('idle725');c.absolute(0x20,labels['prefix523']&65535);c.jump('data');c.labels['data']=labels['data']
    c.label('post_fixture725');c.emit(0xe2,0x20);c.labels['owned_bulk725']=labels['owned_bulk725'];c.jump('owned_bulk725')
    blob=body+bytes(0x1900-len(body))+c.finish()
    b=Code(0x8000);b.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b)
    b.emit(0xe2,0x20,0xa9,0,0x48,0xab,0xc2,0x30,0xa9);b.word(len(blob)-1);b.emit(0xa2,0,0x81,0xa0,0,0x20,0x54,0x7e,0,0xe2,0x20,0xa9,0,0x48,0xab)
    b.store(0x2100,15);b.emit(0xc2,0x30);b.long(0x5c,0x7e3900)
    rom=bytearray((a.client/'sink165.sfc').read_bytes());rom[:0x7fc0]=bytes([255])*0x7fc0;rom[:len(b.finish())]=b.finish();rom[0x100:0x100+len(blob)]=blob
    rom[0x7ffc:0x7ffe]=(0x8000).to_bytes(2,'little');(a.out/'fixture.sfc').write_bytes(rom)
    cases=[('owned',225,100,384),('owned',248,200,1536),('owned',251,200,1536),('owned',200,100,384),('owned',253,100,384)]
    cases += [(n,230,100,384) for n in ('stop','late_stop','active','cold','idle_head','idle_empty')]
    # Append after the calibrated late cases, preserving their indices.
    rows=[]
    for i,(name,line,h,size) in enumerate(cases):
        d=a.out/f'{i:02}-{name}';d.mkdir();(d/'body.bin').write_bytes(body)
        script=LUA
        # Outside the allowed beam window there is no speculative DMA.
        case=name if line in range(225,253) else 'outside'
        target=c.labels['idle725'] if name.startswith('idle') else c.labels['post_fixture725'] if after else labels['owned_bulk725']
        end=labels['data'] if name.startswith('idle') else labels.get('owned_return725',labels['data'])
        for k,v in dict(ROOT=json.dumps(d.as_posix()),CASE=json.dumps(case),LINE=line,H=h,LENGTH=size,ENTRY=target,DATA=end,STOP=labels['stop_packet']).items():script=script.replace('@'+k+'@',str(v))
        (d/'test.lua').write_text(script,encoding='utf8')
        with (d/'mesen.log').open('wb') as log:
            r=subprocess.run([str(a.mesen.resolve()),'--testRunner',str(d/'test.lua'),str(a.out/'fixture.sfc'),'--timeout=15','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],stdout=log,stderr=subprocess.STDOUT,timeout=30,env=dict(os.environ,DOTNET_ROOT='C:/works/dotnet',DOTNET_ROOT_X64='C:/works/dotnet'),creationflags=subprocess.CREATE_NO_WINDOW)
        assert r.returncode==0,(d,(d/'error.txt').read_text() if (d/'error.txt').exists() else 'see log')
        result=json.loads((d/'result.json').read_text())
        rows.append(dict(case=name,entry_line=line,**result))
        if i==2:
            for event in ('latch_clock','mdma_clock'):
                delta=result[event]-result['entry_clock'];at,hpos=divmod(252*1364+1120-delta,1364)
                cases.append(('owned',at,hpos,1536))
                if event=='latch_clock':cases.append(('late_stop',at,hpos,1536))
        if i==11:assert result['latch_line']==252 and result['latch_h']>=1000
        if i==12:assert result['STOP'] and result['DMA_B']==1152 and result['last_line']<262
        if i==13:
            h=result['latch_h']+result['mdma_clock']-result['latch_clock']
            assert result['latch_line']+h//1364==252 and h%1364>=1000
            if after:cases.append(('tile',230,100,128))
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,cases=rows,client=sha(a.client/'sink165.sfc'),scope=__doc__),indent=2)+'\n')
    print('PASS725 native owner/idle/beam/STOP',len(rows))

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
