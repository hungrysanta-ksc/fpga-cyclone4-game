# SPDX-License-Identifier: MIT
"""Actual generated queue RTL: record mapping, credit, CRC, STOP and wrap."""
import argparse,json,shutil,subprocess
from pathlib import Path
from nes_delta231 import sha

TB=r'''
`timescale 1ns/1ps
module queue312_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,retire=0,consume=0,frame=0;reg [109:0] link=0;
 reg [7:0] address=0;wire [7:0] data;reg [191:0] record=0;
 wire record_valid;wire [4:0] record_at;wire [7:0] record_byte;
 always @(posedge clk)if(record_valid)record[record_at*8+:8]<=record_byte;
 wire ready,fault;wire [8:0] length;wire [199:0] status;
 nes_queue260 dut(.clk(clk),.reset(reset),.enable(1'b1),.link270(link),
 .status270(status),.crc_take270(),.progress_status(128'd0),
 .parser_retire(retire),.consume_record312(consume),.frame_start312(frame),
 .frame_serial312(32'd123),.frame_generation312(16'd7),.record312(record),.load_enable312(1'b1),
 .record_valid312(record_valid),.record_at312(record_at),.record_byte312(record_byte),
 .SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),.selected(),.miso(),
 .sn_address(address),.sn_data(data),.packet_ready(ready),.packet_length(length),.fault(fault));
 reg [7:0] packet[0:255],frozen[0:1023];integer n,i,j,passes=0;
 task restart;
  begin @(negedge clk);reset=1;link=0;retire=0;consume=0;frame=0;
   repeat(3)@(negedge clk);reset=0;frame=1;
   @(negedge clk);frame=0;
   for(i=0;i<1024;i++)dut.buffer[i]=8'ha5;
  end
 endtask
 task makepacket(input integer op,input integer seq,input integer payload);
  begin n=16+payload;for(i=0;i<256;i++)packet[i]=i^8'h69;
   packet[0]=op;packet[1]=2;packet[2]=seq;packet[3]=seq>>8;
   packet[4]=123;packet[5]=0;packet[6]=0;packet[7]=0;packet[8]=7;packet[9]=0;
   packet[10]=8'h34;packet[11]=8'h12;packet[12]=payload;packet[13]=payload>>8;
   packet[14]=8'h78;packet[15]=8'h56;
  end
 endtask
 task byte_event(input integer at,input [7:0] b);
  begin @(negedge clk);link=0;link[32:25]=at==0?0:8'he1;link[24:17]=b;
   link[16:7]=at;link[6:4]=7;link[2]=1;
   @(negedge clk);link[2]=0;link[6:4]=0;
   repeat(64)@(negedge clk);
  end
 endtask
 task sendpacket(input integer good);
  begin byte_event(0,8'he1);
   for(j=0;j<n;j++)byte_event(j+1,packet[j]);
   byte_event(n+1,0);byte_event(n+2,0);
   @(negedge clk);link=0;link[32:25]=8'he1;link[16:7]=n+3;link[3]=1;link[109]=1;link[108]=good;
   @(negedge clk);link=0;repeat(32)@(negedge clk);
  end
 endtask
 task release_slot;
  begin @(negedge clk);retire=1;@(negedge clk);retire=0;repeat(32)@(negedge clk);end
 endtask
 task receipt;
  begin @(negedge clk);consume=1;@(negedge clk);consume=0;end
 endtask
 task passed;begin passes++;end endtask
 initial begin
  restart();makepacket(2,0,240);sendpacket(1);
  if(fault||!ready||length!=256||record[47:32]!=16'h1234||record[63:48]!=16'h5678||record[79:64]!=240)$fatal(1,"normalized header");
  for(i=0;i<16;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"legacy view %0d",i);end
  for(i=16;i<256;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"payload %0d",i);end
  for(i=0;i<480;i++)if(dut.buffer[i]!==8'ha5)$fatal(1,"reserved manifest overwritten");passed();
  release_slot();if(dut.retired!=1||dut.consumed312!=0||ready)$fatal(1,"storage is consumption");passed();
  receipt();if(dut.consumed312!=1)$fatal(1,"receipt counter");passed();
  makepacket(14,1,12);sendpacket(1);
  if(record[111:80]!=={packet[19],packet[18],packet[17],packet[16]}||record[119:112]!==packet[20])$fatal(1,"batch record");
  for(i=16;i<n;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"compact batch %0d",i);end
  release_slot();makepacket(12,2,8);sendpacket(1);
  for(i=16;i<n;i++)begin address=i;repeat(2)@(negedge clk);if(data!==packet[i])$fatal(1,"typed record %0d",i);end
  passed();
  restart();makepacket(2,0,2);sendpacket(0);if(!fault||dut.accepted!=0||ready)$fatal(1,"bad CRC published");passed();
  restart();makepacket(2,0,2);packet[4]=122;sendpacket(1);if(!fault||dut.accepted!=0)$fatal(1,"serial");passed();
  restart();makepacket(2,0,2);packet[8]=8;sendpacket(1);if(!fault)$fatal(1,"generation");passed();
  restart();makepacket(2,1,2);sendpacket(1);if(!fault)$fatal(1,"sequence");passed();
  restart();makepacket(2,0,2);packet[12]=3;sendpacket(1);if(!fault)$fatal(1,"length");passed();
  restart();makepacket(2,0,2);sendpacket(1);makepacket(2,1,2);sendpacket(1);
  if(fault||dut.used!=2||!status[170])$fatal(1,"full credit");
  makepacket(2,2,2);sendpacket(1);if(!fault||dut.accepted!=2)$fatal(1,"third slot");passed();
  restart();release_slot();if(!fault)$fatal(1,"empty release");passed();
  restart();dut.accepted=65535;dut.retired=65535;makepacket(2,0,2);sendpacket(1);
  if(fault||dut.accepted!=0||dut.used!=1)$fatal(1,"storage wrap");release_slot();if(dut.retired!=0||dut.used!=0)$fatal(1,"release wrap");passed();
  restart();dut.sequence312=65535;makepacket(2,65535,2);sendpacket(1);if(!fault)$fatal(1,"sequence namespace exhaustion");passed();
  restart();makepacket(2,0,8);byte_event(0,8'he1);byte_event(1,2);@(negedge clk);reset=1;
  repeat(5)@(negedge clk);if(ready||dut.accepted||dut.retired||dut.consumed312)$fatal(1,"STOP ownership");passed();
  for(i=0;i<1024;i++)frozen[i]=dut.buffer[i];
  byte_event(12,8'hff);byte_event(13,8'hff);
  if(dut.write312)$fatal(1,"STOP write enable");
  for(i=0;i<1024;i++)if(dut.buffer[i]!==frozen[i])$fatal(1,"queue RAM changed after STOP");
  $display("PASS312 queue guards=%0d",passes);$finish;
 end
 initial begin #10000000;$fatal(1,"timeout");end
endmodule
'''

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
    shutil.copyfile(a.source/'nes_queue260.sv',d/'nes_queue260.sv')
    (d/'queue312_tb.sv').write_text(TB,newline='\n')
    q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    for tool,args in [('vlib',['work']),('vlog',['-sv','nes_queue260.sv','queue312_tb.sv']),('vsim',['-c','work.queue312_tb','-do','onerror {quit -code 1};run -all;quit -f'])]:
        with (d/(tool+'.log')).open('wb') as log:r=subprocess.run([q/(tool+'.exe'),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=120)
        assert r.returncode==0,(d/(tool+'.log')).read_text(errors='replace')
    raw=(d/'vsim.log').read_text();assert 'PASS312 queue guards=14' in raw
    (d/'result.json').write_text(json.dumps(dict(passed=True,guards=14,queue_sha=sha(d/'nes_queue260.sv'),test_sha=sha(d/'queue312_tb.sv')),indent=2)+'\n',newline='\n')
    print('PASS312 queue guards=14')
if __name__=='__main__':main()
