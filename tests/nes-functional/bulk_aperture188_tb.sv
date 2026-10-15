// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module bulk_aperture188_tb;
 parameter real PHASE=0;
 reg clk=0,clock_running=1;always #5.952 if(clock_running)clk=!clk;
 reg reset=1,active=1,stop=0,begin_valid=0,byte_valid=0,seal=0,cancel=0,consume=0;
 reg [11:0] begin_length=0;
 reg [31:0] begin_token=0,consume_token=0;
 reg [7:0] byte_data=0;
 reg [23:0] address=0;reg read_n=1,write_n=1;
 wire begin_ready,byte_ready,producer_error,consume_error,chunk_ready,oe_n,dir;
 wire [11:0] chunk_length;wire [31:0] chunk_token;wire [7:0] data_out;
 nes_bulk_aperture188 dut(.*);
 // Unchanged deployed ROM/control/packet decoder shares these raw pins.
 wire [7:0] old_data;wire old_oe,old_dir;
 nes_sink_bus165 old_bus(.clk(clk),.reset(reset),.active(active),.stop(stop),.fault(1'b0),
  .address(address),.read_n(read_n),.write_n(write_n),.romsel_n(!address[15]),.data_in(8'd0),
  .data_out(old_data),.oe_n(old_oe),.dir(old_dir),.packet_ready(1'b1),.packet_length(9'd1),
  .packet_data(8'h6d),.packet_address(),.ack_write(),.ack_index(),.ack_byte(),.ack_publish(),
  .pad_commit(),.pad_buttons());
 always @(negedge clk)if(!reset&&active)
  demand(oe_n||old_oe,"only one SNES bus owner");
 reg [7:0] payload[0:65535];
 integer nbytes,blocks,reads=0,checks=0,stream_len,stream_token,stream_first;
 integer fd,code,at,i,j;
 string file_name;
 task tick;begin @(posedge clk);#1;end endtask
 task demand(input bit ok,input string why);begin
  checks=checks+1;if(!ok)$fatal(1,"check %0d: %s",checks,why);
 end endtask
 task start_chunk(input integer len,input integer token);begin
  @(negedge clk);demand(begin_ready,"producer begins in free slot");
  begin_valid=1;begin_length=len;begin_token=token;tick();
  @(negedge clk);begin_valid=0;
 end endtask
 task put(input integer value);begin
  demand(byte_ready,"byte acceptance");byte_valid=1;byte_data=value;tick();
  @(negedge clk);byte_valid=0;
 end endtask
 task publish;begin seal=1;tick();@(negedge clk);seal=0;end endtask
 task release_chunk(input integer token,input bit good);begin
  consume_token=token;consume=1;tick();
  demand(consume_error==!good,"consume token validation");
  @(negedge clk);consume=0;
 end endtask
 task read_byte(input integer offset,input integer expected);begin
  // /RD stays asserted across address changes: continuous DMA-style bus.
  #PHASE;address=24'h400800+offset;read_n=0;write_n=1;
  repeat(4)tick();
  demand(!oe_n&&dir&&data_out==expected[7:0],"address qualified byte");reads=reads+1;
  @(negedge clk);
 end endtask
 task no_drive(input integer addr);begin
  address=addr;read_n=0;repeat(4)tick();demand(oe_n,"unmapped/unpublished read");@(negedge clk);
 end endtask
 initial begin
  repeat(3)tick();@(negedge clk);reset=0;
  no_drive('h400800);
  start_chunk(0,1);demand(producer_error,"zero length rejected");
  start_chunk(2049,1);demand(producer_error,"oversize rejected");
  start_chunk(4,2);put(1);publish();demand(producer_error&&!chunk_ready,"partial seal rejected");
  start_chunk(4,3);put(2);cancel=1;tick();@(negedge clk);cancel=0;demand(!chunk_ready,"cancel hidden");
  start_chunk(4,4);for(i=0;i<4;i=i+1)put(8'h20+i);
  no_drive('h400800);publish();demand(chunk_ready&&chunk_length==4&&chunk_token==4,"seal descriptor");
  start_chunk(4,5);for(i=0;i<4;i=i+1)begin
   put(8'h80+i);read_byte(i,8'h20+i);
  end
  publish();demand(!begin_ready,"two slots apply backpressure");
  release_chunk(999,0);read_byte(0,'h20);
  no_drive('h400804);no_drive('h400000);no_drive('h401800);
  release_chunk(4,1);read_byte(0,'h80);
  release_chunk(4,0);read_byte(3,'h83);release_chunk(5,1);no_drive('h400800);
  no_drive('h400000);demand(!old_oe&&old_data=='h6d,"existing packet window preserved");
  no_drive('h006000);demand(!old_oe&&old_data==1,"existing control preserved");
  no_drive('h008000);demand(!old_oe&&old_data===old_bus.program_rom[0],"existing ROM preserved");

  // Actual archived C request bytes, chunked independently of packet boundaries.
  // Data enters via local producer, not an MCU/SPI adapter. No ROM in this test.
  fd=$fopen("streams.txt","r");demand(fd!=0,"fixture inventory");
  code=$fscanf(fd,"%d\n",blocks);
  for(j=0;j<blocks;j=j+1)begin
   code=$fscanf(fd,"%s %d %d\n",file_name,nbytes,stream_token);
   demand(code==3,"fixture descriptor");$readmemh(file_name,payload,0,nbytes-1);
   at=0;
   while(at<nbytes)begin
    stream_len=(nbytes-at>2048)?2048:nbytes-at;
    start_chunk(stream_len,stream_token+at);
    for(i=0;i<stream_len;i=i+1)put(payload[at+i]);
    publish();demand(chunk_ready&&chunk_length==stream_len,"fixture published");
    for(i=0;i<stream_len;i=i+1)read_byte(i,payload[at+i]);
    release_chunk(stream_token+at,1);at=at+stream_len;
   end
  end
  $fclose(fd);
  // Reset/STOP must cancel output without waiting for the next local edge.
  start_chunk(1,100000);put('h55);publish();read_byte(0,'h55);
  #1;stop=1;#1;demand(oe_n,"STOP gates raw read immediately");tick();
  @(negedge clk);stop=0;no_drive('h400800);release_chunk(100000,0);
  start_chunk(1,100001);put('haa);publish();read_byte(0,'haa);
  #1;reset=1;#1;demand(oe_n,"reset gates raw read immediately");tick();
  @(negedge clk);reset=0;no_drive('h400800);
  start_chunk(1,100002);put('h33);publish();read_byte(0,'h33);
  write_n=0;#1;demand(oe_n,"write never drives candidate read aperture");write_n=1;
  read_n=1;#1;demand(oe_n,"read end releases immediately");read_n=0;
  @(negedge clk);clock_running=0;
  active=0;#1;demand(oe_n,"disable releases immediately with stopped clock");
  #10;active=1;#30;demand(oe_n&&!chunk_ready,"old chunk cannot reappear before clock release");
  clock_running=1;no_drive('h400800);
  $display("PASS BULK188 checks=%0d reads=%0d streams=%0d",checks,reads,blocks);$finish;
 end
 initial begin #10000000;$fatal(1,"test timeout");end
endmodule
