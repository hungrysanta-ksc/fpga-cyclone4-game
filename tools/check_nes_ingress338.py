# SPDX-License-Identifier: MIT
"""Actual old/new queue and D4 RTL miters. Link inputs bypass the SPI shifter.

The integrated probe separately exercises the actual shared SPI path.
"""
import argparse,json,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha

TB=r'''
`timescale 1ns/1ps
module ingress338_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1;reg [113:0] qlink=0,tlink=0;
 reg retire=0,consume=0,load=0;reg[3:0] at=0;
 reg[7:0] address=0;reg[191:0] record=0;
 wire[7:0] qold,qnew,rold,rnew;wire fold,fnew,readyold,readynew;
 wire[199:0] sold,snew;
 reg expected=0,ewrite=0;reg[8:0] ea=0;reg[7:0] ed=0;
 nes_queue_old qo(.link270(qlink),.status270(sold),.progress_status(128'd0),
  .frame_start312(1'b0),.frame_serial312(32'h12345678),.frame_generation312(16'h1234),
  .record312(record),.load_enable312(load),.load_at315(at),.record_byte312(rold),
  .expected_select313(expected),.expected_write313(ewrite),.expected_address313(ea),.expected_data313(ed),
  .parser_retire(retire),.consume_record312(consume),.clk(clk),.reset(reset),.enable(1'b1),
  .SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),.sn_address(address),.sn_data(qold),.packet_ready(readyold),.fault(fold));
 nes_queue260 qn(.link270(qlink),.status270(snew),.progress_status(128'd0),
  .frame_start312(1'b0),.frame_serial312(32'h12345678),.frame_generation312(16'h1234),
  .record312(record),.load_enable312(load),.load_at315(at),.record_byte312(rnew),
  .expected_select313(expected),.expected_write313(ewrite),.expected_address313(ea),.expected_data313(ed),
  .parser_retire(retire),.consume_record312(consume),.clk(clk),.reset(reset),.enable(1'b1),
  .SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),.sn_address(address),.sn_data(qnew),.packet_ready(readynew),.fault(fnew));
 reg rv=0,bv=0,last=0,abort_source=0;reg[7:0] rl=9,bd=0;
 wire r0,r1,b0,b1;wire sf0,sf1,hf0,hf1;
 nes_transport_old t0(.record_last319(last),.link270(tlink),.crc_result(16'hcdef),.frame_generation(16'h1234),
  .src_clk(clk),.host_clk(clk),.reset(reset),.abort_source(abort_source),.record_valid(rv),.record_ready(r0),.record_length(rl),
  .record_flush(1'b1),.byte_valid(bv),.byte_ready(b0),.byte_data(bd),.SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),
  .ack_ready(1'b1),.source_fault(sf0),.host_fault(hf0));
 nes_transport257 t1(.record_last319(last),.link270(tlink),.crc_result(16'hcdef),.frame_generation(16'h1234),
  .src_clk(clk),.host_clk(clk),.reset(reset),.abort_source(abort_source),.record_valid(rv),.record_ready(r1),.record_length(rl),
  .record_flush(1'b1),.byte_valid(bv),.byte_ready(b1),.byte_data(bd),.SPI_SS(1'b1),.SPI_SCK(1'b0),.SPI_MOSI(1'b0),
  .ack_ready(1'b1),.source_fault(sf1),.host_fault(hf1));
 task tick;begin @(posedge clk);#1;@(negedge clk);end endtask
 task clear;begin reset=1;qlink=0;tlink=0;rv=0;bv=0;retire=0;consume=0;load=0;abort_source=0;
  repeat(3)tick();reset=0;repeat(12)tick();end endtask
 function [113:0] link(input[7:0] cmd,input integer n,input[7:0] value);
  reg[113:0] v;begin v=0;v[32:25]=cmd;v[24:17]=value;v[16:7]=n;v[6:4]=7;v[2]=1;
  v[113]=1;v[108]=1;link=v;end
 endfunction
 reg[7:0] packet[0:255];integer seq=0,cases=0;
 task sendpacket(input integer n,input integer op,input integer wrong);
  begin
   for(integer i=0;i<n;i++)packet[i]=(i*37+seq*11)&255;
   packet[0]=op;packet[1]=2;packet[2]=seq;packet[3]=seq>>8;
   packet[4]=8'h78;packet[5]=8'h56;packet[6]=8'h34;packet[7]=8'h12;
   packet[8]=8'h34;packet[9]=8'h12;packet[12]=n-16;packet[13]=0;
   if(wrong)packet[4]^=1;
   qlink=link(8'he1,0,8'he1);tick();
   for(integer i=0;i<n;i++)begin qlink=link(8'he1,i+1,packet[i]);tick();end
   qlink=link(8'he1,n+3,0);qlink[3]=1;qlink[6:4]=0;qlink[109]=1;tick();qlink=0;tick();
   if(fold!==fnew||sold!==snew)$fatal(1,"admission/status miter");
   if(wrong)begin if(!fnew)$fatal(1,"identity admitted");end
   else if(!readynew)$fatal(1,"missing packet");
   seq++;
  end
 endtask
 task checkpacket(input integer n,input integer op,input integer bank);
  integer prefix,fields;begin
   prefix=op==14?21:op==12?20:16;fields=prefix-6;
   record=0;record[7:0]=op;record[79:64]=n-16;
   for(integer i=0;i<n;i++)if(qn.buffer[512+256*bank+i]!==packet[i])$fatal(1,"aligned byte %0d",i);
   load=1;
   for(integer i=0;i<fields;i++)begin at=i;tick();if(rold!==rnew)$fatal(1,"record field %0d",i);end
   load=0;
   for(integer i=prefix;i<n;i++)begin address=i;tick();if(qold!==qnew||qnew!==packet[i])$fatal(1,"payload %0d",i);end
   retire=1;tick();retire=0;tick();
   if(sold!==snew||readynew)$fatal(1,"storage credit");
   if(qn.consumed312!=cases)$fatal(1,"retire published consume");
   consume=1;tick();consume=0;tick();cases++;
  end
 endtask
 task publish(input integer value);
  begin
   wait(r0&&r1);@(negedge clk);rv=1;tick();rv=0;
   for(integer i=0;i<9;i++)begin wait(b0&&b1);@(negedge clk);bv=1;bd=value+i;last=i==8;tick();bv=0;last=0;tick();end
   repeat(12)tick();
  end
 endtask
 task prefix(input integer pop,input integer token,input integer generation=4660);
  begin
   tlink=link(8'hd4,0,8'hd4);tick();
   tlink=link(8'hd4,7,8'ha5);tlink[106:91]=generation;tlink[90:75]=token;tlink[74:67]=pop;tlink[66]=1;
   tick();tlink[2]=0;tick();
  end
 endtask
 task response(input integer n);
  begin
   for(integer i=8;i<(n==0?13:15+n);i++)begin
    tlink=link(8'hd4,i,0);tlink[2]=0;tick();tick();
    if(t0.reply!==t1.reply)$fatal(1,"D4 reply %0d %02x %02x",i,t0.reply,t1.reply);
    tlink[2]=1;tick();
   end
   tlink=link(8'hd4,n==0?13:15+n,0);tlink[3]=1;tlink[6:4]=0;tick();tlink[1]=1;tick();
   if(hf0||hf1)$fatal(1,"D4 transaction fault");
  end
 endtask
 initial begin
  clear();
  for(integer opi=0;opi<3;opi++)begin
   for(integer n=(opi==0?21:opi==1?20:16);n<=256;n++)begin
    repeat(2)begin sendpacket(n,opi==0?14:opi==1?12:3,0);checkpacket(n,opi==0?14:opi==1?12:3,(seq-1)%2);end
   end
  end
  expected=1;ewrite=1;ea=471;ed=8'ha6;tick();ewrite=0;tick();if(qnew!==8'ha6||qold!==qnew)$fatal(1,"expected RAM");expected=0;
  sendpacket(32,3,1);clear();seq=0;
  // Two resident packets and storage/full status; completion remains separate.
  sendpacket(256,14,0);sendpacket(256,14,0);
  if(!qn.full||!qo.full||qn.consumed312!=0)$fatal(1,"two slots");
  clear();
  // Empty prefix must remain empty even when a real mailbox publishes later.
  prefix(0,0);publish(30);if(t1.snapshot_length!==0)$fatal(1,"empty response grew");response(0);
  prefix(0,0);publish(60);response(9);
  // POP switches bank; source reuses the opposite bank during this response.
  prefix(1,0);publish(90);response(9);
  prefix(1,1);response(9);
  tlink=link(8'hd5,0,8'hd5);tick();
  tlink=link(8'hd5,7,8'ha5);tlink[106:91]=16'h1234;tlink[90:75]=2;tlink[74:67]=3;tlink[66]=1;tick();
  tlink=link(8'hd5,8,0);tlink[3]=1;tlink[6:4]=0;tick();tlink[1]=1;repeat(10)tick();
  if(hf0||hf1||t1.token!=3||t0.token!=3)$fatal(1,"D5 input commit");
  clear();publish(10);prefix(0,99);if(!hf0||!hf1)$fatal(1,"wrong token accepted");
  clear();publish(10);prefix(0,0,65535);if(!hf0||!hf1)$fatal(1,"wrong generation accepted");
  clear();publish(10);prefix(0,0);
  tlink=link(8'hd4,14,0);tlink[3]=1;tlink[6:4]=0;tick();
  if(!hf0||!hf1)$fatal(1,"partial response accepted");
  clear();publish(10);prefix(0,0);abort_source=1;repeat(5)tick();
  if(!hf0||!hf1||r0||r1||b0||b1)$fatal(1,"STOP failed");
  $display("PASS338 queue=%0d full256 bothbanks/record/payload/credit/identity; D4 empty-late/other-bank/reuse/token/generation/partial/STOP/D5",cases);$finish;
 end
 initial begin #100000000;$fatal(1,"timeout338");end
endmodule
'''


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--source',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);ap.add_argument('--compile-only',action='store_true');a=ap.parse_args()
    d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
    old=BASE/'probes/nes-read336/window01';pins={}
    for name,module in [('nes_queue260.sv','nes_queue_old'),('nes_transport257.sv','nes_transport_old')]:
        p=old/name;pins[str(p)]=sha(p);(d/(module+'.sv')).write_text(p.read_text().replace('module '+name[:-3]+'(','module '+module+'('),newline='\n')
        p=a.source/name;pins[str(p)]=sha(p);(d/name).write_bytes(p.read_bytes())
    p=a.source/'nes_native_mailbox206.sv';pins[str(p)]=sha(p);(d/p.name).write_bytes(p.read_bytes())
    (d/'ingress338_tb.sv').write_text(TB,newline='\n')
    q=Path('C:/altera_standard/25.1std/questa_fse/win64')
    for label,cmd in [('vlib',[str(q/'vlib.exe'),'work']),('vlog',[str(q/'vlog.exe'),'-sv',*[p.name for p in d.glob('*.sv')]]),('vsim',[str(q/'vsim.exe'),'-c','ingress338_tb','-do','run -all; quit -f'])]:
        if label=='vsim' and a.compile_only:print('COMPILE338 PASS; simulation not run');return
        with (d/(label+'.log')).open('wb') as log:r=subprocess.run(cmd,cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
        raw=(d/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and '** Error' not in raw and '** Fatal' not in raw,raw[-5000:]
    assert 'PASS338' in raw
    (d/'result.json').write_text(json.dumps(dict(passed=True,actual_inputs=pins,log=raw),indent=2)+'\n')
    print(raw[-1600:])


if __name__=='__main__':main()
