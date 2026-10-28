# SPDX-License-Identifier: MIT
"""Real SPI and common byte program: variable EA, RAM tags and cancellation.
This is a protocol/port test; ROM responses here are deterministic, not a frame
schedule. The live ARM/ROM test remains the timing authority.
"""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import ROOT,sha
from probe_nes_refill267 import run

TB=r'''`timescale 1ns/1ps
module hint398_tb;
 reg clk=0,nclk=0;always #5.952 clk=~clk;always #23.2805 nclk=~nclk;
 reg reset=1,stop=0,ss=1,sck=0,mosi=0;reg[15:0]generation398=1;wire rst=reset||stop;
 wire[153:0]link;wire[199:0]qs,ps,hs;
 wire qirq,qfault,pfault,hfault,pcfault;reg failed=0;
 wire mv,mw,iov,iow,handler;wire[7:0]ma,md,mq,ioa,iod,ioq,qq;
 wire[11:0]ca,pc;reg[17:0]code,rom[0:4095];reg[11:0]tag;
 reg mseen=0;wire fire=iov&&!pcfault&&!failed&&!rst;
 wire[31:0]bus398={7'd0,fire&&iow,ioa,iod,8'd0};
 wire[127:0]progress={40'd0,bus398,56'd0};
 assign ioq=ioa>=112&&ioa<=126?qq:ioa>=128&&ioa<=175?link[153:146]:8'd0;
 always @(posedge clk)begin
  code<=rom[ca];tag<=ca;
  if(rst)begin mseen<=0;failed<=0;end
  else begin
   if(mv&&!mseen)mseen<=1;else if(mv&&mseen)mseen<=0;
   if(fire&&iow&&ioa==8)failed<=1;
  end
 end
 nes_byte398 #(.IRQ_ENTRY(IRQ398)) cpu(.clk(clk),.reset(rst),.stop(failed||qfault||pfault||hfault),.irq(qirq),
  .code_address(ca),.code_data(code),.code_ready(tag==pc),.mem_valid(mv),.mem_write(mw),.mem_address(ma),.mem_data(md),.mem_ready(mseen),.mem_q(mq),
  .io_valid(iov),.io_write(iow),.io_address(ioa),.io_data(iod),.io_ready(1'b1),.io_q(ioq),.fault(pcfault),.in_irq(handler),.debug_pc(pc));
 wire qa,pa,pcrc;wire[7:0]pq,hq;wire qselected,qmiso;reg end_sealed=0,retire_done=0;wire plan_seal,plan_retire;integer seals=0,retires=0;
 always @(posedge clk)if(rst)begin seals<=0;retires<=0;end else begin if(plan_seal)seals<=seals+1;if(plan_retire)retires<=retires+1;end
 nes_queue260 queue(.irq398(qirq),.control_write398(fire&&iow),.control_address398(ioa),.control_q398(qq),
  .admit319(qa),.link270(link),.status270(qs),.crc_take270(),.progress_status(progress),.frame_start312(1'b0),.frame_serial312(32'd905),.frame_generation312(16'd1),
  .record312(192'd0),.load_enable312(1'b0),.load_at315(4'd0),.storage_empty312(),.record_valid312(),.record_at312(),.record_byte312(),
  .expected_select313(1'b0),.expected_write313(1'b0),.expected_address313(9'd0),.expected_data313(8'd0),.parser_retire(1'b0),.consume_record312(1'b0),
  .clk(clk),.reset(rst),.enable(1'b1),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(qselected),.miso(qmiso),.sn_address(8'd0),.sn_data(),.packet_ready(),.packet_length(),.fault(qfault));
 wire[199:0]plan_status;
 assign ps={plan_status[199:8],plan_status[7:0]|hq};
 nes_plan_spi200 endpoint(.admit319(pa),.link270(link),.status270(plan_status),.crc_take270(pcrc),.clk(clk),.reset(rst),.enable(1'b1),.stop(stop),.source_fault(1'b0),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.selected(),.miso(),.fault(pfault),.plan_idle(1'b1),.plan_ready(1'b1),.plan_write(),.plan_data(),.plan_seal(plan_seal),.plan_length(),.plan_plans(),.plan_crc(),
  .retire_done(retire_done),.retire(plan_retire),.end_generation(generation398),.chunk_ready(1'b0),.chunk_kind(1'b0),.chunk_length(12'd0),.chunk_slot(10'd0),.chunk_generation(16'd0),.chunk_token(32'd0),.end_sealed(end_sealed));
 nes_spi270 spi(.clk(clk),.reset(rst),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.source_status(200'd0),.output_status(qs),.plan_status(ps),
  .progress_irq284(),.progress_mode284(),.source_mode367(),.request_crc_enable(pcrc),.queue_admit319(qa),.plan_admit319(pa),.link(link));
 wire hmactive,active,request,busy,finished;wire[3:0]hmat;wire[7:0]hmq;wire[21:0]address;reg response=0,hold_response=0,late_response=0;
 nes_hint361 hint(.host_clk(clk),.clk(nclk),.reset(rst),.stop(stop),.prelease(1'b1),.display_lease(1'b0),.immutable(1'b1),
  .generation(generation398),.epoch(32'h01020304),.serial(32'd905),.link(link),.control_q398(hq),.meta_active398(hmactive),.meta_at398(hmat),.meta_q398(hmq),
  .active(active),.request(request),.address(address),.ready(1'b1),.response(response),.error(1'b0),.fault(hfault),.busy(busy),.finished(finished));
 nes_tile_link394 tile_link(.hint_metaactive398(hmactive),.hint_meta_at398(hmat),.hint_meta_q398(hmq),.nes_clk(nclk),.host_clk(clk),.reset(rst),.source_fault(failed),
  .tile_valid(1'b0),.tile_ready(),.tile_data(8'd0),.tile_index(5'd0),.tile_length(6'd16),.tile_kind(2'd0),.tile_slot(10'd0),.tile_generation(16'd1),
  .end_valid(1'b0),.end_partial(1'b0),.end_ready(),.end_generation(16'd1),.word_valid(),.word_ready(1'b1),.word_end(),.word_partial(),.word_kind(),.word_generation(),.word_slot(),.word_length(),
  .read_at(10'd800+ma),.meta_write(mv&&mw&&ma<224&&!mseen&&!rst&&!failed),.meta_data(md),.read_data(mq),.fault());
 integer grants=0,n,mode,bytes398;reg[7:0]wire398[0:599],frozen[0:1023];reg[15:0]crc;
 always @(posedge nclk)begin
  response<=!rst&&(request&&!hold_response||late_response);
  if(rst)grants<=0;
  else if(request)begin
   if(address!==22'h200000+((13'h213+grants/16)<<4)+(grants%16))$fatal(1,"tag address grant%0d got%h",grants,address);
   grants<=grants+1;
  end
 end
 function automatic[15:0]c16(input[15:0]old,input[7:0]v);reg[15:0]c;begin c=old^{v,8'd0};for(integer i=0;i<8;i++)c=c[15]?(c<<1)^16'h1021:c<<1;c16=c;end endfunction
 function automatic[7:0]c8(input[7:0]old,input[7:0]v);reg[7:0]c;begin c=old^v;for(integer i=0;i<8;i++)c=c[7]?(c<<1)^8'h07:c<<1;c8=c;end endfunction
 task plan_packet(input integer length);reg[7:0]h;begin
  for(integer i=0;i<600;i++)wire398[i]=0;
  wire398[0]=8'he9;wire398[1]=length&255;wire398[2]=length>>8;wire398[3]=length==512?16:1;
  if(length==3)begin wire398[4]=8'h83;wire398[5]=generation398[7:0];wire398[6]=generation398[15:8];end
  else for(integer r=0;r<16;r++)begin
   wire398[4+32*r+1]=255;wire398[4+32*r+2]=generation398[7:0];wire398[4+32*r+3]=generation398[15:8];
   wire398[4+32*r+4]=r+1;wire398[4+32*r+6]=8'h13;wire398[4+32*r+7]=2;wire398[4+32*r+8]=255;wire398[4+32*r+15]=1;
   for(integer a=0;a<8;a++)begin wire398[4+32*r+16+2*a]=a+1;wire398[4+32*r+17+2*a]=2;end
  end
  crc=65535;for(integer i=4;i<4+length;i++)crc=c16(crc,wire398[i]);wire398[4+length]=crc[15:8];wire398[5+length]=crc[7:0];
  h=0;for(integer i=0;i<6+length;i++)h=c8(h,wire398[i]);wire398[6+length]=h;wire398[7+length]=8'ha5;send_packet(8+length);repeat(300)@(negedge clk);
 end endtask
 task retire_packet(input integer accepted);reg[7:0]h;begin
  wire398[0]=8'hea;wire398[1]=generation398[7:0];wire398[2]=generation398[15:8];wire398[3]=accepted>>8;wire398[4]=accepted;
  h=0;for(integer i=0;i<5;i++)h=c8(h,wire398[i]);wire398[5]=h;wire398[6]=8'ha5;send_packet(7);repeat(300)@(negedge clk);
 end endtask
 task make_packet(input integer tags,alter);begin
  for(integer i=0;i<64;i++)wire398[i]=0;
  wire398[0]=8'hea;wire398[1]=tags;wire398[2]=1;wire398[4]=4;wire398[5]=3;wire398[6]=2;wire398[7]=1;wire398[8]=8'h89;wire398[9]=3;
  for(integer i=0;i<tags;i++)begin wire398[12+i*2]=(13'h213+i)&255;wire398[13+i*2]=(13'h213+i)>>8;end
  if(alter==5)wire398[4]=5;if(alter==6)wire398[13]=8'h82;if(alter==7)wire398[2]=2;
  crc=65535;for(integer i=0;i<12+tags*2;i++)crc=c16(crc,wire398[i]);wire398[12+tags*2]=crc[7:0];wire398[13+tags*2]=crc[15:8];
  if(alter==3)wire398[13+tags*2]^=1;
  bytes398=14+2*tags;if(alter==4)bytes398--;
 end endtask
 task send_packet(input integer length);begin
  ss=0;#2000;
  for(integer j=0;j<length;j++)for(integer b=7;b>=0;b--)begin mosi=wire398[j][b];#190.476190476;sck=1;#190.476190476;sck=0;end
  #2000;ss=1;#2000;
 end endtask
 task restart;begin reset=1;ss=1;sck=0;stop=0;hold_response=0;late_response=0;end_sealed=0;retire_done=0;generation398=1;repeat(30)@(negedge clk);reset=0;repeat(60)@(negedge clk);end endtask
 initial begin
  $readmemh("program398.hex",rom);
  for(n=1;n<=7;n++)begin
   restart();make_packet(n,0);send_packet(bytes398);repeat(2000)@(negedge clk);
   if(failed||qfault||pfault||hfault||pcfault||grants!=16*n||busy)$fatal(1,"EA%0d failed%0b q%0b p%0b h%0b cpu%0b pc%0d grants%0d event%0d",n,failed,qfault,pfault,hfault,pcfault,pc,grants,queue.event_count);
   $display("EA398 valid tags%0d wire%0d grants%0d",n,bytes398,grants);
  end
  for(mode=1;mode<=7;mode++)begin
   restart();make_packet(mode==1?0:mode==2?8:3,mode);send_packet(bytes398);repeat(1000)@(negedge clk);
   if(!(failed||qfault||pfault||hfault||pcfault)||grants!=0)$fatal(1,"bad EA%0d grants%0d pc%0d",mode,grants,pc);
   $display("EA398 reject%0d no_ROM_grants",mode);
  end
  restart();make_packet(3,0);send_packet(bytes398);repeat(2000)@(negedge clk);if(grants!=48)$fatal(1,"first hint missing");
  send_packet(bytes398);repeat(1000)@(negedge clk);if(!(failed||qfault||pfault||hfault||pcfault)||grants!=48)$fatal(1,"used hint reused");
  for(integer g=0;g<5;g++)begin
  restart();case(g)0:generation398=0;1:generation398=1;2:generation398=12;3:generation398=13;4:generation398=65530;endcase
  plan_packet(3);if(seals!=1||failed||qfault||pfault||pcfault)$fatal(1,"E9 seal failed");
  end_sealed=1;@(negedge clk);end_sealed=0;repeat(10)@(negedge clk);retire_packet(1);
  if(retires!=1||failed||qfault||pfault||hfault||pcfault||grants!=0)$fatal(1,"EA7 retire conflated with hint");
  retire_done=1;@(negedge clk);retire_done=0;repeat(10)@(negedge clk);if(endpoint.accepted!=0||endpoint.ended||endpoint.retiring)$fatal(1,"retire completion lifetime");
  $display("EA398 retire generation%0d PASS",generation398);end
  restart();plan_packet(512);if(seals!=1||failed||qfault||pfault||pcfault||endpoint.plan_length!=512||endpoint.plan_plans!=16)$fatal(1,"E9 512-byte length/cursor boundary");
  $display("EA398 E9 512B/16plans/520wire PASS");
  restart();plan_packet(3);end_sealed=1;@(negedge clk);end_sealed=0;repeat(10)@(negedge clk);retire_packet(2);
  if(!(failed||qfault||pfault||hfault||pcfault)||retires!=0||grants!=0)$fatal(1,"wrong accepted retire admitted");
  restart();make_packet(3,0);send_packet(15);stop=1;repeat(20)@(negedge clk);
  for(integer i=0;i<1024;i++)frozen[i]=tile_link.memory[i];
  repeat(256)begin @(negedge clk);if(mv||iov||request)$fatal(1,"STOP event leak");for(integer i=0;i<1024;i++)if(tile_link.memory[i]!==frozen[i])$fatal(1,"STOP RAM mutation");end
  restart();hold_response=1;make_packet(3,0);send_packet(bytes398);repeat(20)@(negedge nclk);
  if(!busy||!hint.pending||grants!=1)$fatal(1,"active STOP fixture did not hold one ROM request");
  stop=1;repeat(4)@(negedge nclk);late_response=1;
  for(integer i=0;i<1024;i++)frozen[i]=tile_link.memory[i];
  repeat(256)begin @(negedge nclk);if(request||finished||mv||iov)$fatal(1,"active STOP leaked request/DONE/write");for(integer i=0;i<1024;i++)if(tile_link.memory[i]!==frozen[i])$fatal(1,"active STOP RAM mutation");end
  stop=0;repeat(32)begin @(negedge nclk);if(request||finished||busy)$fatal(1,"late DONE resurrected cancelled hint");end
  late_response=0;
  $display("HINT398 PASS valid7 E9_EA7_retire negative9 STOP256 active_STOP_late_DONE32 actual_program_and_RAM_ports");$finish;
 end
endmodule
'''

def main():
 p=argparse.ArgumentParser();p.add_argument('--rtl',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 sources=['nes_byte398.sv','nes_queue260.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_plan_path267.sv','nes_tile_link394.sv','nes_native_mailbox206.sv','nes_domain_reset124.sv']
 for n in sources+['program398.hex']:shutil.copyfile(a.rtl/n,d/n)
 labels=json.loads((a.rtl/'program398.json').read_text())['labels'];(d/'hint398_tb.sv').write_text(TB.replace('IRQ398',str(labels['interrupt'])),newline='\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*sources,'hint398_tb.sv'],d,'vlog')
 out=run(q/'vsim.exe',['-c','hint398_tb','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',180);assert 'HINT398 PASS'in out
 report=dict(passed=True,valid_counts=list(range(1,8)),E9_EA7_retire=True,E9_512B_16plans=True,EA7_generations=[0,1,12,13,65530],negatives=9,STOP_freeze_clocks=256,active_hint_STOP_late_DONE=True,late_DONE_clocks=32,pins={n:sha(d/n)for n in sources+['program398.hex','hint398_tb.sv']},scope=__doc__)
 (d/'result.json').write_text(json.dumps(report,indent=2)+'\n');print('HINT398 PASS counts1..7 E9_EA7_retire negative9 STOP256')
if __name__=='__main__':main()
