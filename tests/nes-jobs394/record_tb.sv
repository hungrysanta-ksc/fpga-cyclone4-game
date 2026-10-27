`timescale 1ns/1ps
module record_tb;
 parameter integer GUARD=0;
 reg host_clk=0,nes_clk=0;always #5 host_clk=~host_clk;always #23.2805 nes_clk=~nes_clk;
 reg reset=1,cancel=0,identity_valid=0;reg [31:0] serial=0;reg [15:0] generation=0;reg bank=0;reg [2:0] raw278=0;
 reg ss=1,sck=0,mosi=0;wire miso,selected,queue_admit319;wire [113:0] link270;wire [199:0] status270;
 reg [23:0] address=0;reg read_n=1,write_n=1;reg [7:0] data_in=0;wire [7:0] data_out;wire bus_valid;
 reg tile_valid=0,end_valid=0,end_partial295=0;wire tile_ready,end_ready;reg [7:0] tile_data=0;reg [4:0] tile_index=0;reg [5:0] tile_length=16;reg [1:0] tile_kind=0;reg [9:0] tile_slot=0;
 wire identity_ready,grant278,host_ack278,init278,ready359,private359,context_valid,context_ready,begin_valid,begin_bank,range_ready,sealed,ordinary_finish,jobs_committed336,display_request,display_request_ready,display_response_valid,display_response_ready,staged,display_ack,retired,flow_fault;
 wire [33:0] read359;wire [31:0] grant_epoch278,grant_serial278;wire [15:0] grant_generation278;wire [2:0] grant_raw278,begin_raw;
 wire [7:0] context_data,expected_data332,display_response;wire [8:0] expected_addr332;wire [3:0] checker_fault;
 nes_output260 flow(.nes_clk(nes_clk),.host_clk(host_clk),.reset(reset),.cancel(cancel||checker_fault!=0),.identity_valid(identity_valid),.identity_ready(identity_ready),.serial(serial),.generation(generation),.bank(bank),.epoch278(32'd1),.raw278(raw278),
  .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(miso),.selected(selected),.queue_admit319(queue_admit319),.link270(link270),.status270(status270),
  .address(address),.read_n(read_n),.write_n(write_n),.data_in(data_in),.data_out(data_out),.bus_valid(bus_valid),
  .tile_valid(tile_valid),.tile_ready(tile_ready),.tile_data(tile_data),.tile_index(tile_index),.tile_length(tile_length),.tile_kind(tile_kind),.tile_slot(tile_slot),.tile_generation(generation),
  .end_valid(end_valid),.end_partial295(end_partial295),.end_ready(end_ready),.end_generation(generation),
  .grant278(grant278),.grant_epoch278(grant_epoch278),.grant_serial278(grant_serial278),.grant_generation278(grant_generation278),.grant_raw278(grant_raw278),.host_ack278(host_ack278),.init278(init278),
  .read359(read359),.ready359(ready359),.private359(private359),.expected_data332(expected_data332),.expected_addr332(expected_addr332),
  .context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),.begin_valid(begin_valid),.begin_bank(begin_bank),.begin_raw(begin_raw),
  .range_ready(range_ready),.sealed(sealed),.ordinary_finish(ordinary_finish),.jobs_committed336(jobs_committed336),.core_idle(1'b1),
  .display_request(display_request),.display_request_ready(display_request_ready),.display_response_valid(display_response_valid),.display_response_ready(display_response_ready),.display_response(display_response),
  .staged(staged),.display_ack(display_ack),.retired(retired),.fault(flow_fault),
  .ctx_q375(8'd0),.crc_done278(1'b0),.crc_index278(4'd0),.manifest_at282(9'd0),.manifest_started282(1'b0),.exec_busy298(1'b0),.exec_done298(1'b0),.exec_addr298(8'd0),.ordinary_stream_ready(1'b1),.ordinary_hash_ready(1'b1));
 nes_spi270 spi(.clk(host_clk),.reset(reset||cancel),.SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.source_status(200'd0),.output_status(status270),.plan_status(200'd0),.request_crc_enable(1'b0),.queue_admit319(queue_admit319),.plan_admit319(1'b0),.link(link270));
 wire [9:0] ram_addr;wire ram_we;wire [7:0] ram_w;reg [7:0] ram_q;reg [7:0] memory[0:1023];
 always @(posedge host_clk)begin ram_q<=memory[ram_addr];if(ram_we)memory[ram_addr]<=ram_w;end
 nes_validator278 validation394(.read359(read359),.ready359(ready359),.private359(private359),.expected_data332(expected_data332),.expected_addr332(expected_addr332),
  .exec_start298(1'b0),.exec_kind298(2'd0),.exec_op298(4'd0),.exec_length298(9'd0),.exec_data298(8'd0),
  .crc_reset287(flow.crc_reset287),.v_descriptor287(1'b0),.clk(host_clk),.reset(reset),.abort_source(cancel||flow_fault),.grant278(grant278),.grant_epoch278(grant_epoch278),.grant_serial278(grant_serial278),.grant_generation278(grant_generation278),.grant_raw278(grant_raw278),.host_ack278(host_ack278),.init278(init278),
  .ram_q(ram_q),.ram_addr(ram_addr),.ram_we(ram_we),.ram_w(ram_w),.display_write(1'b0),.display_request(display_request),.display_request_ready(display_request_ready),.display_response_valid(display_response_valid),.display_response_ready(display_response_ready),.display_response(display_response),
  .v_begin_valid(begin_valid),.v_target_bank(begin_bank),.v_raw_count(begin_raw),.v_range_valid(1'b0),.v_map_range(1'b0),.v_first(12'd0),.v_count(12'd1),.v_check_valid(1'b0),.v_check_value(8'd0),.v_finish_valid(ordinary_finish),.v_all_consumed(jobs_committed336),
  .h_start(1'b0),.h_kind(2'd0),.h_index(4'd0),.legacy_h_valid(1'b0),.legacy_h_data(8'd0),.context_valid(context_valid),.context_data(context_data),.context_ready(context_ready),.v_ready(range_ready),.v_sealed(sealed),.fault(checker_fault));
 reg [7:0] packets[0:32767],expected[0:32767],descriptor[0:8191],view[0:11];reg [15:0] sizes[0:1023],lengths[0:1023];reg [23:0] tile_info[0:255];reg [7:0] tile_payload[0:32767];
 integer frame_id,source_at,source_index,stored,expected_at,tile_at,byte_at,first_map394,total_frames=0,total_bytes=0,max_credit=0,events=0;
 reg active=0,feeding=0,frame_finished=0;reg [7:0] b;reg [31:0] token;reg [7:0] actual_record[0:16];
 always @(posedge host_clk)if(!reset&&!cancel)begin
  if(flow.queue.used>2)$fatal(1,"two slots exceeded");
  if(flow.queue.used>max_credit)max_credit=flow.queue.used;
  if($isunknown({validation394.checksum,validation394.digest,checker_fault}))$fatal(1,"unknown CRC/checker state");
  if((flow_fault||checker_fault)&&GUARD==0)$fatal(1,"frame%0d flow%0d checker%0d state%0d op%h at%0d addr%0d checkerstate%0d bit%0d",frame_id,flow_fault,checker_fault,flow.state,flow.op,flow.at,flow.parser_address,validation394.state,validation394.v_bit_at);
  if(read359[33])events++;
 end
 task rd(input [23:0] a,output reg [7:0] v);begin @(negedge host_clk);address=a;read_n=0;#200;if(!bus_valid)begin if(GUARD&&(checker_fault||flow_fault))wait(1'b0);else $fatal(1,"invalid bus %h",a);end v=data_out;read_n=1;#200;end endtask
 task wr(input [23:0] a,input [7:0] v);begin @(negedge host_clk);address=a;data_in=v;write_n=0;#200;write_n=1;#200;end endtask
 task transfer(input integer offset,n);begin
  wait(queue_admit319);#2000;ss=0;#2000;
  for(integer j=0;j<n;j++)for(integer bitn=7;bitn>=0;bitn--)begin mosi=packets[offset+j][bitn];#190.476190476;sck=1;#190.476190476;sck=0;end
  #2000;ss=1;#2000;
 end endtask
 task send_end(input reg partial);begin
  @(negedge nes_clk);end_partial295=partial;end_valid=1;do @(posedge nes_clk);while(!end_ready);@(negedge nes_clk);end_valid=0;
 end endtask
 initial begin : tile_producer
  forever begin
   wait(feeding);tile_at=0;
   for(integer job=0;job<tile_info[0];job++)begin
    tile_kind=tile_info[job+1][1:0];tile_slot=tile_info[job+1][11:2];
    for(integer tile=0;tile<tile_info[job+1][23:12];tile++)begin
     tile_length=tile_kind==1?32:16;
     for(integer lane=0;lane<tile_length;lane++)begin
      @(negedge nes_clk);tile_valid=1;tile_index=lane;tile_data=tile_payload[tile_at];
      do @(posedge nes_clk);while(!tile_ready);tile_at++;
     end
     @(negedge nes_clk);tile_valid=0;tile_slot++;
    end
    if(job+1<tile_info[0]&&tile_info[job+1][1:0]==0&&tile_info[job+2][1:0]==1)send_end(1);
   end
   send_end(0);feeding=0;wait(!active);
  end
 end
 initial begin : consumer
  forever begin
   @(negedge host_clk);
   if(active&&staged)begin
    if(GUARD==17)begin wr(24'h00606f,8'hee);wait(1'b0);end
    if(GUARD==4)begin wr(24'h006058,8'h5a);wait(1'b0);end
    for(integer j=0;j<17;j++)begin rd(24'h006080+j,actual_record[j]);if(actual_record[j]!==descriptor[stored*17+j])$fatal(1,"record mismatch f%0d job%0d field%0d got%h expected%h",frame_id,stored,j,actual_record[j],descriptor[stored*17+j]);end
    for(integer j=0;j<lengths[stored+1]-(GUARD==1?1:0);j++)begin
     rd(24'h400800+j,b);if(b!==expected[expected_at+j])$fatal(1,"payload mismatch f%0d job%0d byte%0d",frame_id,stored,j);
     if(GUARD==2&&j==0)begin rd(24'h400800,b);wait(1'b0);end
     if(GUARD==5&&j==lengths[stored+1]/2)begin cancel=1;wait(1'b0);end
    end
    for(integer j=0;j<4;j++)begin rd(24'h006048+j,b);token[j*8+:8]=b;end
    if(GUARD==3)token++;
    for(integer j=0;j<4;j++)wr(24'h00604c+j,token[j*8+:8]);wr(24'h006050,8'ha5);
    wait(!staged);expected_at+=lengths[stored+1];total_bytes+=lengths[stored+1];stored++;
   end else if(active&&sealed&&flow.state==flow.DVIEW)begin
    if(stored!=lengths[0])$fatal(1,"early seal jobs%0d expected%0d",stored,lengths[0]);
    for(integer j=0;j<12;j++)begin wait(flow.state==flow.DVIEW);rd(24'h006070+j,b);if(b!==view[j])$fatal(1,"view mismatch");end
    if(GUARD==6)begin cancel=1;wr(24'h006058,8'h5a);wait(1'b0);end
    for(integer j=0;j<4;j++)begin rd(24'h006048+j,b);token[j*8+:8]=b;end
    for(integer j=0;j<4;j++)wr(24'h00604c+j,token[j*8+:8]);wr(24'h006058,8'h5a);wait(!sealed);frame_finished=1;
   end
  end
 end
 initial begin
  repeat(4)@(negedge host_clk);reset=0;wait(init278);wr(24'h006006,8'ha5);
  for(frame_id=905;frame_id<=916;frame_id++)begin
   $readmemh($sformatf("packet%0d.hex",frame_id),packets);$readmemh($sformatf("sizes%0d.hex",frame_id),sizes);
   $readmemh($sformatf("data%0d.hex",frame_id),expected);$readmemh($sformatf("desc%0d.hex",frame_id),descriptor);$readmemh($sformatf("length%0d.hex",frame_id),lengths);
   $readmemh($sformatf("tile%0d.hex",frame_id),tile_payload);$readmemh($sformatf("tileinfo%0d.hex",frame_id),tile_info);$readmemh($sformatf("view%0d.hex",frame_id),view);
   first_map394=0;while(first_map394<lengths[0]&&descriptor[first_map394*17+9]!=2)first_map394++;
   serial=frame_id-904;generation=frame_id-904;bank=~serial[0];raw278=packets[1+10+20];
   @(negedge nes_clk);identity_valid=1;do @(posedge nes_clk);while(!identity_ready);@(negedge nes_clk);identity_valid=0;wait(flow.have_identity&&flow.identity[31:0]==serial);
   active=1;feeding=1;frame_finished=0;stored=0;expected_at=0;source_at=0;
   for(source_index=0;source_index<sizes[0];source_index++)begin transfer(source_at,sizes[source_index+1]);source_at+=sizes[source_index+1];end
   wait(frame_finished);wait(!feeding);wait(retired);active=0;total_frames++;repeat(20)@(negedge nes_clk);
   $display("FRAME394 %0d jobs%0d bytes%0d",frame_id,stored,expected_at);
  end
  $display("PASS RECORD394 frames=%0d bytes=%0d actual_reads=%0d max_credit=%0d",total_frames,total_bytes,events,max_credit);$finish;
 end
 initial begin : guard_result
  reg [7:0] before_ram[0:1023],before_queue[0:1023],before_aperture[0:4095];reg [3:0] observed;reg observed_flow;
  if(GUARD)begin
   wait(flow_fault||checker_fault||cancel);observed=checker_fault;observed_flow=flow_fault;
   if(GUARD==11&&observed!=2)$fatal(1,"duplicate not rejected by independent checker");
   if(GUARD==13&&observed!=3)$fatal(1,"exact bitmap mismatch not rejected independently");
   if(GUARD!=5&&GUARD!=6&&GUARD!=11&&GUARD!=13&&!observed_flow)$fatal(1,"expected transport/host rejection");
   if(GUARD==14&&stored!=0)$fatal(1,"trailing bytes were exposed");
   if(GUARD==15&&stored!=first_map394)$fatal(1,"odd map fragment was exposed");
   if(GUARD==16&&flow.allocation!=1)$fatal(1,"wrapped span reached allocation/tile execution");
   repeat(4)@(negedge host_clk);
   for(integer i=0;i<1024;i++)begin before_ram[i]=memory[i];before_queue[i]=flow.queue.buffer[i];end
   for(integer i=0;i<4096;i++)before_aperture[i]=flow.aperture.storage[i];
   repeat(256)begin
    @(negedge host_clk);if(sealed||display_ack||retired||identity_ready)$fatal(1,"authority after fault/STOP");
    for(integer i=0;i<1024;i++)if(memory[i]!==before_ram[i]||flow.queue.buffer[i]!==before_queue[i])$fatal(1,"RAM write after fault/STOP");
    for(integer i=0;i<4096;i++)if(flow.aperture.storage[i]!==before_aperture[i])$fatal(1,"staging write after fault/STOP");
   end
   if((GUARD==5||GUARD==6)&&flow.allocation<=1)$fatal(1,"STOP recycled token namespace");
   $display("PASS GUARD394 case=%0d independent=%0d host=%0d freeze=256",GUARD,observed,observed_flow);$finish;
  end
 end
 initial begin #500000000;$fatal(1,"record watchdog f%0d state%0d op%h at%0d produced%0d tilebytes%0d checker%0d stored%0d",frame_id,flow.state,flow.op,flow.at,flow.produced,flow.tile_bytes,validation394.state,stored);end
endmodule
