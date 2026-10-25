# SPDX-License-Identifier: MIT
"""Actual338 tap FSM + unchanged independent validator at22MHz; bounded job boundary, not whole executor."""
import argparse,ast,binascii,json,shutil,struct,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_refill267 import run

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 src=BASE/'probes/nes-raster355/fixed01';flow=(src/'nes_mux260.sv').read_text()
 block=flow[flow.index(' reg [11:0] read_count;'):flow.index(' // One command handshake;')]
 block=block.replace(' reg [11:0] read_count;','').replace('posedge host_clk','posedge clk')
 wrapper='''module nes_read358(input wire clk,reset,abort_source,input wire [3:0] vf,
 input wire read_n,end_read,input wire [23:0] address,input wire [15:0] startpos,
 input wire [11:0] read_count,chunk_length,input wire [7:0] aperture_data,op,kind,
 input wire range_ready,ordinary_hash_ready,
 output wire idle,failed,rv,rm,hs,hv,output wire [1:0] hk,output wire [3:0] hi,
 output wire [11:0] unit_at,output wire [7:0] value);
 localparam DMA=1,CHECK=2;wire [1:0] state=DMA;
 wire rst=abort_source,fault=(vf!=0),chunk_ready=1,write_n=1,bus_valid=1;
 wire invalidate_banks=abort_source,rs=end_read,rp=0;wire [23:0] ap=address;
 wire [7:0] header[0:1];assign header[0]=op;assign header[1]=kind;
 wire data_command278=op!=7&&op!=12&&op!=14,zero325=0;
 wire [2:0] prelude_raw=1;wire [15:0] scroll_length=1;
 wire crc_reset287;
'''+block+'''
 assign idle=tap_idle278;assign failed=tap_fault278;
 assign rv=receipt_valid282&&range_ready&&!rst&&!fault;assign rm=map336;
 assign hs=tap_start278&&range_ready&&!rst&&!fault;assign hv=tap_byte278&&!rst;
 assign hk=tap_raw278?2'd0:2'd1;assign hi=tap_relative278[7:4];
 assign unit_at=unit336;assign value=tap_value278;
 endmodule
'''
 (d/'nes_read358.sv').write_text(wrapper,newline='\n');shutil.copyfile(src/'nes_validator278.sv',d/'nes_validator278.sv')
 tree=ast.parse((ROOT/'tools/check_nes_final332.py').read_text());tb=next(n.value.value for n in ast.walk(tree) if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='tb' for t in n.targets))
 tb='`timescale 1ns/1ps\n'+tb.replace('always #5 clk','always #22.727 clk')
 start=tb.index(' initial begin\n  $readmemh');tb=tb[:start]+r'''
 reg rd=1,er=0;reg [23:0] bus_address=24'h400800;reg [15:0] startpos=0;
 reg [11:0] read_count=0;reg [7:0] aperture_data=0,op=12,kind=2;
 wire idle,failed,rv,rm,hs,hv;wire [1:0] hk;wire [3:0] hi;wire [11:0] unit_at;wire [7:0] byte_value;
 nes_read358 tap(clk,reset,abort_source,fault,rd,er,bus_address,startpos,read_count,12'd4095,aperture_data,op,kind,ready,h_ready,idle,failed,rv,rm,hs,hv,hk,hi,unit_at,byte_value);
 integer ticks=0,at_tick,elapsed,maxjob=0;
 always @(posedge clk)ticks<=ticks+1;
 task setup;
 begin
  reset=1;abort_source=0;rd=1;er=0;read_count=0;repeat(3)@(negedge clk);reset=0;wait(initialized);@(negedge clk);
  grant=1;@(negedge clk);grant=0;wait(context_ready);@(negedge clk);
  for(integer j=0;j<32;j++)begin context_valid=1;context_data=context_bytes[j];@(negedge clk);end
  context_valid=0;beg=1;@(negedge clk);beg=0;wait(ready);@(negedge clk);
 end endtask
 task byte_job(input integer b,input integer stop_at);
 begin
  bus_address=24'h400800+read_count;aperture_data=b;rd=0;
  @(negedge clk);at_tick=ticks;
  if(stop_at>=0)begin
   repeat(stop_at)@(negedge clk);abort_source=1;
   repeat(12)@(negedge clk);if(we||sealed||rv||hs||hv||!idle)$fatal(1,"STOP escaped job");
  end else begin
   wait(idle);@(negedge clk);elapsed=ticks-at_tick;
   if(fault||failed)$fatal(1,"job fault op=%0d kind=%0d at=%0d vf=%0d",op,kind,startpos+read_count,fault);
   $display("JOB358 op=%0d kind=%0d at=%0d clocks=%0d",op,kind,startpos+read_count,elapsed);
   if(elapsed>maxjob)maxjob=elapsed;
  end
  rd=1;er=1;@(negedge clk);er=0;read_count=read_count+1;@(negedge clk);
 end endtask
 initial begin
  $readmemh("context.hex",context_bytes);
  setup();op=12;kind=2;startpos=0;for(integer j=0;j<16;j++)byte_job(j,-1);
  if(memory[768]!==255)$fatal(1,"map coverage");
  setup();op=1;kind=3;startpos=0;for(integer j=0;j<16;j++)byte_job(j,-1);
  if(memory[656]!==1||memory[144]!==1)$fatal(1,"OAM private coverage");
  setup();op=1;kind=5;startpos=0;byte_job(0,-1);
  if(dut.digest!==16'he1f0)$fatal(1,"scroll independent CRC");
  setup();op=1;kind=5;startpos=3169;for(integer j=0;j<16;j++)byte_job(j,-1);
  if({memory[449],memory[448]}!==16'h3b37)$fatal(1,"raw independent CRC");
  if(memory[676]!==1||memory[164]!==1)$fatal(1,"raw private coverage");
  for(integer k=0;k<12;k++)begin
   setup();op=1;kind=5;startpos=3169;
   for(integer j=0;j<15;j++)byte_job(j,-1);
   byte_job(15,k);
   $display("PASS STOP358 offset=%0d",k);
  end
  $display("PASS READ358 max=%0d",maxjob);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout358");end
endmodule
'''
 for x,y in [('.grant_raw278(3\'d0)',".grant_raw278(3'd1)"),('.v_raw_count(3\'d0)',".v_raw_count(3'd1)"),('.v_range_valid(range_valid)','.v_range_valid(rv)'),('.v_map_range(map_range)','.v_map_range(rm)'),('.v_first(first)','.v_first(unit_at)'),('.v_count(count)',".v_count(12'd1)"),('.h_start(h_start)','.h_start(hs)'),(".h_kind(2'd1)",'.h_kind(hk)'),(".h_index(4'd0)",'.h_index(hi)'),('.h_valid(h_valid)','.h_valid(hv)'),('.h_data(h_data)','.h_data(byte_value)')]:tb=tb.replace(x,y)
 decl=tb[tb.index(' reg rd='):tb.index(' nes_read358 tap')]
 tb=tb.replace(decl,'').replace(' nes_validator278 dut',decl+' nes_validator278 dut')
 # This fixture binds actual admitted context but deliberately does not run final display; final checks have a separate regression.
 h=bytearray(32);h[:4]=b'H2\x02\0';struct.pack_into('<IIHH',h,4,1,1,1,1);h[16:19]=b'\1\1\1';h[19]=24;h[20]=1;struct.pack_into('<H',h,24,250)
 struct.pack_into('<H',h,30,binascii.crc_hqx(h[:30],65535))
 (d/'context.hex').write_text(''.join(f'{v:02x}\n' for v in h));(d/'final332_tb.sv').write_text(tb,newline='\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv','nes_validator278.sv','nes_read358.sv','final332_tb.sv'],d,'vlog')
 log=run(q/'vsim.exe',['-c','work.final332_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',120)
 m=re.search(r'PASS READ358 max=(\d+)',log);assert m,log[-2000:]
 jobs=[dict(op=int(a),kind=int(b),at=int(c),clocks=int(v)) for a,b,c,v in re.findall(r'JOB358 op=(\d+) kind=(\d+) at=(\d+) clocks=(\d+)',log)]
 result=dict(passed=True,six_clock_passed=int(m[1])<=6,max_clocks=int(m[1]),jobs=jobs,STOP_cases=12,scope=__doc__,limits='Actual338 tap block extracted unchanged except clock name, actual validator. Qualified aperture data/end-read fixture; no actual aperture timing, queue, CDC, SPI, final ACK or VBlank timing proof.',pins={str(p):sha(p) for p in [src/'nes_mux260.sv',src/'nes_validator278.sv',Path(__file__),d/'nes_read358.sv',d/'final332_tb.sv',d/'context.hex',d/'vsim.log']})
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ('pins','jobs')}))
if __name__=='__main__':main()
