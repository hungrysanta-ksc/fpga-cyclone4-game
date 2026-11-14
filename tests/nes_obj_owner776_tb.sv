// SPDX-License-Identifier: MIT
// Replay only the completed tile, control-bus and E8 interfaces of the fitted board.
`timescale 1ns/1ps
module nes_obj_owner776_tb;
  reg host=0, nes=0, reset=0, stop=0;
  always #5.952381 host=!host;
  always #23.28042 nes=!nes;
  reg pv=0, pt=0, tv=0, ev=0;
  reg [1:0] kind=0;
  reg [9:0] slot=0;
  reg [4:0] item=0;
  reg [5:0] length=0;
  reg [7:0] pixels=0, data=0;
  reg [23:0] address=0;
  reg read_n=1, write_n=1, ss=1, sck=0, mosi=0;
  wire permit, tile_ready, end_ready, ready, obj, ended, consume, error, ctrl_error, tile_error, spi_error;
  wire [31:0] token, consume_token;
  wire [11:0] bytes;
  wire [9:0] first_slot;
  wire [15:0] generation, sealed_generation;
  wire [7:0] read_data;
  wire miso, oe_n;
  nes_tile_bulk206 bulk(.nes_clk(nes),.host_clk(host),.reset(reset),.active(1'b1),.stop(stop),.source_fault(1'b0),
    .plan_valid(pv),.plan_taken(pt),.plan_kind(kind),.plan_slot(slot),.plan_generation(16'd969),.plan_permit(permit),
    .tile_valid(tv),.tile_ready(tile_ready),.tile_data(pixels),.tile_index(item),.tile_length(length),
    .tile_kind(kind),.tile_slot(slot),.tile_generation(16'd969),.end_valid(ev),.end_ready(end_ready),.end_generation(16'd969),
    .token_seed(32'd158),.chunk_ready(ready),.chunk_length(bytes),.chunk_token(token),
    .chunk_kind(obj),.chunk_slot(first_slot),.chunk_generation(generation),.consume(consume),.consume_token(consume_token),
    .consume_error(error),.address(address),.read_n(read_n),.write_n(write_n),.data_out(read_data),.oe_n(oe_n),
    .fault(tile_error),.end_sealed(ended),.sealed_generation(sealed_generation));
  nes_bulk_control194 control_port(.clk(host),.reset(reset),.active(1'b1),.stop(stop),.fault(tile_error),
    .chunk_ready(ready),.chunk_kind(obj),.chunk_length(bytes),.chunk_slot(first_slot),.chunk_generation(generation),
    .chunk_token(token),.address(address),.read_n(read_n),.write_n(write_n),.data_in(data),
    .consume(consume),.consume_token(consume_token),.command_error(ctrl_error));
  nes_plan_spi200 spi(.clk(host),.reset(reset),.enable(1'b1),.stop(stop),.source_fault(tile_error),
    .SPI_SS(ss),.SPI_SCK(sck),.SPI_MOSI(mosi),.miso(miso),.fault(spi_error),.plan_idle(1'b1),.plan_ready(1'b1),
    .retire_done(1'b0),.end_generation(sealed_generation),.end_sealed(ended),.chunk_ready(ready),.chunk_kind(obj),
    .chunk_length(bytes),.chunk_slot(first_slot),.chunk_generation(generation),.chunk_token(token),.host_first(7'd0),.nes_first(8'd0));

  integer tile_at[0:4], release_at[0:3], poll_at[0:63], expected[0:63];
  integer octets[0:143];
  integer count, fd, i, j, n;
  string fixture;
  realtime origin, last_sealed, last_head;
  always @(posedge bulk.aperture.sealed[1])
    if(bulk.aperture.tokens[1]==161) last_sealed=$realtime-origin;
  always @(posedge host) if(ready && token==161 && last_head==0) last_head=$realtime-origin;
  task automatic at_time(input integer ns);
    realtime delay_ns;
    delay_ns=origin+ns-$realtime;
    if(delay_ns < -1) $fatal(1,"stimulus missed by %f ns", -delay_ns);
    if(delay_ns > 0) #(delay_ns);
  endtask
  task automatic send_tile(input integer k,input integer dest,input integer start_byte,input integer size);
    @(negedge nes); kind=k==0?2:1; slot=dest; length=size; pv=1;
    do @(negedge nes); while(!permit);
    pt=1; @(negedge nes); pt=0;pv=0;
    if($realtime<origin+tile_at[k]) at_time(tile_at[k]);
    for(int b=0;b<size;b++)begin
      @(negedge nes); while(!tile_ready) @(negedge nes);
      tv=1; item=b; pixels=octets[start_byte+b];
      @(posedge nes); #1; tv=0;
    end
  endtask
  task automatic wr(input integer a,input integer d);
    @(negedge host); address=a;data=d;write_n=0;
    repeat(5) @(negedge host);write_n=1;
    repeat(6) @(negedge host);
  endtask
  task automatic check_release(input integer k,input integer start_byte,input integer size);
    at_time(release_at[k]-24000);
    if(!ready || token!=158+k || bytes!=size || generation!=969) $fatal(1,"wrong head at release %d",k);
    for(int b=0;b<size;b++)begin
      @(negedge host);address='h400800+b;read_n=0;repeat(5) @(negedge host);
      if(oe_n!==1'b0 || read_data!==octets[start_byte+b][7:0]) $fatal(1,"payload %d %d",k,b);
    end
    read_n=1;
    for(int b=0;b<4;b++) wr('h604c+b,(158+k)>>(8*b));
    at_time(release_at[k]);wr('h6050,'ha5);
    if(error||ctrl_error||ready && token==158+k) $fatal(1,"release failed");
  endtask
  task automatic query(input integer index);
    reg [7:0] reply[0:19];
    reg [7:0] c;
    integer seen;
    at_time(poll_at[index]); ss=0;
    for(int b=0;b<20;b++)begin
      reply[b]=0;
      for(int bitno=7;bitno>=0;bitno--)begin
        mosi=b==0 && ((8'he8>>bitno)&1);
        #190.476; sck=1; reply[b][bitno]=miso; #190.476;sck=0;
      end
    end
    #120;ss=1;#100;
    seen=reply[6]?{reply[17],reply[16],reply[15],reply[14]}:-1;
    c=0;
    for(int b=1;b<19;b++)begin
      c=c^reply[b];for(int h=0;h<8;h++) c=c[7]?(c<<1)^7:c<<1;
    end
    if($isunknown({reply[6],reply[17],reply[16],reply[15],reply[14],c}) ||
       seen!==expected[index] || reply[1]!==8'hd7 || reply[2]!==8'd4 || reply[19]!==c || spi_error)
      $fatal(1,"E8 %d expected %d got %d",index,expected[index],seen);
    if(seen==161 && ({reply[13],reply[12],reply[11],reply[10],reply[9],reply[8],reply[7]}!==
                           {16'd969,16'd256,16'd32,8'd1})) $fatal(1,"final descriptor");
  endtask
  initial begin
    if(!$value$plusargs("fixture=%s",fixture)) $fatal;
    fd=$fopen(fixture,"r");if(!fd)$fatal;
    for(i=0;i<5;i++) if($fscanf(fd,"%d",tile_at[i])!=1)$fatal;
    for(i=0;i<4;i++) if($fscanf(fd,"%d",release_at[i])!=1)$fatal;
    for(i=0;i<144;i++) if($fscanf(fd,"%d",octets[i])!=1)$fatal;
    if($fscanf(fd,"%d",count)!=1 || count>64 || count<2)$fatal;
    for(i=0;i<count;i++) if($fscanf(fd,"%d %d",poll_at[i],expected[i])!=2)$fatal;
    $fclose(fd);
    #1;reset=1;#200;reset=0;#500;origin=$realtime;last_head=0;
    fork
      begin
        send_tile(0,0,0,16);send_tile(1,2,16,32);send_tile(2,4,48,32);
        send_tile(3,5,80,32);send_tile(4,8,112,32);
        @(negedge nes);while(!end_ready) @(negedge nes);ev=1;@(negedge nes);ev=0;
      end
      begin
        check_release(0,0,16);check_release(1,16,32);
        check_release(2,48,64);check_release(3,112,32);
      end
      begin for(int k=0;k<count;k++) query(k); end
    join
    if(tile_error||error||spi_error||last_sealed<=0||last_sealed>=release_at[2]||
       last_head<release_at[2]||last_head>release_at[2]+200) $fatal(1,"FIFO visibility");
    $display("OWNER776 sealed_ns=%0.0f head_ns=%0.0f release_ns=%0d",last_sealed,last_head,release_at[2]);
    stop=1;#1;if(ready||!oe_n)$fatal(1,"STOP left ownership");
    $display("PASS776");$finish;
  end
  initial if($test$plusargs("stop_while_sealed"))begin
    wait(bulk.aperture.sealed==2'b11 && token==160 &&
         bulk.aperture.tokens[!bulk.aperture.reader]==161);
    @(negedge host);stop=1;#1;
    if(ready!==0 || oe_n!==1) $fatal(1,"STOP exposed pending head");
    repeat(20) @(negedge host);stop=0;
    repeat(20) @(negedge host);
    if(ready!==0 || consume || ended || bulk.aperture.sealed!=0 || spi.ended)
      $fatal(1,"old owner survived restart");
    $display("PASS776_STOP");$finish;
  end
  initial #50000000 $fatal(1,"timeout");
endmodule
