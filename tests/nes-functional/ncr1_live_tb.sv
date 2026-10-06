// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module ncr1_live_tb;
 reg queue_clk=0,host_clk=0,reset=1;
 wire clk=queue_clk,reset_nes=reset,cold_reset=reset;
 always #23.280423 queue_clk=~queue_clk;
 initial begin #1.1;forever #5.952381 host_clk=~host_clk;end
 reg [15:0] reset_epoch=7;
 wire frame_start,frame_end,supported_mode;
 wire [7:0] frame_id;wire [2:0] fine_x;reg chr_32k;
 wire [63:0] palette_snes;
 wire bg_valid;wire signed [8:0] bg_line;wire [8:0] bg_dot;
 wire [14:0] bg_chr_address;wire [1:0] bg_palette;wire [31:0] bg_tick;
 wire frame_ready,encoder_fault;wire [7:0] encoder_error;
 wire desc_valid,desc_ready;wire [15:0] desc_epoch,desc_seq;wire [23:0] desc_base;wire [11:0] desc_length;
 wire mem_req_valid,mem_req_ready,mem_rsp_valid,mem_rsp_ready,mem_rsp_error;
 wire [23:0] mem_req_address,mem_rsp_address;wire [15:0] mem_req_epoch,mem_rsp_epoch;wire [7:0] mem_rsp_data;
 wire [1:0] p_op;wire [15:0] p_epoch,p_seq;wire [11:0] p_length;wire [7:0] p_data;
 wire p_accept,done,producer_fault,exhausted;wire [3:0] p_error;wire [7:0] producer_error;wire [15:0] published;
 wire ready,busy,fault,host_read_owned;wire [3:0] bus_error,frontend_error;wire [127:0] frontend_snapshot;
 reg [23:0] snes_addr=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] snes_data_in=0;
 wire [7:0] bus_data;wire databus_oe_n,databus_dir;
 reg [7:0] cpumem_din=0,ppumem_din=0;
 reg [4:0] joypad1_data=0,joypad2_data=0;
 wire [24:0] cpumem_addr;wire [21:0] ppumem_addr;
 wire cpumem_read,cpumem_write,ppumem_read,ppumem_write;wire [7:0] cpumem_dout,ppumem_dout;
 wire [5:0] color;wire [2:0] emphasis;wire [8:0] cycle,scanline;wire [15:0] sample;
 wire [1:0] joypad_clock;wire [2:0] joypad_out;wire apu_ce,hsync,hblank,vsync,vblank;
 wire tap_ce,tap_bgp,tap_mode,tap_ppu_change,tap_mapper_change;
 wire [2:0] tap_fine;wire [14:0] tap_scroll;wire [95:0] tap_palette;wire [1:0] tap_attribute;
 wire tap_fault;wire [7:0] tap_error;
 wire immutable_chr=1;
 integer frames_started=0,frames_ended=0,seq_read=0,bytes_read=0,acquire_retries=0,fd,fp;
 reg test_arm=0;initial begin #60000000;test_arm=1;end
 wire arm=test_arm && frames_started<4;
 nes_probe dut(.*);
 nes_ncr1_ppu_tap tap(.*);
 nes_ncr1_encoder encoder(.*);
 nes_packet_memory_producer producer(.*);
 nes_transport transport(.*);
 reg [7:0] prg[0:65535],chr[0:32767],ram[0:2047],nt[0:2047];
 integer i,pixels=0,fetches=0;
 reg collecting=0;reg [8:0] prevcycle=511,prevline=511;
 always @(posedge clk)begin
  if(cpumem_read)begin
   if(cpumem_addr<65536)cpumem_din<=prg[cpumem_addr];
   else if(cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)cpumem_din<=ram[cpumem_addr[10:0]];
   else cpumem_din<=0;
  end
  if(cpumem_write && cpumem_addr>=25'h380000 && cpumem_addr<25'h380800)ram[cpumem_addr[10:0]]<=cpumem_dout;
  if(ppumem_read)begin
   if(ppumem_addr>=22'h200000 && ppumem_addr<(chr_32k?22'h208000:22'h204000))ppumem_din<=chr[ppumem_addr[14:0]];
   else if(ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800)ppumem_din<=nt[ppumem_addr[10:0]];
   else ppumem_din<=0;
  end
  if(ppumem_write && ppumem_addr>=22'h3a0000 && ppumem_addr<22'h3a0800)nt[ppumem_addr[10:0]]<=ppumem_dout;
  if(!reset)begin
   if(frame_start)begin
    if(!frame_ready || $isunknown({tap_palette,tap_scroll,tap_mode,tap_fine}))$fatal(1,"frame unavailable or unknown state");
    frames_started++;collecting=1;fp=$fopen($sformatf("frame-%0d.hex",frames_started),"w");
    $fdisplay(fd,"S %0d %0d",frames_started,bg_tick);
   end
   if(bg_valid)begin
    if($isunknown({bg_chr_address,tap_attribute}) || dut.core.ppu.vram_din!==chr[bg_chr_address])$fatal(1,"physical CHR tap/data mismatch");
    fetches++;$fdisplay(fd,"E %0d %0d %0d %0d %0d %0d",frames_started,bg_line,bg_dot,bg_tick,bg_chr_address,tap_attribute);
   end
   if(frame_end)begin frames_ended++;collecting=0;$fclose(fp);$fdisplay(fd,"F %0d %0d",frames_ended,bg_tick);end
   if(desc_valid && desc_ready)begin
    if(desc_seq>frames_ended)$fatal(1,"early publication");
    $fdisplay(fd,"D %0d %0d",desc_seq,bg_tick);
   end
   if(encoder_fault || producer_fault || fault || tap_fault)$fatal(1,"pipeline fault tap%h encoder%h producer%h bus%h line%0d dot%0d palette%h scroll%h",tap_error,encoder_error,producer_error,bus_error,scanline,cycle,tap_palette,tap_scroll);
  end
 end
 always @(negedge clk)begin
  if(collecting && (cycle!=prevcycle || scanline!=prevline) && scanline<240 && cycle>=2 && cycle<=257)begin
   if($isunknown(color) || emphasis!=0)$fatal(1,"invalid output pixel");
   $fwrite(fp,"%02x\n",color);pixels++;
  end
  prevcycle=cycle;prevline=scanline;
 end
  task automatic wr(input integer a,input integer value);
  snes_addr=a;snes_data_in=value;romsel_n=1;#20;write_n=0;#180;write_n=1;#20;snes_addr=24'h123456;#100;
 endtask
 task automatic rd(input integer a,input integer want,input integer payload);
  snes_addr=a;romsel_n=payload?0:1;#20;read_n=0;#160;
  if(databus_oe_n || !databus_dir || (!payload && bus_data!==want[7:0]))$fatal(1,"read address%h got%h wanted%h frontend%h",a,bus_data,want,frontend_error);
  if(payload)begin bytes_read++;$fdisplay(fd,"B %0d %0d",seq_read,bus_data);end
  #60;read_n=1;romsel_n=1;snes_addr=24'habcd00;
  #0.001;if(!databus_oe_n || databus_dir)$fatal(1,"raw release");#100;
 endtask
 task automatic consume(input integer seqnum,input integer base_addr,input integer length);
  integer n;
  wr(24'h6002,reset_epoch&255);wr(24'h6003,reset_epoch>>8);wr(24'h6004,seqnum&255);wr(24'h6005,seqnum>>8);wr(24'h6000,1);
  n=0;while(!ready && !fault && n<50000)begin #100;n++;if(!busy && !ready && !fault)begin acquire_retries++;wr(24'h6000,1);end end
  if(!ready || fault || producer_fault)$fatal(1,"acquire failed producer%h bus%h",producer_error,bus_error);
  rd(24'h6006,length&255,0);rd(24'h6007,length>>8,0);
  for(integer i=0;i<length;i++)rd(24'h408000+i,0,1);
  rd(24'h6008,length&255,0);rd(24'h6009,length>>8,0);
  wr(24'h6000,2);n=0;while(busy && n<50000)begin #100;n++;end
  if(busy || fault || host_read_owned || frontend_error)$fatal(1,"commit");
 endtask

 initial begin
  integer unused;unused=$value$plusargs("CHR32=%d",chr_32k);
  fd=$fopen("live.tsv","w");$readmemh("prg.hex",prg);$readmemh("chr.hex",chr,0,chr_32k?32767:16383);
  for(i=0;i<2048;i++)begin ram[i]=0;nt[i]=0;end
  #20000;reset=0;
  for(integer f=1;f<=4;f++)begin
   wait(published==f);seq_read=f;consume(f,0,2008);
   $display("CONSUMED frame=%0d tick=%0d pixels=%0d",f,bg_tick,pixels);
  end
  if(frames_ended!=4 || bytes_read!=8032 || pixels!=245760 || fetches!=65552)$fatal(1,"accounting");
  $display("PASS LIVE NES frames=4 bytes=8032 pixels=%0d fetches=%0d",pixels,fetches);$fclose(fd);$finish;
 end
 initial begin repeat(15)begin #10000000;$display("PROGRESS tick%0d frames%0d bytes%0d",bg_tick,frames_ended,bytes_read);end $fatal(1,"watchdog");end
endmodule
