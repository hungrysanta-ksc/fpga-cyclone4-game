# SPDX-License-Identifier: MIT
"""Execute STOP cancellation on actual65816; endpoint status is a test model.

Packet DMA, zero DMA, validity publication, overlapping MVN, partial ACK and
short STOP pulses are covered. The separate RTL guard checks the same sticky
6001/6006 contract; this is not live CPU/FPGA co-simulation.
"""
from pathlib import Path
import argparse,json,os,shutil,subprocess
from nes_delta231 import sha
from probe_nes_ordinary269 import rom
from probe_nes_ordinary268 import guards

LUA=r'''
local orig=assert
function assert(v,m)if not v then local f=io.open(OUT..'/error.txt','a');f:write(tostring(m)..'\n');f:close();emu.stop(1)end;return orig(v,m)end
local f=assert(io.open(OUT..'/packets.hex','r'));local cases={}
for line in f:lines()do local p={};for b in line:gmatch('%x%x')do p[#p+1]=tonumber(b,16)end;cases[#cases+1]=p end;f:close()
local at=1;local reads=0;local pending=true;local held=0;local fired={};local stops=0;local clears=0;local accepted=0;local ignored=0;local zeros=0;local fills=0;local wram=0
local function flag(a)return emu.read(a,emu.memType.snesWorkRam)end
local function stop()
 if fired[at]then return end;fired[at]=true;pending=true;stops=stops+1;held=at==9 and 0 or 2
end
local function p(i)return cases[at][i+1]end
local function word(i)return p(i)+256*p(i+1)end
emu.addMemoryCallback(function(a,v)
 if a==0x6001 then
  if held>0 then held=held-1;return 0xc0 end
  return pending and 0x40 or 0
 elseif a==0x6000 then return pending and 0 or 1
 elseif a==0x6004 then return #cases[at]%256
 elseif a==0x6005 then return math.floor(#cases[at]/256) end
end,emu.callbackType.read,0x6000,0x6005)
emu.addMemoryCallback(function(a,v)
 assert(v==0xa5 and held==0,'invalidation handshake');assert(flag(0x50)==0 and flag(0x51)==0,'both flags cleared before acknowledgement')
 pending=false;clears=clears+1;reads=0;zeros=0;wram=0
end,emu.callbackType.write,0x6006)
emu.addMemoryCallback(function(a,v)
 local i=a-0x400000;assert(i==reads,'packet order');reads=reads+1
 if at==3 and reads==5 then stop()end
 -- The FPGA may withdraw its packet bus immediately. Remaining DMA bytes
 -- are deliberately garbage; the CPU must discard them before execution.
 return pending and 0xee or p(i)
end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function()fills=fills+1;zeros=0 end,emu.callbackType.exec,ZERO)
emu.addMemoryCallback(function()if at==10 then stop()end end,emu.callbackType.exec,EXECUTE)
emu.addMemoryCallback(function(a,v)if pending then return 0x5a end end,emu.callbackType.read,ZERO_SOURCE)
emu.addMemoryCallback(function(a,v)
 if a==0x2180 and at==5 then zeros=zeros+1;if zeros==500 then stop()end end
end,emu.callbackType.write,0x2180)
emu.addMemoryCallback(function()
 if at==6 then stop()end
 if at==9 then stop()end
end,emu.callbackType.exec,COPIED)
-- The generic MVN writes this poisoned byte before its copied/ACK checks.
emu.addMemoryCallback(function(a,v)
 if at==7 then wram=wram+1;if wram==1 then stop()end end
end,emu.callbackType.write,0x7f6515,0x7f6518)
emu.addMemoryCallback(function(a,v)
 if at==8 and a==0x6014 then stop()end
 if a~=0x601c then return end
 if pending then ignored=ignored+1;return end
 assert(reads==#cases[at] and v==0xa5,'complete command ACK')
 local n=p(0)==2 and word(12) or word(14);local bank=(word(4)-1)%2
 local offset=0x16500+bank*0x8000+word(10)
 for i=0,n-1 do assert(emu.read(offset+i,emu.memType.snesWorkRam)==p(16+i%word(12)),'WRAM after retry')end
 if p(0)==5 and word(10)==21 then assert(flag(0x50+bank)==1,'valid after complete zero DMA')end
 accepted=accepted+1;at=at+1;reads=0;zeros=0;wram=0
 if at>#cases then
  assert(stops==7 and clears==8 and ignored==1,'all STOP stages reached '..stops..'/'..clears..'/'..ignored)
  local r=assert(io.open(OUT..'/result.json','w'));r:write(string.format('{"passed":true,"STOP_cases":%d,"clears":%d,"accepted":%d,"stale_ACK_ignored":%d,"fills":%d}',stops,clears,accepted,ignored,fills));r:close();emu.stop(0)
 end
end,emu.callbackType.write,0x6010,0x601c)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 zero,bank1=guards()[0][0],guards()[0][2]
 def make(seed,op=2,offset=21,bank=0):
  b=bytearray(zero);b[0]=op;b[4:6]=(bank+1).to_bytes(2,'little');b[10:12]=offset.to_bytes(2,'little');b[12:14]=len(seed).to_bytes(2,'little');b[14:16]=len(seed).to_bytes(2,'little');return bytes(b[:16])+seed
 # STOP at case5 cleared both flags; bank1 case6 must publish a newly filled
 # bank before its copied callback, rather than exercising only a reuse hit.
 cases=[zero,bank1,zero,make(b'\x99'),zero,bank1,make(b'\x91\x92\x93\x94'),zero,zero,bank1]
 (d/'packets.hex').write_text('\n'.join(x.hex(' ') for x in cases)+'\n');size,labels=rom(d,'reuse')
 lua='local OUT='+json.dumps(d.as_posix())+'\nlocal ZERO='+str(labels['zero_dma'])+'\nlocal COPIED='+str(labels['copied'])+'\nlocal EXECUTE='+str(labels['execute'])+'\nlocal ZERO_SOURCE='+str(labels['zero_source'])+'\n'+LUA
 (d/'capture.lua').write_text(lua,encoding='utf-8',newline='\n');shutil.copyfile(__file__,d/Path(__file__).name)
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 with (d/'mesen.log').open('wb') as f:r=subprocess.run(['C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe','--testRunner',str(d/'capture.lua'),str(d/'ordinary.sfc'),'--timeout=90','--doNotSaveSettings','--enableStdout','--debug.scriptWindow.allowIoOsAccess=true'],cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0 and not (d/'error.txt').exists(),(d/'error.txt').read_text() if (d/'error.txt').exists() else (d/'mesen.log').read_text()[-1500:]
 result=json.loads((d/'result.json').read_text());result.update(scope=__doc__,ROM_sha256=sha(d/'ordinary.sfc'),script_sha256=sha(Path(__file__)),rom_body_bytes=size,live_RTL=False)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
