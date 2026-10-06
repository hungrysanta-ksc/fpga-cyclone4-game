# SPDX-License-Identifier: MIT
# Bounded first-stage resolution model; no change to production sample registers.
from pathlib import Path
import subprocess,re
from nes_h1_qualified import frontend as old_frontend
TB=r'''
`timescale 1ns/1ps
module resolution_tb;
 reg clk=0;always #5.952381 clk=~clk;
 reg reset=1,rd=1,wr=1,sel=1;reg [23:0] addr=0;
 wire [3:0] error_new,error_old;wire [7:0] data_new,data_old;
 wire oe_new,dir_new,dr_new,dr_old;
 reg [23:0] model_addr;
 integer good_binary=0,x_reproduced=0,delay_cases=0,reads_new=0,reads_old=0;
 nes_snes_frontend dut(.host_clk(clk),.reset(reset),.snes_addr(addr),.read_n(rd),.write_n(wr),.romsel_n(sel),.snes_data_in(8'd0),.bus_data(data_new),.databus_oe_n(oe_new),.databus_dir(dir_new),.reg_write(),.reg_read(),.data_read(dr_new),.reg_address(),.reg_wdata(),.reg_rdata(8'h55),.data(8'ha6),.reg_rvalid(1'b1),.data_valid(1'b1),.ready(1'b1),.busy(1'b0),.fault(1'b0),.frontend_snapshot(),.frontend_error(error_new));
 nes_snes_frontend_043 old(.host_clk(clk),.reset(reset),.snes_addr(addr),.read_n(rd),.write_n(wr),.romsel_n(sel),.snes_data_in(8'd0),.bus_data(data_old),.databus_oe_n(),.databus_dir(),.reg_write(),.reg_read(),.data_read(dr_old),.reg_address(),.reg_wdata(),.reg_rdata(8'h55),.data(8'ha6),.reg_rvalid(1'b1),.data_valid(1'b1),.ready(1'b1),.busy(1'b0),.fault(1'b0),.frontend_snapshot(),.frontend_error(error_old));
 always @(posedge clk)if(reset)begin reads_new<=0;reads_old<=0;end
 else begin if(dr_new)reads_new<=reads_new+1;if(dr_old)reads_old<=reads_old+1;end
 task automatic trial(input integer bit_id,input integer value,input integer delays,input integer phase);
  reset=1;rd=1;wr=1;sel=1;addr=0;#100;reset=0;#100;
  addr=24'h408000;sel=0;#20;rd=0;#120;
  if(oe_new || !dir_new || data_new!==8'ha6 || data_old!==8'ha6)$fatal(1,"response before resolution injection");
  @(negedge clk);#(phase);
  model_addr=24'h408000;
  if(bit_id>=0)begin
   if(value==2)model_addr[bit_id]=1'bx;else model_addr[bit_id]=value[0];
  end
  // One uncertain/old first-stage sample; following samples resolve normally.
  if(bit_id>=0 || (delays&4))begin force dut.addr_meta=model_addr;force old.addr_meta=model_addr;end
  if(delays&1)begin force dut.rd_sync[0]=0;force old.rd_sync[0]=0;end
  if(delays&2)begin force dut.sel_sync[0]=0;force old.sel_sync[0]=0;end
  rd=1;sel=1;addr=24'h011800;
  #0.001;if(!oe_new || dir_new)$fatal(1,"raw release delayed");
  @(posedge clk);#1;
  release dut.addr_meta;release old.addr_meta;
  release dut.rd_sync[0];release old.rd_sync[0];release dut.sel_sync[0];release old.sel_sync[0];
  #180;
  if(error_new!==0 || reads_new!=1 || reads_old!=1)$fatal(1,"044 resolution fault bit=%0d value=%0d delays=%0d phase=%0d new=%b",bit_id,value,delays,phase,error_new);
  if(value==2)begin
   if(!$isunknown(error_old))$fatal(1,"043 X counterexample not reproduced");x_reproduced++;
  end else begin
   if(error_old!==0)$fatal(1,"binary behavior changed");
   if(bit_id>=0)good_binary++;else delay_cases++;
  end
 endtask
 initial begin
  for(integer phase=0;phase<12;phase++)begin
   for(integer bit_id=0;bit_id<24;bit_id++)begin
    trial(bit_id,0,0,phase);trial(bit_id,1,0,phase);trial(bit_id,2,0,phase);
   end
   for(integer delays=0;delays<8;delays++)trial(-1,0,delays,phase);
  end
  if(good_binary!=576 || x_reproduced!=288 || delay_cases!=96)$fatal(1,"coverage");
  $display("PASS RESOLUTION binary=576 X_negative_controls=288 independent_delay_cases=96");$finish;
 end
 initial begin #2000000;$fatal(1,"resolution watchdog");end
endmodule
'''
def run(out,questa):
 (out/'nes_snes_frontend_043.sv').write_text(old_frontend().replace('module nes_snes_frontend(','module nes_snes_frontend_043('))
 (out/'resolution_tb.sv').write_text(TB)
 for label,tool,args in [('vlib','vlib',['resolution_work']),('compile','vlog',['-sv','-work','resolution_work','nes_snes_frontend.sv','nes_snes_frontend_043.sv','resolution_tb.sv']),('run','vsim',['-c','-lib','resolution_work','resolution_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (out/('resolution-'+label+'.log')).open('wb') as f:cp=subprocess.run([str(questa/(tool+'.exe')),*args],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  text=(out/('resolution-'+label+'.log')).read_text()
  assert cp.returncode==0 and not re.search(r'\*\* (?:Fatal|Error):',text),text[-4000:]
 assert 'PASS RESOLUTION binary=576 X_negative_controls=288 independent_delay_cases=96' in text
 return {'binary_resolution_cases':576,'legacy_X_failures_fixed':288,'independent_one_cycle_delay_cases':96,'scope':'Testbench-only forced first-stage samples, both binary resolutions and bounded one-extra-cycle RD/ROMSEL/address models; not physical probability or unbounded metastability proof'}
