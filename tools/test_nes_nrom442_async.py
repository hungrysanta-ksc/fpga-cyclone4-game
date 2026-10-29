# SPDX-License-Identifier: MIT
"""Nonblocking transaction adapter with delayed FPGA ACK."""
import argparse,json,os,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--board',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
r=json.loads((a.rtl/'result.json').read_text());assert r['passed'] and r['fixture_sha256']==sha(a.rom) and r['blocks_sha256']==sha(a.rtl/'nrom429-blocks.txt')
prod=BASE/'probes/nes-repeat227/arm01/src';prior=BASE/'probes/nes-repeat227/snes04';cand=prior/'candidate'
for n in ('nes_native_sink165.c','nes_native165.c','nes_planner211.c','nes_resident211.c'):assert sha(cand/n)==sha(prod/n)
for q in cand.iterdir():
 if q.is_file() and q.suffix in ('.c','.h','.inc'):shutil.copyfile(q,d/q.name)
for f in prod.glob('*.h'):shutil.copyfile(f,d/f.name)
for n in ('nes_palette165.inc','nes_plan_service200.c','nes_native_runtime165.c','nes_sink_window184.c','nes_budget210.c'):shutil.copyfile(prod/n,d/n)
for n in ('nes_direct206.sv','nes_source_epoch207.sv','nes_capture_lease201.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv','nes_plan_spi200.sv','nes_plan_batch206.sv','nes_tile_bulk206.sv','nes_bulk_control194.sv','nes_bulk_aperture188.sv','nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv','nes_sink_bridge165.sv','nes_sink_spi165.sv','nes_sink_bus165.sv'):shutil.copyfile(a.board/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom437/runtime.c',d/'host.c');shutil.copyfile(ROOT/'tests/nes-nrom441/join_tb.sv',d/'join208_tb.sv');shutil.copyfile(ROOT/'tests/nes-functional/join208_rpc.c',d/'join208_rpc.c');shutil.copyfile(a.rom,d/'fixture.nes');shutil.copyfile(a.rtl/'nrom429-blocks.txt',d/'blocks.txt');shutil.copyfile(a.board/'sink-program.hex',d/'sink-program.hex')
s=(ROOT/'tests/nes-functional/spi200_bus.svh').read_text().replace('SPI_HALF=62.5,SPI_SETUP=200,SPI_HOLD=200,SPI_GAP=2000','SPI_HALF=190.476190476,SPI_SETUP=2000,SPI_HOLD=2000,SPI_GAP=4000');(d/'spi200_bus.svh').write_text(s)
lua=(prior/'candidate-normal/capture.lua').read_text(encoding='utf-8').split('\n',1)[1]
setup=r'''local rpcseq=1
local function rpc208(op,address,n,data,want)
 local root=string.format(OUT_DIR..'/S-%06d',rpcseq);rpcseq=rpcseq+1
 local f=assert(io.open(root..'.tmp','wb'));f:write(string.char(op,address&255,(address>>8)&255,(address>>16)&255,n&255,(n>>8)&255,0,0));if data then f:write(data)end;f:close();assert(os.rename(root..'.tmp',root..'.req'))
 local began=os.time();repeat f=io.open(root..'.rsp','rb');assert(os.time()-began<120,'RTL response timeout')until f
 local s=f:read('*a');f:close();assert(#s==want,'RTL response length');return s
end
'''
lua=lua.replace('local tile=nil;local consumed=false;','local tile=nil;local actualDescriptor=nil;local consumed=false;',1).replace('packet=nil;tile=nil;consumed=false;reads=0;','packet=nil;tile=nil;actualDescriptor=nil;consumed=false;reads=0;',1)
start=lua.index('local function descriptor()');end=lua.index('emu.addMemoryCallback(function(a,v)return descriptor()',start)
lua=lua[:start]+'''local function descriptor()
 if not actualDescriptor then actualDescriptor=rpc208(2,0x6040,12,nil,12)end
 return actualDescriptor
end
'''+lua[end:]
needle="local i=a-0x400800;assert(i<#tile,'bulk overread');assert(i==reads,'nonsequential DMA')";assert lua.count(needle)==1;lua=lua.replace(needle,needle+"\n if i==0 then local actual=rpc208(2,0x400800,#tile,nil,#tile);assert(actual==tile,'RTL tile differs');tile=actual end",1)
needle='consumed=true;retires=retires+1;';assert lua.count(needle)==1;lua=lua.replace(needle,"rpc208(3,0x604c,5,string.char(table.unpack(tokenWrites))..string.char(0xa5),0);"+needle,1)
start=lua.index("local function publish(bytes)");end=lua.index("emu.addMemoryCallback(function(a,v)",start)
lua=lua[:start]+r"""local publishing=false
local inflight=nil
local candidate=nil
local function begin_async(op,address,n,data,phase)
 assert(not inflight,'overlapping async request')
 local root=string.format(OUT_DIR..'/S-%06d',rpcseq);rpcseq=rpcseq+1
 local f=assert(io.open(root..'.tmp','wb'));f:write(string.char(op,address&255,(address>>8)&255,(address>>16)&255,n&255,(n>>8)&255,0,0));if data then f:write(data)end;f:close();assert(os.rename(root..'.tmp',root..'.req'))
 inflight={path=root..'.rsp',phase=phase,began=os.time()}
end
local function publish(bytes)
 packet=nil;pendingAck=nil;publishing=true;begin_async(3,0x6010,13,bytes..string.char(0xa5),{kind='ack',bytes=bytes})
end
"""+lua[end:]
needle="if a==0x6000 then return packet and not pendingAck and 1 or 0 end"
assert lua.count(needle)==1;lua=lua.replace(needle,"if a==0x6000 then return packet and not pendingAck and not publishing and 1 or 0 end",1)
start=lua.index(" if not packet and not rejected then local f=io.open");end=lua.index(" local done=io.open(OUT_DIR..'/producer-done.txt'",start)
lua=lua[:start]+r""" if not packet and not rejected and not publishing and not inflight then
  local f=io.open(string.format(OUT_DIR..'/req-%04d.bin',ordinal),'rb')
  if f then candidate=f:read('*a');f:close();publishing=true;begin_async(2,0x6000,6,nil,{kind='status'}) end
 end
"""+lua[end:]
needle="emu.addEventCallback(function()\n local st=emu.getState()"
assert lua.count(needle)==1
lua=lua.replace(needle,r"""emu.addEventCallback(function()
 if inflight then
  local f=io.open(inflight.path,'rb')
  if f then
   local value=f:read('*a');f:close();local phase=inflight.phase;inflight=nil
   if phase.kind=='status' then
    assert(#value==6 and value:byte(1)==1 and value:byte(2)==0 and value:byte(5)+256*value:byte(6)==#candidate,'RTL queue status')
    begin_async(2,0x400000,#candidate,nil,{kind='packet'})
   elseif phase.kind=='packet' then
    assert(value==candidate,'RTL queue packet mismatch');packet=value;candidate=nil
    if pb(0)==7 then local tf=assert(io.open(string.format(OUT_DIR..'/tile-%04d.bin',ordinal),'rb'));tile=tf:read('*a');tf:close()end
    publishing=false
   elseif phase.kind=='ack' then
    assert(#value==0,'ACK response length');local name=string.format(OUT_DIR..'/ack-%04d',ordinal)
    local af=assert(io.open(name..'.tmp','wb'));af:write(phase.bytes);af:close();assert(os.rename(name..'.tmp',name..'.bin'))
    packet=nil;tile=nil;actualDescriptor=nil;consumed=false;reads=0;tokenWrites={};ordinal=ordinal+1;pendingAck=nil;publishing=false
   else error('unknown async phase')end
  else assert(os.time()-inflight.began<120,'async RTL response timeout')end
 end
 local st=emu.getState()""",1)
needle="local done=io.open(OUT_DIR..'/producer-done.txt','r')"
assert lua.count(needle)==1;lua=lua.replace(needle,"local done=(not publishing and not inflight and not packet and not pendingAck) and io.open(OUT_DIR..'/producer-done.txt','r')",1)
lua=lua.replace('if st.frameCount>4000','if st.frameCount>100000');(d/'capture.lua').write_text('local OUT_DIR='+json.dumps(d.as_posix())+'\n'+setup+lua,encoding='utf-8')
exe=prior/'client/sink165.sfc';gcc=Path('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe');questa=Path('C:/altera_standard/25.1std/questa_fse/win64');mesen=Path('C:/Users/mohallo/AppData/Local/Temp/nes-coupled165-mesen/Mesen.exe');env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','');env['DOTNET_ROOT']=env['DOTNET_ROOT_X64']='C:/works/dotnet'
rtl=['nes_direct206.sv','nes_source_epoch207.sv','nes_capture_lease201.sv','nes_source_tile192.sv','nes_chr_cache192.sv','nes_tile205.sv','nes_plan_spi200.sv','nes_plan_batch206.sv','nes_tile_bulk206.sv','nes_bulk_control194.sv','nes_bulk_aperture188.sv','nes_native_arbiter165.sv','nes_rom_physical.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv','nes_sink_bridge165.sv','nes_sink_spi165.sv','nes_sink_bus165.sv']
def run(name,cmd):
 with(d/(name+'.log')).open('wb') as f:q=subprocess.run(list(map(str,cmd)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=90,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-4000:]
run('host-build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','host.c','nes_native165.c','nes_trace166.c','nes_planner211.c','nes_resident211.c','nes_native_sink165.c','nes_sink_trace168.c','nes_sink_window184.c','nes_native_runtime165.c','nes_budget210.c','nes_plan_service200.c','-o','host.exe'])
run('rpc-build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','join208_rpc.c','-o','join208_rpc.dll']);run('vlib',[questa/'vlib.exe','work']);run('vlog',[questa/'vlog.exe','-sv',*rtl,'join208_tb.sv'])
logs=[];children=[]
try:
 commands=[('rtl',[questa/'vsim.exe','-L','altera_mf_ver','-c','-sv_lib','join208_rpc','work.nrom437_tb','-do','onerror {quit -code 1};run -all;quit -f']),('host',[d/'host.exe','blocks.txt','fixture.nes']),('mesen',[mesen,'--testRunner',d/'capture.lua',exe,'--timeout=240','--doNotSaveSettings','--enableStdout','--snes.disableFrameSkipping=true','--debug.scriptWindow.allowIoOsAccess=true'])]
 for name,cmd in commands:
  f=(d/(name+'.log')).open('wb');logs.append(f);children.append(subprocess.Popen(list(map(str,cmd)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
 for child in (children[1],children[2],children[0]):child.wait(timeout=240)
finally:
 for child in children:
  if child.poll() is None:child.kill();child.wait()
 for f in logs:f.close()
assert all(x.returncode==0 for x in children),[(d/(n+'.log')).read_text(errors='replace')[-3500:] for n in ('rtl','host','mesen')]
assert not (d/'lua-error.txt').exists(),(d/'lua-error.txt').read_text() if (d/'lua-error.txt').exists() else ''
consumer=json.loads((d/'consumer-result.json').read_text());assert consumer['passed'] and consumer['commits']==1 and consumer['retired_chunks']>=1
host=(d/'host.log').read_text();rtl=(d/'rtl.log').read_text(errors='replace');assert 'PASS NROM437 actual queue RUN frames=1' in host and 'PASS NROM437 RTL frames=1 retires=1' in rtl and 'Errors: 0' in rtl
pixels=(d/'frame-1.rgb').read_bytes();assert len(pixels)==256*239*3
for y in range(16,224):
 for x in range(16,240):
  i=(y*256+x)*3;assert (pixels[i:i+3]==bytes(3))==((x+y)%2==0),(x,y)
result={'passed':True,'rom_sha256':sha(a.rom),'geometry_sha256':sha(a.rtl/'nrom429-blocks.txt'),'client_sha256':sha(exe),'frame_sha256':sha(d/'frame-1.rgb'),'consumer':consumer,'host':host.strip(),'scope':'nonblocking callback adapter with deliberately delayed FPGA ACK, recorded geometry and modeled source; no physical timing'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
