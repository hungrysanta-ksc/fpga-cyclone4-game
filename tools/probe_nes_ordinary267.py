# SPDX-License-Identifier: MIT
"""Execute ordinary literal/repeat commands and real CGRAM/OAM DMA on65816.

Immutable264 packets are supplied at the bus callback. No target WRAM is seeded.
Forced blank isolates command service cost; active-display/VBlank scheduling,
tile/map DMA, H2 validation and final display ACK are not part of this kernel.
"""
from pathlib import Path
import argparse,json,os,struct,subprocess
from nes_delta231 import BASE,ROOT,sha
from build_nes_trace_replay import Code
from probe_nes_joint261 import packets

def rom(d):
 c=Code(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 c.store(0x4200,0);c.store(0x420c,0);c.store(0x2100,0x80)
 def lda(a):c.absolute(0xad,a)
 def sta(a):c.absolute(0x8d,a)
 def cond(op,label):c.emit(op^0x20,3);c.jump(label)
 c.label('next');lda(0x6000);c.branch(0xf0,'next');c.emit(0xc2,0x20);lda(0x6004);sta(0x20);sta(0x4305);c.emit(0xe2,0x20)
 for a,v in [(0x2181,0),(0x2182,0x11),(0x2183,0),(0x4300,0),(0x4301,0x80),(0x4302,0),(0x4303,0),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
 c.label('execute');c.emit(0xc2,0x20);lda(0x1104);c.emit(0x3a,0x29,1,0,0xeb,0x0a,0x0a,0x0a,0x0a,0x0a,0x0a,0x0a);sta(0x40)
 c.emit(0xe2,0x20);lda(0x1101);c.emit(0xc9,3);c.branch(0xf0,'cgbase');c.emit(0xc9,4);c.branch(0xf0,'oambase')
 c.emit(0xc2,0x20,0xa9,0,0x65);c.jump('base')
 c.label('cgbase');c.emit(0xc2,0x20,0xa9,0,0x60);c.jump('base')
 c.label('oambase');c.emit(0xc2,0x20,0xa9,0,0x62)
 c.label('base');c.emit(0x18,0x65,0x40);c.absolute(0x6d,0x110a);sta(0x40);c.emit(0xe2,0x20);c.store(0x42,0x7f)
 lda(0x1100);c.emit(0xc9,2);c.branch(0xd0,'repeat');c.emit(0xc2,0x20);lda(0x110c);sta(0x24);c.jump('pattern')
 c.label('repeat');c.emit(0xc2,0x20);lda(0x110e);sta(0x24)
 c.label('pattern');lda(0x110c);sta(0x26);c.emit(0x3a,0xa2,0x10,0x11);c.absolute(0xac,0x40)
 c.emit(0x54,0x7f,0x7e,0x4b,0xab) # MVN literal/pattern seed; restore DBR0.
 lda(0x24);c.emit(0x38,0xe5,0x26);c.branch(0xf0,'copied');c.emit(0x3a);sta(0x28)
 lda(0x40);c.emit(0x18,0x65,0x26,0xa8);c.absolute(0xae,0x40);lda(0x28)
 c.emit(0x54,0x7f,0x7f,0x4b,0xab) # Forward overlapping MVN repeats the validated seed.
 c.label('copied');c.emit(0xe2,0x20)
 c.label('dma_setup');lda(0x1101);c.emit(0xc9,5);cond(0xf0,'ack')
 c.emit(0xc2,0x20);lda(0x40);sta(0x4302);lda(0x24);sta(0x4305);lda(0x110a);c.emit(0x4a);sta(0x28);c.emit(0xe2,0x20);c.store(0x4304,0x7f)
 lda(0x1101);c.emit(0xc9,3);c.branch(0xd0,'oamdma')
 lda(0x28);sta(0x2121);c.store(0x4300,2);c.store(0x4301,0x22);c.jump('dma')
 c.label('oamdma');lda(0x28);sta(0x2102);lda(0x29);sta(0x2103);c.store(0x4300,0);c.store(0x4301,4)
 c.label('dma');c.store(0x420b,1)
 c.label('ack');c.store(0x6010,0);lda(0x1100);sta(0x6011);c.emit(0xa2,2,0)
 c.label('ackloop');c.absolute(0xbd,0x1100);c.absolute(0x9d,0x6010);c.emit(0xe8,0xe0,10,0);c.branch(0xd0,'ackloop')
 c.store(0x601a,0x65);c.store(0x601b,0x9a);c.store(0x601c,0xa5);c.jump('next');body=c.finish()
 r=bytearray([255])*32768;r[:len(body)]=body;r[0x7fc0:0x7fd5]=b'NES267 ORDINARY DMA   ';r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,p,0x8000)
 checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum);(d/'ordinary.sfc').write_bytes(r)
 return len(body),c.labels

LUA=r'''
local f=assert(io.open(OUT..'/packets.hex','r'));local cases={}
for line in f:lines()do local p={};for b in line:gmatch('%x%x')do p[#p+1]=tonumber(b,16)end;cases[#cases+1]=p end;f:close()
local at=1;local reads=0;local first=nil;local lastread=nil;local execute=nil;local setup=nil;local dma={};local ack={};local total=0
local bus=assert(io.open(OUT..'/bus.csv','w'));bus:write('case,write,address,value,clock\n')
local function event(w,a,v)bus:write(string.format('%d,%d,%d,%d,%d\n',at,w,a,v,emu.getState().masterClock));bus:flush();return v end
local log=assert(io.open(OUT..'/timing.csv','w'));log:write('case,serial,sequence,op,section,length,output_bytes,read_clocks,service_clocks,dma_setup_service_clocks,dma_bytes,total_clocks\n')
local function p(i)return cases[at][i+1]end
local function word(i)return p(i)+256*p(i+1)end
local function clock()return emu.getState().masterClock end
emu.addMemoryCallback(function(a,v)if a==0x6000 then return event(0,a,1) elseif a==0x6004 then return event(0,a,#cases[at]%256) else return event(0,a,math.floor(#cases[at]/256))end end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)local i=a-0x400000;assert(i==reads,'packet read order');first=first or clock();lastread=clock();reads=reads+1;return event(0,a,p(i))end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function()execute=clock()end,emu.callbackType.exec,EXECUTE)
emu.addMemoryCallback(function()setup=clock()end,emu.callbackType.exec,SETUP)
emu.addMemoryCallback(function(a,v)dma[#dma+1]=v end,emu.callbackType.write,0x2122)
emu.addMemoryCallback(function(a,v)dma[#dma+1]=v end,emu.callbackType.write,0x2104)
emu.addMemoryCallback(function(a,v)
 event(1,a,v)
 if a~=0x601c then ack[a-0x6010]=v;return end
 assert(v==0xa5 and reads==#cases[at] and ack[0]==0 and ack[10]==0x65 and ack[11]==0x9a)
 assert(ack[1]==p(0),'ACK opcode');for i=2,9 do assert(ack[i]==p(i),'ACK identity')end
 local count=p(0)==2 and word(12) or word(14);local bank=(word(4)-1)%2
 local offset=(p(1)==3 and 0x6000 or p(1)==4 and 0x6200 or 0x6500)+bank*0x8000+word(10)
 assert(#dma==(p(1)==5 and 0 or count),'DMA count')
 for i=0,count-1 do local expected=p(16+i%word(12));assert(emu.read(0x10000+offset+i,emu.memType.snesWorkRam)==expected,'WRAM command byte')
  if p(1)~=5 then assert(dma[i+1]==expected,'DMA source/destination data')end
 end
 log:write(string.format('%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d,%d\n',at,word(4),word(2),p(0),p(1),#cases[at],count,lastread-first,clock()-lastread,clock()-setup,#dma,clock()-first));log:flush();total=total+count
 at=at+1;reads=0;first=nil;lastread=nil;execute=nil;setup=nil;dma={};ack={}
 if at>#cases then local r=assert(io.open(OUT..'/cpu-result.json','w'));r:write(string.format('{"passed":true,"commands":%d,"output_bytes":%d}',#cases,total));r:close();log:close();bus:close();emu.stop(0)end
end,emu.callbackType.write,0x6010,0x601c)
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 cases=[];pins={}
 for f in range(905,976):
  path=BASE/f'probes/nes-joint264/arm01/frame{f}.packets';pins[path.relative_to(BASE).as_posix()]=sha(path)
  cases += [p for p in packets(path) if p[0] in (2,4,5,8)]
 (d/'packets.hex').write_text('\n'.join(p.hex(' ') for p in cases)+'\n');body,labels=rom(d)
 lua='local OUT='+json.dumps(d.as_posix())+'\nlocal EXECUTE='+str(labels['execute'])+'\nlocal SETUP='+str(labels['dma_setup'])+'\n'+LUA
 # Record callback assertions as a hard failure, even if Mesen keeps running.
 lua=lua.replace('local f=assert',"local original_assert=assert\nfunction assert(v,msg)if not v then local e=io.open(OUT..'/error.txt','a');e:write(tostring(msg)..'\\n'..debug.traceback()..'\\n');e:close()end;return original_assert(v,msg)end\nlocal f=assert",1)
 (d/'capture.lua').write_text(lua,encoding='utf-8',newline='\n');(d/'labels.json').write_text(json.dumps(labels,indent=2)+'\n')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (d/'mesen.log').open('wb') as log:
  r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'ordinary.sfc'),'--timeout=300','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=330,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/'mesen.log').read_text(errors='replace')[-2500:]
 assert not (d/'error.txt').exists(),(d/'error.txt').read_text()
 cpu=json.loads((d/'cpu-result.json').read_text());assert cpu['passed'] and cpu['commands']==len(cases)
 result=dict(passed=True,scope=__doc__,CPU=cpu,rom_body_bytes=body,ROM_sha256=sha(d/'ordinary.sfc'),input_hashes=pins,
  script_sha256=sha(Path(__file__)),physical=False,live_RTL=False,active_display=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(cpu))

if __name__=='__main__':main()
