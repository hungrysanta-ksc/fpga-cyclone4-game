# SPDX-License-Identifier: MIT
"""Actual257 source/receipt plus258 ordinary ACK, tile/map staging, Mesen DMA.

One cold frame: ordinary header, one16B tile from the existing C fixture, one
64B map. The other ranges and H2 remain fixtures. RPC is logical, not physical.
"""
import struct,sys,json,shutil
from pathlib import Path
import probe_nes_slice257 as old
from nes_mux258 import sources
from nes_delta231 import once
from build_nes_trace_replay import Code


def tb():
 s=old.testbench()
 s=once(s,'nes_range257 flow(','''reg tv258=0,ev258=0;wire tr258,er258;reg [7:0] td258;reg [4:0] ti258;
 nes_mux258 flow(.tile_valid(tv258),.tile_ready(tr258),.tile_data(td258),.tile_index(ti258),.tile_length(6'd16),.tile_kind(2'd0),.tile_slot(10'd0),.tile_generation(display_gen),
 .end_valid(ev258),.end_ready(er258),.end_generation(display_gen),.ordinary_ready(),.next_token(),''')
 s=once(s,'  for(k=0;k<100;k++)packet257[k]=0;', '''
  fd=$fopen("tile.hex","w");
  for(k=0;k<16;k++)begin
   wait(tr258);@(negedge clk);tv258=1;td258=stream_bytes[k];ti258=k;$fwrite(fd,"%02x\\n",stream_bytes[k]);
   @(negedge clk);tv258=0;
  end
  $fclose(fd);wait(er258);@(negedge clk);ev258=1;@(negedge clk);ev258=0;
  for(k=0;k<100;k++)packet257[k]=0;
  packet257[0]=2;packet257[4]=serial[7:0];packet257[8]=display_gen[7:0];packet257[9]=display_gen[15:8];
  @(negedge host_clk);os=0;crc257=c16(16'hffff,8'he1);output_byte(8'he1);
  for(k=0;k<16;k++)begin output_byte(packet257[k]);crc257=c16(crc257,packet257[k]);end
  output_byte(crc257[15:8]);output_byte(crc257[7:0]);#190;os=1;repeat(8)@(negedge host_clk);
  for(k=0;k<100;k++)packet257[k]=0;''')
 s=once(s,'packet257[0]=9;','packet257[0]=9;packet257[2]=1;')
 s=once(s,"packet257[16]=1;packet257[18]=8'h57;packet257[19]=2;",'packet257[16]=2;')
 s=once(s,'  wait(staged);repeat(32)@(negedge host_clk);','  target_waiting=1;wait(staged&&flow.owner==flow.MAP);repeat(32)@(negedge host_clk);')
 s=once(s,'flow.queue.retired!=1||flow.queue.accepted!=1','flow.queue.retired!=2||flow.queue.accepted!=2')
 s=once(s,' integer eventfd,nes_ticks=0;', '''
 always @(posedge flow.failed or posedge flow.tfault)if(!reset)
  $display("FLOW258 diagnostic state=%0d owner=%0d failed=%0d tfault=%0d sf=%0d hf=%0d pe=%0d ce=%0d core=%0d bus=%h/%h write=%0d reads=%0d/%0d token=%h written=%h mask=%h tgen=%0d igen=%0d",flow.state,flow.owner,flow.failed,flow.tfault,flow.tiles.source_failed,flow.tiles.host_failed,flow.pe,flow.ce,source_fault,flow.ap,flow.dp,flow.write_end,flow.read_count,flow.chunk_length,flow.chunk_token,flow.written,flow.mask,flow.tgen,flow.identity[47:32]);
 integer eventfd,nes_ticks=0;''')
 if SEPARATE:s=once(s,'nes_mux258 flow(','nes_mux258 #(.SHARED(0)) flow(')
 return s


def rom(out):
 c=Code(0x8000)
 c.emit(0x78,0x18,0xfb,0xc2,0x30,0xa2,0xff,0x1f,0x9a,0xa9,0,0,0x5b,0xe2,0x20)
 for a,v in [(0x4200,0),(0x420c,0),(0x2100,0x80),(0x2115,0x80)]:c.store(a,v)
 c.label('ordinary');c.absolute(0xad,0x6000);c.branch(0xf0,'ordinary')
 for i in range(16):c.emit(0xaf,i,0,0x40);c.absolute(0x8d,0x1000+i)
 c.store(0x6010,0);c.store(0x6011,2)
 for i in range(2,10):c.absolute(0xad,0x1000+i);c.absolute(0x8d,0x6010+i)
 for a,v in [(0x601a,0x65),(0x601b,0x9a),(0x601c,0xa5)]:c.store(a,v)
 def token():
  for i in range(4):c.absolute(0xad,0x6048+i);c.absolute(0x8d,0x604c+i)
 for index,base in enumerate([0,0x4000]):
  c.label(f'ready{index}');c.absolute(0xad,0x6040);c.branch(0xf0,f'ready{index}')
  c.emit(0xc2,0x20,0xa9,base&255,base>>8);c.absolute(0x8d,0x2116)
  c.absolute(0xad,0x6042);c.absolute(0x8d,0x4305);c.emit(0xe2,0x20)
  for a,v in [(0x4300,1),(0x4301,0x18),(0x4302,0),(0x4303,8),(0x4304,0x40),(0x420b,1)]:c.store(a,v)
  token();c.store(0x6050,0xa5)
 c.label('receipt');c.absolute(0xad,0x6051);c.branch(0xf0,'receipt')
 c.label('sealed');c.absolute(0xad,0x6052);c.branch(0xf0,'sealed')
 c.label('active');c.absolute(0xad,0x4212);c.branch(0x30,'active')
 c.label('blank');c.absolute(0xad,0x4212);c.branch(0x10,'blank')
 c.store(0x2107,0x40);c.store(0x2100,15);token();c.store(0x6058,0x5a)
 c.label('done');c.branch(0x80,'done')
 data=c.finish();r=bytearray([255])*32768;r[:len(data)]=data;r[0x7fc0:0x7fd5]=b'NES258 SHARED DMA TEST';r[0x7fd5:0x7fdc]=bytes([0x20,0,5,0,1,0,0])
 for p in range(0x7fe0,0x8000,2):struct.pack_into('<H',r,p,0x8000)
 checksum=sum(r)&65535;struct.pack_into('<HH',r,0x7fdc,checksum^65535,checksum);(out/'slice.sfc').write_bytes(r)
 return len(data)


if __name__=='__main__':
 # Wall-clock allowance for a blocking simulator RPC, never emulated timing.
 # These switches are local to this invocation; Mesen settings are not saved.
 def take(name,default):
  if name not in sys.argv:return default
  i=sys.argv.index(name);value=int(sys.argv[i+1]);del sys.argv[i:i+2];return value
 script_timeout=take('--script-timeout',90)
 rpc_delay_ms=take('--rpc-delay-ms',0)
 assert 1<=script_timeout<=90 and 0<=rpc_delay_ms<=5000
 original_popen=old.subprocess.Popen
 def launch(args,*a,**kw):
  if Path(args[0]).name.lower()=='mesen.exe':
   args=[*args,f'--debug.scriptWindow.scriptTimeout={script_timeout}']
  return original_popen(args,*a,**kw)
 old.subprocess.Popen=launch
 old.LUA=once(old.LUA,'local function rpc(op,a,v)','local function raw_rpc(op,a,v)')
 old.LUA=once(old.LUA,'local bytes={};',r'''local function rpc(op,a,v)
 local ok,value=pcall(raw_rpc,op,a,v)
 if not ok then
  local f=assert(io.open(OUT..'/rpc-error.txt','w'))
  f:write(string.format('seq=%d op=%d address=%d error=%s',seq,op,a,tostring(value)));f:close()
  emu.stop(1);error(value)
 end
 return value
end
local bytes={};''')
 if rpc_delay_ms:
  old.TCL=once(old.TCL,' lassign $cmd op address value',f' lassign $cmd op address value\n if {{$seq==140}} {{after {rpc_delay_ms}}}')
 SEPARATE='--separate' in sys.argv
 original_tb=old.testbench
 # Keep the inherited testbench accessible without recursive monkey patching.
 globals()['old_tb']=original_tb
 original=tb
 def bound_tb():
  old.testbench=original_tb
  try:return original()
  finally:old.testbench=bound_tb
 old.testbench=bound_tb;old.sources=sources;old.rom=rom
 old.LUA=once(old.LUA,"local bytes={};",'''emu.addMemoryCallback(function(a,v)return rpc(0,a,0)end,emu.callbackType.read,0x400000,0x4000ff)
emu.addMemoryCallback(function(a,v)rpc(1,a,v)end,emu.callbackType.write,0x6010,0x601c)
local bytes={};''')
 old.LUA=old.LUA.replace('emu.callbackType.read,0x6040,0x6052','emu.callbackType.read,0x6000,0x6052')
 old.LUA=once(old.LUA,'assert(#bytes==n)','''assert(#bytes==n+16)
  local tile=assert(io.open(OUT..'/tile.hex','r'));local k=0
  for line in tile:lines()do local expected=tonumber(line,16);assert(bytes[k+1]==expected);assert(emu.read(k,emu.memType.snesVideoRam)==expected);k=k+1 end
  tile:close();assert(k==16)''')
 old.LUA=once(old.LUA,'assert(bytes[i+1]==expected','assert(bytes[i+17]==expected')
 if SEPARATE:sys.argv.remove('--separate')
 out=Path(sys.argv[sys.argv.index('--out')+1])
 bridge={'script_timeout_seconds':script_timeout,'injected_rpc140_wall_delay_ms':rpc_delay_ms,'fail_fast_rpc_errors':True}
 old.__doc__=__doc__
 try:old.main()
 finally:
  old.subprocess.Popen=original_popen
  if out.exists():
   for name in ['nes_mux258.py','probe_nes_mux258_coupled.py']:
    shutil.copyfile(Path(__file__).parent/name,out/name)
   (out/'bridge.json').write_text(json.dumps(bridge,indent=2)+'\n',newline='\n')
 f=out/'result.json';r=json.loads(f.read_text());r['shared']=not SEPARATE
 r['bridge']=bridge
 f.write_text(json.dumps(r,indent=2)+'\n',newline='\n')
