"""Read every selected packed ROM byte through the actual synchronous host bus."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_raw506 import sha

BENCH=r'''
`timescale 1ns/1ps
module longrun694_bus_tb;
 reg clk=0,reset=1,active=0,stop=0,fault=0,read_n=1,write_n=1,romsel_n=1;
 reg [23:0] address=0;wire [7:0] data_out;wire oe_n,dir;
 wire [7:0] pa,ab;wire [3:0] ai;wire mp,aw,ap,pc;wire [15:0] pads;
 nes_sink_bus165 dut(.clk(clk),.reset(reset),.active(active),.stop(stop),.fault(fault),
 .address(address),.read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(8'd0),
 .data_out(data_out),.oe_n(oe_n),.dir(dir),.packet_ready(1'b0),.packet_length(9'd0),.packet_data(8'd0),
 .packet_address(pa),.map_progress(mp),.ack_write(aw),.ack_index(ai),.ack_byte(ab),.ack_publish(ap),.pad_commit(pc),.pad_buttons(pads));
 always #5.952 clk=~clk;
 reg [7:0] expected[0:5119];integer count=0;
 task automatic rd(input [23:0] addr,input [7:0] wanted,input integer phase);
  #(phase);address=addr;romsel_n=0;#90.908;read_n=0;#180.816;
  if(oe_n||!dir||data_out!==wanted)$fatal(1,"ROM %h wanted=%h got=%h",addr,wanted,data_out);
  count++;read_n=1;#0.001;if(!oe_n||dir)$fatal(1,"read did not release immediately");
  romsel_n=1;address=24'h123456;#45.454;
 endtask
 initial begin
  $readmemh("sink-program.hex",expected);repeat(8)@(negedge clk);reset=0;active=1;
  rd(24'h00fffc,expected[5116],0);rd(24'h00fffd,expected[5117],3);
  for(integer i=0;i<5056;i++)rd(24'h008000+24'(i),expected[i],i%23);
  for(integer i=0;i<64;i++)rd(24'h00ffc0+24'(i),expected[5056+i],i%23);
  rd(24'h0093c0,8'hff,7);rd(24'h00ffbf,8'hff,17);
  stop=1;rd(24'h006001,8'h80,0);
  address=24'h008000;romsel_n=0;read_n=0;#100;active=0;#0.001;
  if(!oe_n||dir||ap||mp)$fatal(1,"inactive bus not released");
  active=1;reset=1;#0.001;if(!oe_n||dir)$fatal(1,"reset bus not released");
  $display("PASS694 bus reads=%0d phases=23 STOP-status inactive/reset release",count);$finish;
 end
 initial begin #5000000;$fatal(1,"bus watchdog");end
endmodule
'''
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ('board','out','bin'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    for n in ('nes_sink_bus165.sv','sink-program.hex'):shutil.copyfile(a.board/n,a.out/n)
    (a.out/'test.sv').write_text(BENCH,newline='\n')
    for t,args in [('vlib',['work']),('vlog',['-sv','nes_sink_bus165.sv','test.sv']),('vsim',['-c','longrun694_bus_tb','-do','onbreak {quit -code 1};onerror {quit -code 1};run -all;quit -code 0'])]:
        with (a.out/(t+'.log')).open('wb') as f:subprocess.run([a.bin/(t+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=60,check=True)
    assert 'PASS694 bus reads=5125' in (a.out/'vsim.log').read_text()
    (a.out/'result.json').write_text(json.dumps(dict(passed=True,reads=5125,clock_MHz=84,phases=23,pins={n:sha(a.out/n) for n in ('nes_sink_bus165.sv','sink-program.hex','test.sv','vsim.log')},scope='Actual host program bus and selected ROM initialization; STOP status plus externally inactive/reset release, not full board STOP propagation or CPU co-simulation'),indent=2)+'\n')
    print('PASS694 host bus5125 reads/23 phases, STOP status/reset release')
