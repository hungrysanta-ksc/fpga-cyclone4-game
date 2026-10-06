// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module ncr1_encoder_tb;
 reg queue_clk=0,host_clk=0,reset=1;
 always #23.280423 queue_clk=~queue_clk;
 initial begin #1.1;forever #5.952381 host_clk=~host_clk;end
 integer cycles=0;always @(posedge queue_clk)cycles<=cycles+1;
 reg [15:0] reset_epoch=7;
 reg frame_start=0,frame_end=0,supported_mode=1;
 reg [7:0] frame_id=1;reg [2:0] fine_x=0;reg chr_32k=1;
 reg [63:0] palette_snes=64'h@PALETTE@;
 reg bg_valid=0;reg signed [8:0] bg_line=0;reg [8:0] bg_dot=0;
 reg [14:0] bg_chr_address=0;reg [1:0] bg_palette=0;reg [31:0] bg_tick=0;
 wire frame_ready,encoder_fault;wire [7:0] encoder_error;
 wire desc_valid,desc_ready;wire [15:0] desc_epoch,desc_seq;wire [23:0] desc_base;wire [11:0] desc_length;
 wire mem_req_valid,mem_req_ready,mem_rsp_valid,mem_rsp_ready,mem_rsp_error;
 wire [23:0] mem_req_address,mem_rsp_address;wire [15:0] mem_req_epoch,mem_rsp_epoch;wire [7:0] mem_rsp_data;
 wire [1:0] p_op;wire [15:0] p_epoch,p_seq;wire [11:0] p_length;wire [7:0] p_data;
 wire p_accept,done,producer_fault,exhausted;wire [3:0] p_error;wire [7:0] producer_error;wire [15:0] published;
 wire ready,busy,fault,host_read_owned;wire [3:0] bus_error,frontend_error;wire [127:0] frontend_snapshot;
 reg [23:0] snes_addr=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] snes_data_in=0;
 wire [7:0] bus_data;wire databus_oe_n,databus_dir;
 nes_ncr1_encoder encoder(.*);
 nes_packet_memory_producer producer(.*);
 nes_transport transport(.*);
 reg [79:0] events[0:131103];reg [7:0] golden[0:16383];
 integer checks=0,bytes_read=0,acquire_retries=0,fd,origin_cycle,origin_tick,frames_ended=0,descriptors=0;
 always @(posedge queue_clk)if(!reset && desc_valid && desc_ready)begin
  descriptors++;$fdisplay(fd,"D %0t %0d %0d %0d",$time,desc_epoch,desc_seq,frames_ended);
  if(descriptors>frames_ended)$fatal(1,"descriptor published before frame end");
 end
 task automatic pass(input string name);checks++;$display("PASS CASE %s",name);endtask
 task automatic restart;
  @(negedge queue_clk);reset=1;reset_epoch=reset_epoch+1'b1;frame_start=0;frame_end=0;bg_valid=0;supported_mode=1;
  read_n=1;write_n=1;romsel_n=1;
  #0.001;if(desc_valid || mem_req_valid || frame_ready || mem_rsp_valid)$fatal(1,"reset gating");
  repeat(6)@(negedge queue_clk);reset=0;repeat(12)@(negedge queue_clk);
  frames_ended=0;descriptors=0;
 endtask
 task automatic start_frame(input integer f);
  if(!frame_ready)$fatal(1,"source ownership unavailable at frame start");
  frame_id=f%4+1;fine_x=f<4?0:1;chr_32k=f<4;frame_start=1;
  @(negedge queue_clk);frame_start=0;
 endtask
 task automatic event_at(input integer i,input integer mutation=0);
  reg [79:0] e;e=events[i];bg_line=e[34:26];bg_dot=e[25:17];bg_chr_address=e[16:2];bg_palette=e[1:0];bg_tick=e[66:35];
  case(mutation)
   1:bg_dot=bg_dot+2;
   2:bg_tick=events[i-1][66:35];
   3:bg_chr_address=bg_chr_address^1;
   4:bg_palette=1;
   5:bg_chr_address=bg_chr_address^16;
   6:bg_chr_address=bg_chr_address^16384;
  endcase
  bg_valid=1;@(negedge queue_clk);bg_valid=0;
 endtask
 task automatic finish_frame;
  repeat(3)@(negedge queue_clk);frame_end=1;frames_ended++;
  $fdisplay(fd,"F %0t %0d %0d",$time,reset_epoch,frames_ended);
  @(negedge queue_clk);frame_end=0;
 endtask
 task automatic stream_frame(input integer f,input integer timed);
  integer first_tick;first_tick=events[f*16388][66:35];
  if(timed)while(cycles<origin_cycle+first_tick-origin_tick-4)@(negedge queue_clk);
  start_frame(f);
  for(integer j=0;j<16388;j++)begin
   if(timed)while(cycles<origin_cycle+events[f*16388+j][66:35]-origin_tick)@(negedge queue_clk);
   event_at(f*16388+j);
   if(encoder_fault || desc_valid || mem_req_valid)$fatal(1,"early output or rejected valid event f=%0d j=%0d error=%h",f,j,encoder_error);
  end
  finish_frame();
 endtask
 task automatic wr(input integer a,input integer value);
  snes_addr=a;snes_data_in=value;romsel_n=1;#20;write_n=0;#180;write_n=1;#20;snes_addr=24'h123456;#100;
 endtask
 task automatic rd(input integer a,input integer want,input integer payload);
  snes_addr=a;romsel_n=payload?0:1;#20;read_n=0;#160;
  if(databus_oe_n || !databus_dir || bus_data!==want[7:0])$fatal(1,"read address%h got%h wanted%h frontend%h",a,bus_data,want,frontend_error);
  if(payload)begin bytes_read++;$fdisplay(fd,"B %0t %0d %0d",$time,a,bus_data);end
  #60;read_n=1;romsel_n=1;snes_addr=24'habcd00;
  #0.001;if(!databus_oe_n || databus_dir)$fatal(1,"raw release");#100;
 endtask
 task automatic consume(input integer seqnum,input integer base_addr,input integer length);
  integer n;
  wr(24'h6002,reset_epoch&255);wr(24'h6003,reset_epoch>>8);wr(24'h6004,seqnum&255);wr(24'h6005,seqnum>>8);wr(24'h6000,1);
  n=0;while(!ready && !fault && n<50000)begin #100;n++;if(!busy && !ready && !fault)begin acquire_retries++;wr(24'h6000,1);end end
  if(!ready || fault || producer_fault)$fatal(1,"acquire failed producer%h bus%h",producer_error,bus_error);
  rd(24'h6006,length&255,0);rd(24'h6007,length>>8,0);
  for(integer i=0;i<length;i++)rd(24'h408000+i,golden[(base_addr+i)%16384],1);
  rd(24'h6008,length&255,0);rd(24'h6009,length>>8,0);
  wr(24'h6000,2);n=0;while(busy && n<50000)begin #100;n++;end
  if(busy || fault || host_read_owned || frontend_error)$fatal(1,"commit");
 endtask

 task automatic failure(input integer code,input string name);
  repeat(5)@(negedge queue_clk);
  if(!encoder_fault || encoder_error!=code || desc_valid || mem_rsp_valid || published!=0)$fatal(1,"fault expected%h got%h published%0d",code,encoder_error,published);
  pass(name);
 endtask
 task automatic corrupt(input integer index,input integer mutation,input integer code,input string name);
  restart();start_frame(0);
  for(integer j=0;j<index;j++)event_at(j);
  event_at(index,mutation);failure(code,name);
 endtask
 initial begin
  fd=$fopen("encoder-trace.tsv","w");$readmemh("events.hex",events);$readmemh("golden.hex",golden);
  for(integer group_id=0;group_id<2;group_id++)begin
   restart();origin_cycle=cycles+40;origin_tick=events[group_id*4*16388][66:35];
   fork
    begin for(integer f=group_id*4;f<group_id*4+4;f++)stream_frame(f,1);end
    begin
     for(integer f=group_id*4;f<group_id*4+4;f++)begin
      while(published<f%4+1 && !encoder_fault && !producer_fault)@(negedge queue_clk);
      if(encoder_fault || producer_fault)$fatal(1,"producer pipeline fault");
      consume(f%4+1,f*2008,2008);
     end
    end
   join
   if(published!=4 || descriptors!=4 || encoder_fault || producer_fault)$fatal(1,"group accounting");
   pass(group_id==0?"four_banks32_frames_actual_fetch_spacing_exact":"four_fineX_frames_actual_fetch_spacing_exact");
  end
  restart();supported_mode=0;frame_start=1;@(negedge queue_clk);frame_start=0;failure(2,"unsupported_mode_before_start");
  restart();start_frame(0);supported_mode=0;failure(2,"midframe_mode_change");
  restart();start_frame(0);frame_start=1;@(negedge queue_clk);frame_start=0;failure(1,"overlapping_frame");
  corrupt(2,1,3,"missing_or_duplicate_fetch_cadence");
  corrupt(1,2,4,"nonmonotonic_tick");
  corrupt(64,3,5,"wrong_tile_row");
  corrupt(64,4,6,"unsupported_attribute_palette");
  corrupt(65,5,7,"in_cell_tile_change");
  corrupt(65,6,8,"mixed_CHR_window");
  restart();start_frame(4);for(integer j=0;j<64;j++)event_at(4*16388+j);event_at(4*16388+64,6);failure(5,"out_of_16KiB_CHR_range");
  restart();start_frame(0);for(integer j=0;j<10;j++)event_at(j);frame_end=1;@(negedge queue_clk);frame_end=0;failure(9,"incomplete_frame_not_published");
  restart();event_at(0);failure(11,"event_outside_frame");
  restart();stream_frame(0,0);frame_start=1;@(negedge queue_clk);frame_start=0;failure(1,"source_memory_held_until_done");
  restart();start_frame(0);for(integer j=0;j<100;j++)event_at(j);restart();
  fork stream_frame(0,0);begin while(published!=1 && !encoder_fault)@(negedge queue_clk);consume(1,0,2008);end join
  if(encoder_fault || producer_fault)$fatal(1,"reset recovery");pass("RESET_partial_frame_rebuild_exact");
  if(bytes_read!=18072)$fatal(1,"byte count");
  $display("PASS NCR1 ENCODER checks=%0d bytes=%0d",checks,bytes_read);$fclose(fd);$finish;
 end
 initial begin #200000000;$fatal(1,"watchdog");end
endmodule
