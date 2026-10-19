# SPDX-License-Identifier: MIT
"""Actual65816 DMA for every cold-frame map batch, true core seal and display ACK.

File RPC stretches host bus time. CPU master clocks and RTL time are separate.
Non-map streams and H2/context/manifest producers remain the pinned255 fixtures.
"""
from pathlib import Path
import argparse,json,os,struct,subprocess,time
from probe_nes_joint261 import prepare,run
from probe_nes_slice257 import TCL
from build_nes_trace_replay import Code
from nes_delta231 import sha


def rom(d):
 c=Code(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a,v in [(0x4200,0),(0x420c,0),(0x2100,0x80),(0x2115,0x80)]:c.store(a,v)
 c.label('next');c.absolute(0xad,0x6040);c.branch(0xd0,'dma')
 c.absolute(0xad,0x6052);c.branch(0xf0,'next');c.jump('display')
 c.label('dma');c.emit(0xc2,0x20);c.absolute(0xad,0x6044);c.emit(0x18,0x69,0,0x40);c.absolute(0x8d,0x2116)
 c.absolute(0xad,0x6042);c.absolute(0x8d,0x4305);c.emit(0xe2,0x20)
 for a,v in [(0x4300,1),(0x4301,0x18),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
 def token():
  for i in range(4):c.absolute(0xad,0x6048+i);c.absolute(0x8d,0x604c+i)
 token();c.store(0x6050,0xa5)
 # Next DMA availability (or sealed) is durable;6051 may pulse between
 # batch ranges and is not a CPU polling contract.
 c.jump('next')
 c.label('display');c.label('active');c.absolute(0xad,0x4212);c.branch(0x30,'active')
 c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
 c.store(0x2107,0x40);c.store(0x2100,15);token();c.store(0x6058,0x5a)
 c.label('done');c.branch(0x80,'done');data=c.finish()
 r=bytearray([255])*32768;r[:len(data)]=data;r[0x7fc0:0x7fd5]=b'NES261 BATCH DMA TEST '.ljust(21,b' ')[:21];r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,p,0x8000)
 checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum);(d/'joint.sfc').write_bytes(r);return len(data)

LUA=r'''
local seq=0
local trace=assert(io.open(OUT..'/cpu-bus.csv','w'))
local function rpc(op,a,v)
 seq=seq+1
 local f=assert(io.open(OUT..'/request.tmp','w'));f:write(string.format('%d %d %d',op,a,v or 0));f:close();assert(os.rename(OUT..'/request.tmp',OUT..'/req'..seq))
 local deadline=os.time()+90;local answer=nil
 repeat answer=io.open(OUT..'/rsp'..seq,'r');assert(os.time()<deadline,'RTL RPC timeout')until answer
 local raw=answer:read('*a');answer:close();local value=op==3 and raw:gsub('%s','') or tonumber(raw);assert(value and (op==3 or value>=0))
 trace:write(string.format('%d,%d,%d,%d,%d\n',seq,op,a,op==0 and value or v,emu.getState().masterClock));trace:flush();return value
end
local bytes=0;local burst={};local chunks=0;local dma_start=nil;local dma_end=nil;local bg=false;local visible=false
-- Execute all actual RTL bus reads of one immutable chunk in one file RPC.
-- The65816 still reads every byte and only then writes consume. Timelines
-- remain independent; this is not physical bus latency measurement.
emu.addMemoryCallback(function(a,v)
 if a==0x400800 then
  local n=rpc(0,0x6042,0)+256*rpc(0,0x6043,0);assert(n>0 and n<=64)
  local data=rpc(3,a,n);assert(#data==n*2);burst={}
  for b in data:gmatch('%x%x')do burst[#burst+1]=tonumber(b,16) end
 end
 local i=a-0x400800+1;assert(burst[i]);bytes=bytes+1
 trace:write(string.format('0,0,%d,%d,%d\n',a,burst[i],emu.getState().masterClock));trace:flush()
 return burst[i]
end,emu.callbackType.read,0x400800,0x400fff)
emu.addMemoryCallback(function(a,v)return rpc(0,a,0)end,emu.callbackType.read,0x6040,0x6052)
emu.addMemoryCallback(function(a,v)
 if a==0x6050 then chunks=chunks+1;dma_end=emu.getState().masterClock end
 if a==0x6058 then
  assert(bg and visible and bytes==4096 and chunks==64,'incomplete display')
  local f=assert(io.open(OUT..'/map905.expected','r'));local text=f:read('*a');f:close();local i=0
  for b in text:gmatch('%x%x')do assert(emu.read(0x8000+i,emu.memType.snesVideoRam)==tonumber(b,16),'VRAM mismatch '..i);i=i+1 end
  assert(i==4096)
 end
 rpc(1,a,v)
 if a==0x6058 then
  rpc(2,0,0)
  local f=assert(io.open(OUT..'/cpu-result.json','w'))
  f:write(string.format('{"passed":true,"dma_bytes":%d,"ranges":%d,"dma_start_master":%d,"last_consume_master":%d,"final_ack_master":%d}',bytes,chunks,dma_start,dma_end,emu.getState().masterClock));f:close();trace:close();emu.stop(0)
 end
end,emu.callbackType.write,0x604c,0x6058)
emu.addMemoryCallback(function(a,v)if not dma_start then dma_start=emu.getState().masterClock end end,emu.callbackType.write,0x420b)
emu.addMemoryCallback(function(a,v)if v==0x40 then bg=true end end,emu.callbackType.write,0x2107)
emu.addMemoryCallback(function(a,v)if v==15 then visible=true end end,emu.callbackType.write,0x2100)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii()
 src,pins,stats=prepare(d,905);body=rom(d)
 tcl=TCL.replace('slice257_tb','joint261_tb').replace('finished257','finished261').replace('$address==24657 || $address==24658','$address==24640 || $address==24657 || $address==24658')
 tcl=tcl.replace(' set f [open req$seq r];set cmd [read $f];close $f', ' if {[catch {open req$seq r} f]} {after 1;continue}\n set cmd [read $f];close $f')
 tcl=tcl.replace(' force -deposit $root/bus_address 10#$address', r'''
 if {$op==3} {
  if {$address!=4196352 || $value<1 || $value>64} {error "invalid DMA burst"}
  set reply "";set fd [open rtl-dma.csv a]
  for {set i 0} {$i<$value} {incr i} {
   set ba [expr {$address+$i}]
   force -deposit $root/bus_address 10#$ba
   force -deposit $root/bus_read 0
   run 200 ns
   if {[examine -radix unsigned $root/bus_valid]!=1} {error "invalid DMA read"}
   set byte [examine -radix unsigned $root/bus_out]
   append reply [format %02x $byte]
   puts $fd "$seq,$ba,$byte"
   force -deposit $root/bus_read 1
   run 200 ns
  }
  close $fd
  set f [open rsp$seq.tmp w];puts $f $reply;close $f
  file rename rsp$seq.tmp rsp$seq
  incr seq;continue
 }
 force -deposit $root/bus_address 10#$address''')
 (d/'rpc.do').write_text(tcl,encoding='utf-8',newline='\n');(d/'capture.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\n'+LUA,encoding='utf-8',newline='\n')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint261_tb.sv'],d,'vlog')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet';mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
 with (d/'vsim.log').open('wb') as vf,(d/'mesen.log').open('wb') as mf:
  sim=subprocess.Popen([str(a.questa_bin/'vsim.exe'),'-c','-voptargs=+acc','work.joint261_tb','-gRPC=1','+LAST=905','-do','do rpc.do'],cwd=d,env=env,stdout=vf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);cpu=None
  try:
   deadline=time.monotonic()+120
   while not (d/'ready.txt').exists():
    assert sim.poll() is None,(d/'vsim.log').read_text(errors='replace')[-4000:];assert time.monotonic()<deadline;time.sleep(.05)
   cpu=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(d/'joint.sfc'),'--timeout=600','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   deadline=time.monotonic()+620
   while cpu.poll() is None:
    assert sim.poll() is None or sim.returncode==0,(d/'vsim.log').read_text(errors='replace')[-4000:];assert time.monotonic()<deadline;time.sleep(.05)
   assert cpu.returncode==0,(d/'mesen.log').read_text(errors='replace')[-4000:];assert sim.wait(timeout=10)==0
  finally:
   for proc in [cpu,sim]:
    if proc and proc.poll() is None:proc.kill();proc.wait()
 cpu_result=json.loads((d/'cpu-result.json').read_text());assert cpu_result['passed']
 r=dict(passed=True,scope=__doc__,cpu=cpu_result,rom_body_bytes=body,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,rom_sha256=sha(d/'joint.sfc'),physical=False,full_ARM=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(cpu_result))

if __name__=='__main__':main()
