# SPDX-License-Identifier: MIT
"""Live C203 RUN + RTL207 direct/epoch/lease/READ16 + actual65816 client195.
Metadata is an archived real203 exporter trace, capture/loader/RAM status and
sink E0/E1 queue are fixtures. No game CPU, whole-board/physical/FPS claim.
File transactions couple independently scheduled simulators, not their clocks.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,time
from nes_board204 import ROOT,BASE,sha,replace
from test_nes_bulk194_snes import script

RPC_LUA=r'''
local function guarded208(fn)
 return function(...)
  local ok,result=pcall(fn,...)
  if not ok then local f=assert(io.open(OUT_DIR..'/lua-error.txt','w'));f:write(tostring(result));f:close();emu.stop(1);return end
  return result
 end
end
local oldMemory208=emu.addMemoryCallback
emu.addMemoryCallback=function(fn,...)return oldMemory208(guarded208(fn),...)end
local oldEvent208=emu.addEventCallback
emu.addEventCallback=function(fn,...)return oldEvent208(guarded208(fn),...)end
local rpcseq=1
local actualDescriptor=nil
local function rpc208(op,address,n,data,want)
 local root=string.format(OUT_DIR..'/S-%06d',rpcseq);rpcseq=rpcseq+1
 local f=assert(io.open(root..'.tmp','wb'))
 f:write(string.char(op,address&255,(address>>8)&255,(address>>16)&255,n&255,(n>>8)&255,0,0));if data then f:write(data)end;f:close()
 assert(os.rename(root..'.tmp',root..'.req'))
 local began=os.time();repeat f=io.open(root..'.rsp','rb');assert(os.time()-began<120,'RTL response timeout')until f
 local s=f:read('*a');f:close();assert(#s==want,'RTL response length');return s
end
'''

def lua():
 s=script(BASE/'probes/nes-copy186/evidence/coupled03/inherit')
 s=RPC_LUA+s
 s=replace(s,'packet=nil;tile=nil;consumed=false;reads=0;', 'packet=nil;tile=nil;actualDescriptor=nil;consumed=false;reads=0;')
 start=s.index('local function descriptor()');end=s.index('emu.addMemoryCallback(function(a,v)return descriptor()',start)
 s=s[:start]+'''local function descriptor()
 if not actualDescriptor then actualDescriptor=rpc208(2,0x6040,12,nil,12)end
 return actualDescriptor
end
'''+s[end:]
 s=replace(s,"local i=a-0x400800;assert(i<#tile,'bulk overread');assert(i==reads,'nonsequential DMA')",'''local i=a-0x400800;assert(i<#tile,'bulk overread');assert(i==reads,'nonsequential DMA')
 if i==0 then local actual=rpc208(2,0x400800,#tile,nil,#tile);assert(actual==tile,'RTL pixels differ from186 C reference');tile=actual end''')
 s=replace(s,'consumed=true;retires=retires+1;',"rpc208(3,0x604c,5,string.char(table.unpack(tokenWrites))..string.char(0xa5),0);consumed=true;retires=retires+1;")
 s=replace(s,' if not packet and (rejected or ordinal>TOTAL) then'," local done=io.open(OUT_DIR..'/producer-done.txt','r')\n if done then done:close();")
 s=replace(s,"assert(commits==(MODE=='normal' and 7 or 1));assert(maximumDma==2048);assert(retires>0)","assert(commits==(MODE=='normal' and 3 or 1));assert(maximumDma>0 and retires>0)")
 s=replace(s,"  if MODE=='normal' then assert(chunks>0 and held>0)end", "  if MODE=='partial' then local now=emu.getScreenBuffer();for i=1,#now do assert(now[i]==previousScreen[i],'partial cancel changed displayed frame')end end")
 s=s.replace('if st.frameCount>4000','if st.frameCount>100000')
 return s

def prepare(out):
 out.mkdir(parents=True,exist_ok=False);pins={}
 def read(p):pins[p.relative_to(BASE).as_posix()]=sha(p);return p.read_text(encoding='utf8')
 src=BASE/'probes/nes-metadata203/test04'
 names=['reference203.h','reference203.c','nes_native_runtime165.h','nes_native_runtime165.c','nes_native165.h','nes_native165.c',
 'nes_trace166.h','nes_trace166.c','nes_plan191.h','nes_plan191.c','nes_plan_service200.h','nes_plan_service200.c',
 'nes_native_sink165.h','nes_native_sink165.c','nes_sink_trace168.h','nes_sink_trace168.c','nes_sink_window184.h','nes_sink_window184.c',
 'nes_native_video165.h','nes_sink_bulk195.h']
 for n in names:
  f=src/n;read(f);shutil.copyfile(f,out/n)
 # Some production includes are generated alongside the selected C snapshot.
 for f in [*src.glob('*.inc'),*src.glob('*.h')]:read(f);shutil.copyfile(f,out/f.name)
 s=read(src/'host203.c');start=s.index('static void decode(')
 s=s[:start]+read(ROOT/'tests/nes-functional/join208_host.inc')
 # The expected tile bytes are186 reference output; actual DMA bytes come from RTL.
 anchor='  memcpy(queue[qsent%4],tx+1,size);'
 extra='''  if(tx[1]==7){unsigned len=u16(tx+15),offset=u16(tx+11);assert(tx[2]<2&&offset+len<=sizes[tx[2]]);
   char name[80];sprintf(name,"tile-%04u.bin",qsent+1);FILE*f=fopen(name,"wb");assert(f&&fwrite((tx[2]?obj:bg)+offset,1,len,f)==len);fclose(f);}
'''
 s=replace(s,anchor,extra+anchor);(out/'host.c').write_text(s,encoding='utf8',newline='\n')
 for n in ['scene1.wire']:
  read(src/n);shutil.copyfile(src/n,out/n)
 board=BASE/'probes/nes-board207/source02';p=json.loads((board/'preparation207.json').read_bytes())
 rtl=['nes_direct206.sv','nes_source_epoch207.sv','nes_capture_lease201.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv',
 'nes_plan_spi200.sv','nes_plan_batch206.sv','nes_tile_bulk206.sv','nes_bulk_control194.sv','nes_bulk_aperture188.sv',
 'nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
 for n in rtl:
  assert sha(board/n)==p['sources'][n];read(board/n);shutil.copyfile(board/n,out/n)
 for n in ['join208_tb.sv','join208_rpc.c']:
  f=ROOT/'tests/nes-functional'/n;read(f);shutil.copyfile(f,out/n)
 f=BASE/'probes/nes-board206/test01/direct/spi200_bus.svh';s=read(f)
 s=replace(s,'SPI_HALF=62.5,SPI_SETUP=200,SPI_HOLD=200,SPI_GAP=2000','SPI_HALF=190.476190476,SPI_SETUP=2000,SPI_HOLD=2000,SPI_GAP=4000')
 (out/f.name).write_text(s,encoding='utf8',newline='\n')
 client=BASE/'probes/nes-bulk195/coupled03/candidate/client/sink165.sfc';pins[client.relative_to(BASE).as_posix()]=sha(client)
 shutil.copyfile(client,out/'sink165.sfc')
 read(ROOT/'tools/test_nes_bulk194_snes.py');read(BASE/'probes/nes-copy186/evidence/coupled03/inherit/capture.lua')
 return pins,rtl

def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--modes',nargs='+',default=['normal','partial']);a=p.parse_args();a.out=a.out.resolve()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';pins,rtl=prepare(a.out)
 (a.out/'runner-source.py').write_bytes(Path(__file__).read_bytes())
 (a.out/'input-pins.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf8',newline='\n')
 gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe')
 env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
 def run(args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run(list(map(str,args)),cwd=a.out,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
 c=['host.c','reference203.c','nes_native_runtime165.c','nes_native165.c','nes_trace166.c','nes_plan191.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c']
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-Wno-unused-function','-Wno-unused-variable','-Wno-misleading-indentation','-O2',*c,'-o','host.exe'],'gcc-host')
 run([gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-shared','join208_rpc.c','-o','join208_rpc.dll'],'gcc-rpc')
 run([a.questa_bin/'vlib.exe','work'],'vlib');run([a.questa_bin/'vlog.exe','-sv',*rtl,'join208_tb.sv'],'vlog')
 run([a.questa_bin/'vmap.exe','-c'],'vmap-create');run([a.questa_bin/'vmap.exe','work',(a.out/'work').as_posix()],'vmap-work')
 cases=[]
 for mode in a.modes:
  d=a.out/mode;d.mkdir();shutil.copyfile(a.out/'scene1.wire',d/'scene1.wire')
  for n in ['modelsim.ini','join208_rpc.dll']:shutil.copyfile(a.out/n,d/n)
  (d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\nlocal MODE='+json.dumps(mode)+'\n'+lua(),encoding='utf8',newline='\n')
  cmds=[[str(a.questa_bin/'vsim.exe'),'-c','-sv_lib','join208_rpc','work.join208_tb','-do','onerror {quit -code 1}; run -all; quit -f'],
   [str(a.out/'host.exe'),mode],
   [str(mesen),'--testRunner',str(d/'capture.lua'),str(a.out/'sink165.sfc'),'--timeout=300','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true']]
  children=[];logs=[]
  try:
   for name,cmd in zip(['rtl','host','mesen'],cmds):
    log=(d/(name+'.log')).open('wb');logs.append(log);children.append(subprocess.Popen(cmd,cwd=d,env=env,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
   began=time.monotonic()
   while any(c.poll() is None for c in children):
    if any(c.poll() not in (None,0) for c in children) or time.monotonic()-began>320:break
    if '** Fatal:' in (d/'rtl.log').read_text(errors='replace'):break
    time.sleep(.1)
   codes=[c.poll() for c in children]
  finally:
   for child in children:
    if child.poll() is None:child.kill();child.wait()
   for log in logs:log.close()
  texts={n:(d/(n+'.log')).read_text(errors='replace') for n in ['rtl','host','mesen']}
  assert codes==[0,0,0] and 'PASS JOIN208 RTL' in texts['rtl'] and 'PASS JOIN208 frames=' in texts['host'],{n:t[-4000:] for n,t in texts.items()}
  result=json.loads((d/'consumer-result.json').read_bytes());assert result['passed'];result['mode']=mode
  if mode=='normal':
   assert (d/'frame-1.rgb').read_bytes()==(d/'frame-2.rgb').read_bytes()==(d/'frame-3.rgb').read_bytes()
   result['same_scene_pixels']=3*256*239
  result['rtl']=re.search(r'PASS JOIN208 RTL[^\r\n]*',texts['rtl'])[0];result['host']=re.search(r'PASS JOIN208 frames=[^\r\n]*',texts['host'])[0]
  cases.append(result);print(json.dumps(result),flush=True)
 pins['repository-nes-milestone/tools/test_nes_join208.py']=sha(Path(__file__))
 result=dict(passed=True,cases=cases,source_pins=pins,compiler_sha256=sha(gcc),mesen_sha256=sha(mesen),scope=__doc__,actual_c_rtl_snes_transaction_join=True,full_board=False,physical=False,actual_scroll_measured=False,new_fit=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
if __name__=='__main__':main()
