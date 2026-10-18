# SPDX-License-Identifier: MIT
"""Actual bus RTL equality for split5KiB versus direct8KiB; no board timing."""
from pathlib import Path
import argparse,json,shutil,subprocess,tempfile
from nes_delta231 import sha

TB=r'''`timescale 1ns/1ps
module tb;
 reg clk=0;always #10 clk=~clk;
 reg reset=1,active=1,read_n=0,write_n=1,romsel_n=0;
 reg [23:0] address=0;
 wire [7:0] d8,d5;wire o8,o5,dir8,dir5;
 wire [7:0] pa8,pa5;wire aw8,aw5,ap8,ap5,pc8,pc5;
 wire [3:0] ai8,ai5;wire [7:0] ab8,ab5;wire [15:0] pad8,pad5;
 direct8 dut8(.data_out(d8),.oe_n(o8),.dir(dir8),.packet_address(pa8),.ack_write(aw8),.ack_index(ai8),.ack_byte(ab8),.ack_publish(ap8),.pad_commit(pc8),.pad_buttons(pad8),
 .clk(clk),.reset(reset),.active(active),.stop(1'b0),.fault(1'b0),.address(address),.read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(8'h5a),.packet_ready(1'b1),.packet_length(9'd256),.packet_data(8'ha6));
 split5 dut5(.data_out(d5),.oe_n(o5),.dir(dir5),.packet_address(pa5),.ack_write(aw5),.ack_index(ai5),.ack_byte(ab5),.ack_publish(ap5),.pad_commit(pc5),.pad_buttons(pad5),
 .clk(clk),.reset(reset),.active(active),.stop(1'b0),.fault(1'b0),.address(address),.read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(8'h5a),.packet_ready(1'b1),.packet_length(9'd256),.packet_data(8'ha6));
 reg [7:0] expected[0:8191];integer i,checks=0;reg [7:0] want;
 task readcheck(input [23:0] addr,input [7:0] value);
 begin @(negedge clk);address=addr;repeat(5)@(posedge clk);#1;
 if(o8!==0||o5!==0||dir8!==1||dir5!==1||d8!==value||d5!==value)$fatal(1,"read %h expected%h got%h/%h oe%b/%b",addr,value,d8,d5,o8,o5);
 checks=checks+1;
 end endtask
 initial begin
 $readmemh("sink-program.hex",expected);repeat(4)@(posedge clk);@(negedge clk);reset=0;
 for(i=0;i<32768;i=i+1)begin
 want=(i<8128||i>=32704)?expected[i%8192]:8'hff;readcheck(24'h8000+i,want);
 end
 for(i=0;i<256;i=i+1)readcheck(24'h400000+i,8'ha6);
 readcheck(24'h6000,8'h01);readcheck(24'h6001,0);readcheck(24'h6004,0);readcheck(24'h6005,1);
 readcheck(24'h9000,expected[4096]);
 @(negedge clk);read_n=1;#1;if(o8!==1||o5!==1)$fatal(1,"raw read cancel");
 read_n=0;reset=1;#1;if(o8!==1||o5!==1)$fatal(1,"raw reset cancel");
 reset=0;active=0;#1;if(o8!==1||o5!==1)$fatal(1,"inactive cancel");
 active=1;write_n=0;#1;if(o8!==1||o5!==1)$fatal(1,"write exclusion");
 $display("PASS STORAGE247 reads=%0d raw_guards=4",checks);$finish;
 end
endmodule
'''

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--map',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);d=Path(tempfile.mkdtemp(prefix='nes-storage-rtl247-'))
 for variant,name in [('direct8k','direct8'),('split5k','split5')]:
  s=(a.map/'runs'/variant/'rom.sv').read_text().replace('module nes_sink_bus165','module '+name)
  (d/(name+'.sv')).write_text(s)
 for f in ('sink-program.hex','program-lo.hex','program-hi.hex'):shutil.copyfile(a.map/'runs/split5k'/f,d/f)
 (d/'tb.sv').write_text(TB)
 try:
  for exe,args in [('vlib',['work']),('vlog',['-sv','direct8.sv','split5.sv','tb.sv']),('vsim',['-c','work.tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
   with (d/(exe+'.log')).open('wb') as log:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
   assert r.returncode==0,(exe,(d/(exe+'.log')).read_text(errors='replace')[-2000:])
  log=(d/'vsim.log').read_text();assert 'PASS STORAGE247 reads=33029 raw_guards=4' in log
  result=dict(passed=True,scope=__doc__,read_checks=33029,raw_guards=4,map_sha256=sha(a.map/'result.json'),script_sha256=sha(Path(__file__)),fit=False,sta=False,physical=False)
  (out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS STORAGE247 reads=33029 raw_guards=4')
 finally:shutil.copytree(d,out/'run',dirs_exist_ok=True);shutil.copyfile(__file__,out/'test.py')

if __name__=='__main__':main()
