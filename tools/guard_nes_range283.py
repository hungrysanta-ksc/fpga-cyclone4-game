# SPDX-License-Identifier: MIT
"""Directed admitted-range RAM unit checks; integration owns grant/ACK checks."""
import argparse,json,shutil,re
from pathlib import Path
from nes_delta231 import sha
from guard_nes_spi270 import run

TB=r'''
`timescale 1ns/1ps
module range283_tb;
 reg clk=0,reset=1,stop=0,valid=0,map=0;always #5 clk=~clk;
 reg [11:0] first=0,count=0;wire ready,init;wire [3:0] fault;
 reg [7:0] mem[0:1023],q;wire [9:0] addr;wire we;wire [7:0] data;
 integer checks=0,writes=0;reg [7:0] expected[0:1023];
 always @(posedge clk)begin q<=mem[addr];if(we)begin mem[addr]<=data;writes++;end end
 nes_validator278 dut(.clk(clk),.reset(reset),.abort_source(stop),.fault(fault),
 .manifest_at282(),.manifest_started282(),.context_ready(),.h_ready(),.v_sealed(),
 .display_response(),.display_response_valid(),.display_request_ready(),.crc_index278(),.crc_done278(),
 .grant278(1'b0),.grant_epoch278(32'd0),.grant_serial278(32'd0),.grant_generation278(16'd0),.grant_raw278(3'd0),
 .host_ack278(1'b0),.init278(init),.ram_q(q),.ram_addr(addr),.ram_we(we),.ram_w(data),
 .display_write(1'b0),.display_request(1'b0),.display_response_ready(1'b0),
 .v_begin_valid(1'b0),.v_target_bank(1'b0),.v_raw_count(3'd0),
 .v_range_valid(valid),.v_map_range(map),.v_first(first),.v_count(count),
 .v_check_valid(1'b0),.v_check_value(8'd0),.v_finish_valid(1'b0),.v_all_consumed(1'b0),.v_ready(ready),
 .h_start(1'b0),.h_kind(2'd0),.h_index(4'd0),.h_valid(1'b0),.h_data(8'd0),
 .context_valid(1'b0),.context_data(8'd0));
 task clear;
 begin
  @(negedge clk);reset=1;stop=0;valid=0;
  for(integer i=0;i<1024;i++)begin mem[i]=0;expected[i]=0;end
  repeat(3)@(negedge clk);reset=0;wait(init);@(negedge clk);
  // Unit-only admitted lifetime. Full SPI tests independently verify grant,
  // descriptor consumption, STOP and final ACK without these deposits.
  dut.active=1;dut.state=dut.V_ACTIVE;dut.v_bank=0;writes=0;
 end endtask
 task submit(input integer f,input integer n,input bit m);
 begin @(negedge clk);first=f;count=n;map=m;valid=1;
 @(negedge clk);valid=0;
 if($isunknown({ready,fault}))$fatal(1,"unbound range status");
 for(integer timeout=0;!ready&&!fault;timeout++)begin
  if(timeout>4096)$fatal(1,"range timeout");@(negedge clk);
 end end endtask
 task accept(input integer f,input integer n,input bit m);
 integer a;begin submit(f,n,m);if(fault)$fatal(1,"range rejected %0d %0d map%0d",f,n,m);
  for(integer i=f;i<f+n;i++)begin
   a=(m?562:396)+(i>>3);expected[a]|=1<<(i&7);
   if(!m)expected[i>>3]|=1<<(i&7);
  end
  for(integer i=0;i<1024;i++)if(mem[i]!==expected[i])$fatal(1,"RAM mismatch %0d f%0d n%0d got%h expected%h",i,f,n,mem[i],expected[i]);checks++;
 end endtask
 task reject(input integer f,input integer n,input bit m);
 integer saved_writes;begin saved_writes=writes;submit(f,n,m);
 if(fault!=2||writes!=saved_writes)$fatal(1,"bad range admission f%0d n%0d m%0d fault%0d writes%0d",f,n,m,fault,writes-saved_writes);checks++;
 end endtask
 initial begin
  for(integer offset=0;offset<8;offset++)begin
   for(integer n=1;n<=33;n++)begin clear();accept(offset,n,0);end
  end
  clear();accept(0,1024,0);accept(1024,128,0);accept(1152,32,0);accept(1184,128,0);
  for(integer i=1312;i<1328;i++)accept(i,1,0);
  clear();accept(0,32,1);accept(32,1,1);accept(33,31,1);accept(2017,31,1);
  clear();reject(0,0,0);clear();reject(1023,2,0);clear();reject(1151,2,0);
  clear();reject(1183,2,0);clear();reject(1311,2,0);clear();reject(1312,2,0);
  clear();reject(1328,1,0);clear();reject(4095,1,0);clear();reject(4095,4095,0);
  clear();reject(0,33,1);clear();reject(2047,2,1);
  clear();accept(3,7,0);reject(3,7,0);
  clear();accept(32,8,1);reject(31,1,1);
  for(integer phase=0;phase<4;phase++)begin
   clear();@(negedge clk);first=3;count=100;map=0;valid=1;@(negedge clk);valid=0;
   case(phase)
    0:wait(dut.state==dut.V_RREAD);1:wait(dut.state==dut.V_RWRITE);
    2:wait(dut.state==dut.V_PREAD);3:wait(dut.state==dut.V_PWRITE);
   endcase
   if(clk)@(negedge clk);stop=1;#1;begin integer saved_writes;saved_writes=writes;
   repeat(12)@(negedge clk);if(fault!=4||we||writes!=saved_writes)$fatal(1,"STOP RAM write phase%0d",phase);end
   checks++;
  end
  $display("PASS RANGE283 checks=%0d",checks);$finish;
 end
 initial begin #10000000;$fatal(1,"unit timeout");end
endmodule
'''


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--source',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    shutil.copyfile(a.source/'nes_validator278.sv',d/'nes_validator278.sv')
    (d/'range283_tb.sv').write_text(TB,encoding='utf-8',newline='\n');shutil.copyfile(__file__,d/Path(__file__).name)
    run(a.questa_bin/'vlib.exe',['work'],d,'vlib')
    run(a.questa_bin/'vlog.exe',['-sv','nes_validator278.sv','range283_tb.sv'],d,'vlog')
    log=run(a.questa_bin/'vsim.exe',['-c','work.range283_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim')
    match=re.search(r'PASS RANGE283 checks=(\d+)',log);assert match
    result=dict(passed=True,checks=int(match[1]),scope=__doc__,rtl_sha256=sha(d/'nes_validator278.sv'),test_sha256=sha(d/'range283_tb.sv'))
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))


if __name__=='__main__':main()
