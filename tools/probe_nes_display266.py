# SPDX-License-Identifier: MIT
"""Actual65816 H2 display view, bank/HDMA/VBlank and final RTL ACK.

Earlier output DMA is native C plus bus model. HDMA WRAM is seeded from the
independently checked metadata, not uploaded by this ROM. File RPC stretches
RTL time; CPU clocks are reported separately, never added as a frame bound.
"""
from pathlib import Path
import argparse,json,os,struct,subprocess,time,shutil
from nes_delta231 import BASE,ROOT,sha,once
from probe_nes_joint266 import prepare,run
from probe_nes_slice257 import TCL
from build_nes_trace_replay import Code


def rom(d):
 c=Code(0x8000);c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a,v in [(0x4200,0),(0x420c,0),(0x2100,0x80)]:c.store(a,v)
 for a in range(0x2123,0x212c):c.store(a,0)
 for a,v in [(0x2123,2),(0x2125,2),(0x2126,0),(0x2127,7),(0x2130,0),(0x2131,0),(0x2132,0xe0),(0x2133,0)]:c.store(a,v)
 c.emit(0xa2,0,0);c.label('next');c.absolute(0xad,0x6054);c.branch(0xf0,'next')
 c.absolute(0xbd,0x6070);c.absolute(0x9d,0x1000);c.emit(0xe8,0xe0,12,0);c.branch(0xd0,'next')
 c.label('active');c.absolute(0xad,0x4212);c.branch(0x30,'active')
 c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
 c.store(0x420c,0);c.absolute(0xad,0x1000);c.branch(0xd0,'bankb')
 for a,v in [(0x210b,0),(0x2101,1),(0x2107,0x31),(0x4313,0x65),(0x4322,0x61),(0x4323,0x71),(0x4333,0x72)]:c.store(a,v)
 c.jump('common');c.label('bankb')
 for a,v in [(0x210b,6),(0x2101,2),(0x2107,0x51),(0x4313,0xe5),(0x4322,0xb2),(0x4323,0xf1),(0x4333,0xf2)]:c.store(a,v)
 c.label('common')
 for a,v in [(0x2105,0),(0x2106,0),(0x212c,17),(0x212d,0),(0x212f,0)]:c.store(a,v)
 c.absolute(0xad,0x1001);c.emit(0xc9,0x18);c.branch(0xd0,'unclip');c.emit(0xa9,17);c.jump('window')
 c.label('unclip');c.emit(0xa9,0);c.label('window');c.absolute(0x8d,0x212e)
 for i in range(4):c.absolute(0xad,0x1008+i);c.absolute(0x8d,0x210d+i//2)
 for a,v in [(0x4310,3),(0x4311,0x0d),(0x4312,0),(0x4314,0x7f),(0x4320,4),(0x4321,5),(0x4324,0x7f),(0x4330,4),(0x4331,0x2c),(0x4332,3),(0x4334,0x7f)]:c.store(a,v)
 c.absolute(0xad,0x1002);c.branch(0xf0,'single');c.emit(0xa9,14);c.jump('enable')
 c.label('single');c.emit(0xa9,2);c.label('enable');c.absolute(0x8d,0x420c);c.store(0x2100,15)
 for i in range(4):c.absolute(0xad,0x6048+i);c.absolute(0x8d,0x604c+i)
 c.store(0x6058,0x5a)
 # Exercise one visible frame of the configured HDMA before reporting success.
 c.label('leave');c.absolute(0xad,0x4212);c.branch(0x30,'leave')
 c.label('visible');c.absolute(0xad,0x4212);c.branch(0x10,'visible')
 c.store(0x606f,0xa5);c.label('done');c.branch(0x80,'done');data=c.finish()
 r=bytearray([255])*32768;r[:len(data)]=data;r[0x7fc0:0x7fd5]=b'NES266 H2 DISPLAY    ';r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,p,0x8000)
 checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum);(d/'display.sfc').write_bytes(r)
 (d/'labels.json').write_text(json.dumps(c.labels,indent=2)+'\n');return len(data)


LUA=r'''
local seq=0;local trace=assert(io.open(OUT..'/cpu-bus.csv','w'));local pp=assert(io.open(OUT..'/ppu.csv','w'))
local function rpc(op,a,v)
 seq=seq+1;local f=assert(io.open(OUT..'/request.tmp','w'));f:write(string.format('%d %d %d',op,a,v or 0));f:close();assert(os.rename(OUT..'/request.tmp',OUT..'/req'..seq))
 local deadline=os.time()+90;local answer=nil
 repeat answer=io.open(OUT..'/rsp'..seq,'r');assert(os.time()<deadline,'RTL RPC timeout')until answer
 local value=tonumber(answer:read('*a'));answer:close();assert(value and value>=0)
 trace:write(string.format('%d,%d,%d,%d,%d\n',seq,op,a,op==0 and value or v,emu.getState().masterClock));trace:flush();return value
end
local function bytes(path)local f=assert(io.open(OUT..'/'..path,'r'));local t=f:read('*a');f:close();local r={};for b in t:gmatch('%x%x')do r[#r+1]=tonumber(b,16)end;return r end
local meta=bytes('meta'..FRAME..'.hex');assert(#meta==8570)
local desc=bytes('expected-display.hex');assert(#desc==12)
local bank=desc[1];local base=bank*0x8000
-- Fixture preload is explicit: native consumer already checked all8570 bytes.
for i=0,3417 do emu.write(0x10000+base+0x6500+i,meta[5153+i],emu.memType.snesWorkRam)end
local regs={};local scroll={};local hdma={0,0,0};local reads=0;local first=nil;local last=nil;local ack=nil;local ackscan=nil;local program=nil
emu.addMemoryCallback(function(a,v)
 local b=rpc(0,a,0)
 if a>=0x6070 then
  assert(a==0x6070+reads and b==desc[reads+1],'display view mismatch');reads=reads+1
  first=first or emu.getState().masterClock;last=emu.getState().masterClock
 end
 return b
end,emu.callbackType.read,0x6070,0x607b)
emu.addMemoryCallback(function(a,v)return rpc(0,a,0)end,emu.callbackType.read,0x6054)
emu.addMemoryCallback(function(a,v)return rpc(0,a,0)end,emu.callbackType.read,0x6048,0x604b)
local function record(a,v)
 local st=emu.getState();pp:write(string.format('%d,%d,%d,%d\n',a,v,st.masterClock,st['ppu.scanline']));pp:flush()
 if reads==12 and not ack then
  assert(st['ppu.scanline']>=225,'display write outside VBlank');program=program or st.masterClock
 end
 regs[a]=v;if a==0x210d or a==0x210e then scroll[#scroll+1]=v end
end
emu.addMemoryCallback(record,emu.callbackType.write,0x2100,0x212f)
emu.addMemoryCallback(record,emu.callbackType.write,0x4310,0x4334)
emu.addMemoryCallback(record,emu.callbackType.write,0x420c)
emu.addMemoryCallback(function(a,v)
 if a==0x6058 then
  local st=emu.getState();ack=st.masterClock;ackscan=st['ppu.scanline'];assert(reads==12 and ackscan>=225 and regs[0x2100]==15)
  assert(regs[0x210b]==(bank==0 and 0 or 6) and regs[0x2101]==bank+1 and regs[0x2107]==(bank==0 and 0x31 or 0x51))
  assert(regs[0x2105]==0 and regs[0x2106]==0 and regs[0x212c]==17 and regs[0x212d]==0 and regs[0x212f]==0)
  assert(regs[0x212e]==(desc[2]==0x18 and 17 or 0));assert(#scroll==4)
  assert(regs[0x2123]==2 and regs[0x2125]==2 and regs[0x2126]==0 and regs[0x2127]==7)
  for i=1,4 do assert(scroll[i]==desc[8+i])end
  assert(regs[0x4310]==3 and regs[0x4311]==13 and regs[0x4312]==0 and regs[0x4313]==0x65+bank*0x80 and regs[0x4314]==0x7f)
  assert(regs[0x4320]==4 and regs[0x4321]==5 and regs[0x4324]==0x7f and regs[0x4322]+256*regs[0x4323]==base+0x7161+bank*81)
  assert(regs[0x4330]==4 and regs[0x4331]==0x2c and regs[0x4334]==0x7f and regs[0x4332]+256*regs[0x4333]==base+0x7203)
  assert(regs[0x420c]==(desc[3]==0 and 2 or 14))
 end
 rpc(1,a,v)
end,emu.callbackType.write,0x604c,0x6058)
emu.addMemoryCallback(function(a,v)
 if not ack then return end
 local offset=a-0x7f0000-base;local k=nil
 if offset>=0x6500 and offset<0x6500+desc[4]+256*desc[5] then k=1
 elseif offset>=0x7161+bank*81 and offset<0x7161+bank*81+desc[6+bank] then k=2
 elseif offset>=0x7203 and offset<0x7203+desc[8] then k=3 end
 if k then
  local actual=emu.read(a-0x7e0000,emu.memType.snesWorkRam);assert(actual==meta[5153+offset-0x6500],'HDMA source mismatch');hdma[k]=hdma[k]+1
 end
end,emu.callbackType.read,0x7f0000,0x7fffff)
emu.addMemoryCallback(function(a,v)
 assert(v==0xa5 and ack and hdma[1]>0 and (desc[3]==0 or hdma[2]>0 and hdma[3]>0),'missing actual HDMA reads')
 rpc(2,0,0);local f=assert(io.open(OUT..'/cpu-result.json','w'))
 f:write(string.format('{"passed":true,"frame":%d,"bank":%d,"display_reads":%d,"first_read_master":%d,"last_read_master":%d,"program_start_master":%d,"final_ack_master":%d,"ack_scanline":%d,"HDMA_reads":[%d,%d,%d]}',FRAME,bank,reads,first,last,program,ack,ackscan,hdma[1],hdma[2],hdma[3]));f:close();trace:close();pp:close();emu.stop(0)
end,emu.callbackType.write,0x606f)
'''


def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--frame',type=int,choices=[905,906,907],required=True);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,a.frame);s=(d/'joint266_tb.sv').read_text(encoding='utf-8')
 script=ROOT/'tools/probe_nes_display266.py';shutil.copyfile(script,d/script.name);pins[script.relative_to(BASE).as_posix()]=sha(script)
 s=once(s,'    check_final265();','''    check_final265();
    if(RPC&&f==LAST)begin target_waiting=1;wait(flow_retired);target_waiting=0;end else begin''')
 s=once(s,"wr261(24'h006058,8'h5a);wait(!v_sealed);", "wr261(24'h006058,8'h5a);wait(!v_sealed);end")
 # LAST is a plusarg local integer named last_frame in the inherited harness.
 s=s.replace('RPC&&f==LAST',f'RPC&&f=={a.frame}')
 (d/'joint266_tb.sv').write_text(s,encoding='utf-8',newline='\n');body=rom(d)
 packets=bytes.fromhex((d/f'all{a.frame}.hex').read_text());lens=[int(x,16) for x in (d/f'all{a.frame}.lens').read_text().split()];at=0;ctx=None
 for n in lens[1:1+lens[0]]:
  q=packets[at:at+n];at+=n
  if q[0]==15:ctx=q[16:40]
 assert ctx is not None;h2=packets[16:48];view=bytes([h2[3],h2[19],h2[20],*h2[14:19],*ctx[12:16]])
 (d/'expected-display.hex').write_text(view.hex(' ')+'\n')
 tcl=TCL.replace('slice257_tb','joint266_tb').replace('finished257','finished261').replace('$address==24657 || $address==24658','$address==24660').replace('$n<1000','$n<5000')
 tcl=tcl.replace(' set f [open req$seq r];set cmd [read $f];close $f', ' if {[catch {open req$seq r} f]} {after 1;continue}\n set cmd [read $f];close $f')
 (d/'rpc.do').write_text(tcl,encoding='utf-8',newline='\n')
 (d/'capture.lua').write_text('local OUT='+json.dumps(d.as_posix())+'\nlocal FRAME='+str(a.frame)+'\n'+LUA,encoding='utf-8',newline='\n')
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer264.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint266_tb.sv'],d,'vlog')
 env=os.environ.copy();env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet';mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
 with (d/'vsim.log').open('wb') as vf,(d/'mesen.log').open('wb') as mf:
  sim=subprocess.Popen([str(a.questa_bin/'vsim.exe'),'-c','-voptargs=+acc','-sv_lib','producer263','work.joint266_tb','-gRPC=1',f'+LAST={a.frame}','-do','do rpc.do'],cwd=d,env=env,stdout=vf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);cpu=None
  try:
   deadline=time.monotonic()+240
   while not (d/'ready.txt').exists():
    assert sim.poll() is None,(d/'vsim.log').read_text(errors='replace')[-4000:];assert time.monotonic()<deadline;time.sleep(.05)
   cpu=subprocess.Popen([str(mesen),'--testRunner',str(d/'capture.lua'),str(d/'display.sfc'),'--timeout=600','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true','--debug.scriptWindow.scriptTimeout=90'],cwd=d,env=env,stdout=mf,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
   deadline=time.monotonic()+620
   while cpu.poll() is None:
    assert sim.poll() is None or sim.returncode==0,(d/'vsim.log').read_text(errors='replace')[-4000:];assert time.monotonic()<deadline;time.sleep(.05)
   assert cpu.returncode==0,(d/'mesen.log').read_text(errors='replace')[-4000:];assert sim.wait(timeout=10)==0
  finally:
   for proc in [cpu,sim]:
    if proc and proc.poll() is None:proc.kill();proc.wait()
 cpu_result=json.loads((d/'cpu-result.json').read_text());assert cpu_result['passed']
 r=dict(passed=True,scope=__doc__,cpu=cpu_result,rom_body_bytes=body,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,rom_sha256=sha(d/'display.sfc'),physical=False,full_ARM=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(cpu_result))


if __name__=='__main__':main()
