# SPDX-License-Identifier: MIT
"""SPI ordinary packets -> executable C consumer -> real bus/CDC/core.

All71 ARM262 packet plans replay unchanged. Tile bytes remain planner output
fixtures. The C executor is DPI host code, not a target CPU timing measurement.
"""
from pathlib import Path
import argparse,json,os,shutil
from nes_delta231 import BASE,ROOT,sha,once
from nes_joint263 import sources
from probe_nes_joint262 import prepare as old_prepare,tb as old_tb,run
from probe_nes_joint261 import packets

EXTRA=r'''
 import "DPI-C" function int producer263(input int command,input int a,input int b);
 reg [7:0] all263[0:65535],expected263[0:8569],tiles263[0:24575];
 integer sizes263[0:255],tile_sizes263[0:255];reg [63:0] tile_desc263[0:255];
 integer ordinary263=0,event263=0,frames263=0,dmabytes263=0,tilebytes263=0,packetbytes263=0;
 reg active263=0,producer_done263=0;reg tv263=0;wire tr263;reg [7:0] td263=0;
 reg [4:0] ti263=0;reg [5:0] tl263=16;reg [1:0] tk263=0;reg [9:0] ts263=0;
 function automatic integer call263(input integer cmd,input integer a,input integer b);
 integer r;begin r=producer263(cmd,a,b);if(r<0)$fatal(1,"C consumer error%0d cmd%0d a%0d frame%0d",r,cmd,a,f);return r;end endfunction
 task emit263(input integer count263);
 integer word263,ignore263;reg [7:0] ready263;
 begin
  for(integer i=0;i<count263;i++)begin
   word263=call263(3,i,0);
   do rd261(24'h006064,ready263);while(!ready263);
   for(integer j=0;j<3;j++)wr261(24'h006060+j,word263>>(8*j));
   wr261(24'h006063,8'ha5);event263++;
  end
  do rd261(24'h006064,ready263);while(!ready263);
 end endtask
 task ordinary_task263;
 integer n,ignore263,events263,copy263;reg [7:0] val263;reg [31:0] tok263;
 reg [7:0] p263[0:255];
 begin
  n=dut.flow.qlen;
  for(integer i=0;i<n;i++)begin rd261(24'h400000+i,val263);p263[i]=val263;ignore263=call263(1,i,val263);end
  if(p263[0]==7)begin
   wait(staged);n={p263[15],p263[14]};tok263={p263[19],p263[18],p263[17],p263[16]};
   if(dut.flow.owner!=dut.flow.TILE||dut.flow.chunk_token!=tok263||dut.flow.chunk_length!=n)$fatal(1,"tile ownership");
   #41904;
   for(integer i=0;i<n;i++)begin rd261(24'h400800+i,val263);ignore263=call263(5,i,val263);end
   token261(tok263);wr261(24'h006050,8'ha5);tilebytes263+=n;dmabytes263+=n;
   n=dut.flow.qlen;
  end
  if(p263[0]==2||p263[0]==4||p263[0]==5||p263[0]==8)begin
   copy263=p263[0]==2?{p263[13],p263[12]}:{p263[15],p263[14]};
   repeat(copy263)#560; // Prior260 ordinary byte-service allocation, NOT CPU WCET.
  end
  events263=call263(2,n,0);emit263(events263);
  if(p263[0]==3)begin
   wait(v_sealed);
   for(integer i=0;i<8570;i++)if(call263(4,i,0)!==int'(expected263[i]))$fatal(1,"metadata frame%0d byte%0d C=%0d expected=%0d",f,i,call263(4,i,0),expected263[i]);
   for(integer i=0;i<754;i++)if(dut.core.memory[i<332?i:i+64]!==receipts[(f-905)*754+i])$fatal(1,"receipt263 frame%0d byte%0d actual=%h expected=%h",f,i,dut.core.memory[i<332?i:i+64],receipts[(f-905)*754+i]);
   for(integer i=0;i<64;i++)if(dut.core.memory[332+i]!==hashes[(f-905)*64+i])$fatal(1,"CRC263 frame%0d byte%0d",f,i);
  end
  wr261(24'h006010,p263[0]==3?1:0);wr261(24'h006011,p263[0]);
  for(integer i=2;i<10;i++)wr261(24'h006010+i,p263[i]);
  wr261(24'h00601a,8'h65);wr261(24'h00601b,8'h9a);wr261(24'h00601c,8'ha5);
  wait(dut.flow.qdone);@(negedge host_clk);ordinary263++;
 end endtask
 task tiles_task263;
 integer at,n,unit;reg [63:0] desc;
 begin
  at=0;
  for(integer k=0;k<tile_sizes263[0];k++)begin
   desc=tile_desc263[k];tk263=desc[49:48];unit=tk263==1?32:16;n=desc[31:0];tl263=unit;
   for(integer j=0;j<n;j++)begin
    repeat(4)@(negedge clk);wait(tr263);@(negedge clk);tv263=1;ti263=j%unit;ts263=desc[47:32]+j/unit;td263=tiles263[at+j];
    @(negedge clk);tv263=0;
   end
   at+=n;
  end
  wait(er);@(negedge clk);ev=1;@(negedge clk);ev=0;
 end endtask
 initial begin : bus263
 integer n,first263,ignore263;reg [7:0] val263;reg [31:0] token263;
 wait(!reset);
 forever begin
  @(negedge host_clk);
  if(active263)begin
   if(dut.flow.ordinary_ready)ordinary_task263();
   else if(dut.flow.state==dut.flow.DMA&&staged)begin
    n=dut.flow.chunk_length;first263=dut.flow.first;token263=dut.flow.chunk_token;
    ignore263=call263(6,first263,n/2);#41904;
    for(integer i=0;i<n;i++)begin
     rd261(24'h400800+i,val263);
     if(val263!==expected263[first263*2+i])$fatal(1,"map DMA263");
     ignore263=call263(7,first263*2+i,val263);
    end
    token261(token263);wr261(24'h006050,8'ha5);dmabytes263+=n;
    wait(dut.flow.state!=dut.flow.DMA);
   end else if(v_sealed&&dut.flow.state==dut.flow.IDLE)begin
    token261(dut.flow.last_map_token);wr261(24'h006058,8'h5a);wait(!v_sealed);
   end
  end
 end
 end
 task output_frame;
 integer at,n,ignore263,start_events263,start_ordinary263,start_dma263;reg [15:0] crc263;
 begin
  if(f==905)ignore263=call263(0,0,0);
  start_events263=event263;start_ordinary263=ordinary263;start_dma263=dmabytes263;
  name=$sformatf("all%0d.hex",f);$readmemh(name,all263);
  name=$sformatf("all%0d.lens",f);$readmemh(name,sizes263);
  name=$sformatf("meta%0d.hex",f);$readmemh(name,expected263);
  name=$sformatf("tiles%0d.hex",f);$readmemh(name,tiles263);
  name=$sformatf("tiles%0d.lens",f);$readmemh(name,tile_sizes263);
  name=$sformatf("tiles%0d.desc",f);$readmemh(name,tile_desc263);
  prelude_task262();
  for(integer i=0;i<28;i++)ignore263=call263(1,i,begin262[i]);
  ignore263=call263(2,28,0);active263=1;producer_done263=0;
  fork
   tiles_task263();
   begin
    at=76;
    for(integer k=2;k<sizes263[0];k++)begin
     wait((dut.flow.queue.accepted-dut.flow.queue.retired)<4);
     n=sizes263[k+1];tx[0]=8'he1;crc263=c16(16'hffff,8'he1);
     for(integer j=0;j<n;j++)begin tx[j+1]=all263[at+j];crc263=c16(crc263,tx[j+1]);end
     tx[n+1]=crc263[15:8];tx[n+2]=crc263[7:0];transfer(n+3);at+=n;packetbytes263+=n+3;
    end
    producer_done263=1;
   end
  join
  wait(flow_retired);@(negedge clk);active263=0;frames263++;
  $fwrite(events261,"consumer,%0d,%0d,%0d,%0d\n",f,event263-start_events263,ordinary263-start_ordinary263,dmabytes263-start_dma263);
  wait(start_ready);
 end endtask
'''

def tb():
 s=old_tb().replace('joint262_tb','joint263_tb').replace('nes_joint262 dut','nes_joint263 dut')
 # Replace the fixture consumer and automatic map bus worker; preserve source.
 a=s.index(' initial begin : bus261');b=s.index(' initial begin : negative261',a);s=s[:a]+s[b:]
 a=s.index(' task output_frame;');b=s.index(' initial begin : query_cancel',a)
 split=EXTRA.index(' function automatic')
 s=s[:a]+EXTRA[split:]+'\n'+s[b:]
 s=once(s,' reg enable=0;',EXTRA[:split]+'\n reg enable=0;')
 ports=['v_range_valid','v_map_range','v_first','v_count','v_check_valid','v_check_value','v_finish_valid','v_all_consumed','stream_valid','stream_data','h_start','h_kind','h_index','h_valid','h_data']
 for n in ports:s=once(s,f'.{n}({n}),','')
 s=s.replace(".tile_valid(1'b0),.tile_ready(),.tile_data(8'd0),.tile_index(5'd0),.tile_length(6'd16),.tile_kind(2'd0),.tile_slot(10'd0)",'.tile_valid(tv263),.tile_ready(tr263),.tile_data(td263),.tile_index(ti263),.tile_length(tl263),.tile_kind(tk263),.tile_slot(ts263)')
 s=once(s,'   wait(er);@(negedge clk);ev=1;@(negedge clk);ev=0;packet_seq261=0;', '   packet_seq261=0;')
 # Producer owns ordering. The reference image checks address/data independently.
 a=s.index('   if(sink_data!==stream_bytes[sink_at]');b=s.index('   accepted++;sink_at++;',a)
 s=s[:a]+'''   if(sink_kind!=0)$fatal(1,"unexpected ordinary map stream");
   if(sink_unit>=1152)begin
    if(sink_data!==expected263[sink_unit<1184?4096+(sink_unit-1152)*16+sink_lane:6273+(sink_unit-1184)*16+sink_lane])$fatal(1,"ordinary sink data");
   end
'''+s[b:]
 s=once(s,'  events261=$fopen', '  sink_ready=1;\n  events261=$fopen')
 s=s.replace('PASS JOINT262','PASS JOINT263')
 return s

def prepare(d,last):
 src,pins,stats=old_prepare(d,last);src.pop('nes_joint262.sv');new=sources()
 for n,s in new.items():(d/n).write_text(s,encoding='utf-8',newline='\n');src[n]=''
 for f in range(905,last+1):
  pp=packets(BASE/f'probes/nes-joint262/arm01/frame{f}.packets')
  (d/f'all{f}.hex').write_text(b''.join(pp).hex(' '),encoding='utf-8')
  (d/f'all{f}.lens').write_text(' '.join(f'{n:x}' for n in [len(pp),*[len(p) for p in pp]]),encoding='utf-8')
  root=BASE/'probes/nes-wholepath247/jointdecode-test02/run'
  metadata=root/f'expected-{f-904}.bin';bank=root/f'bank-{f-904}.bin'
  for path in [metadata,bank]:pins[path.relative_to(BASE).as_posix()]=sha(path)
  (d/f'meta{f}.hex').write_text(metadata.read_bytes().hex(' '),encoding='utf-8')
  raw=bank.read_bytes();data=bytearray();desc=[]
  for p in pp:
   if p[0]!=7:continue
   section=p[1];first=int.from_bytes(p[10:12],'little');n=int.from_bytes(p[14:16],'little');unit=32 if section else 16
   desc.append((section<<48)|((first//unit)<<32)|n);data+=raw[(16384 if section else 0)+first:(16384 if section else 0)+first+n]
  (d/f'tiles{f}.hex').write_text((data or b'\x00').hex(' '),encoding='utf-8')
  (d/f'tiles{f}.lens').write_text(f'{len(desc):x} {len(data):x}',encoding='utf-8')
  (d/f'tiles{f}.desc').write_text(' '.join(f'{n:016x}' for n in (desc or [0])),encoding='utf-8')
 (d/'joint263_tb.sv').write_text(tb(),encoding='utf-8',newline='\n')
 for name in ['nes_producer263.c','nes_joint263.py','probe_nes_joint263.py']:
  path=ROOT/'tools'/name;shutil.copyfile(path,d/name);pins[path.relative_to(BASE).as_posix()]=sha(path)
 return src,pins,stats

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);p.add_argument('--last',type=int,default=975);a=p.parse_args()
 d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 src,pins,stats=prepare(d,a.last)
 run('C:/altera_standard/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe',['-O2','-std=c99','-Wall','-Wextra','-Werror','-shared','nes_producer263.c','-o','producer263.dll'],d,'native')
 run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'joint263_tb.sv'],d,'vlog')
 log=run(a.questa_bin/'vsim.exe',['-c','-sv_lib','producer263','work.joint263_tb',f'+LAST={a.last}','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',1800)
 assert f'PASS JOINT263 frames={a.last-904}' in log
 r=dict(passed=True,frames=a.last-904,rtl_hashes={n:sha(d/n) for n in src},input_hashes=pins,scope=__doc__,actual_SNES=False,full_ARM=False,physical=False,whole_FIT=False)
 (d/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8');print(log[-1500:])

if __name__=='__main__':main()
