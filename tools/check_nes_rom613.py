"""Read the exact packaged SNES program through the fitted board's ROM aperture."""
import argparse,json,subprocess,shutil
from pathlib import Path
from check_nes_wire600 import ROOT,read,sha
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('board','client','out','bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 assert sha(a.client/'sink165.sfc')==read(ROOT/'analysis/oe612-verification.json')['client_SHA']
 for n in ('sink-program.hex','nes_sink_bus165.sv'):shutil.copy(a.board/n,a.out/n)
 rom=(a.client/'sink165.sfc').read_bytes();expected=rom[:5056]+rom[-64:]
 (a.out/'expected.hex').write_text(''.join(f'{b:02x}\n' for b in expected),newline='\n')
 bench='''`timescale 1ns/1ps
module rom613_tb;
 reg clk=0,run=1,reset=1,active=1,stop=0;always #5 if(run)clk=!clk;
 reg [23:0] address=0;reg read_n=1;wire [7:0] data;wire oe,dir;
 reg [7:0] expected[0:5119];integer i;
 nes_sink_bus165 dut(.clk(clk),.reset(reset),.active(active),.stop(stop),.fault(1'b0),
 .address(address),.read_n(read_n),.write_n(1'b1),.romsel_n(1'b0),.data_in(8'd0),.data_out(data),.oe_n(oe),.dir(dir),
 .packet_ready(1'b0),.packet_length(9'd0),.packet_data(8'd0),.packet_address(),.ack_write(),.ack_index(),.ack_byte(),.ack_publish(),.pad_commit(),.pad_buttons());
 initial begin
  $readmemh("expected.hex",expected);#32;reset=0;
  for(i=0;i<5120;i=i+1)begin
   @(negedge clk);read_n=1;address=(i<5056)?24'h008000+i:24'h00ffc0+i-5056;
   @(negedge clk);read_n=0;repeat(4)@(negedge clk);
   if(oe||!dir||data!==expected[i])$fatal(1,"ROM613 byte %0d",i);
  end
  address=24'h0093c0;repeat(5)@(negedge clk);if(data!==8'hff)$fatal(1,"ROM gap");
  address=24'h006001;stop=1;repeat(5)@(negedge clk);if(oe||data!==8'h80)$fatal(1,"STOP status");
  run=0;#3;reset=1;#1;if(!oe||dir)$fatal(1,"clock stopped reset");
  $display("PASS613 ROM=5120 gap STOP reset");$finish;
 end
endmodule
'''
 (a.out/'test.sv').write_text(bench,newline='\n')
 for tool,args in [('vlib',['work']),('vlog',['-sv','nes_sink_bus165.sv','test.sv']),('vsim',['-c','rom613_tb','-do','onbreak {quit -code 1}; onerror {quit -code 1}; run -all; quit -code 0'])]:
  with (a.out/(tool+'.log')).open('wb') as f:subprocess.run([a.bin/(tool+'.exe'),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=120)
 assert 'PASS613 ROM=5120' in (a.out/'vsim.log').read_text()
 (a.out/'result.json').write_text(json.dumps(dict(bytes=5120,program=sha(a.board/'sink-program.hex'),client=sha(a.client/'sink165.sfc'),
   bus=sha(a.board/'nes_sink_bus165.sv'),bench=sha(a.out/'test.sv'),log=sha(a.out/'vsim.log')),indent=2)+'\n',newline='\n')
