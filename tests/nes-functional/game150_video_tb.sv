`timescale 1ns/1ps
module game150_video_tb;
 reg nes_clk=0,host_clk=0,reset=1;
 always #23.28 nes_clk=~nes_clk;
 always #5.952 host_clk=~host_clk;
 reg [8:0] cycle=0,scanline=0;reg [5:0] color=0;
 reg [23:0] address=0;reg read_n=1,write_n=1,romsel_n=1;reg [7:0] data_in=0;
 wire [7:0] data_out,frame_data;wire oe_n,dir,ready,response,request,release_frame,pad_commit;
 wire [15:0] byte_address,pad_buttons;
 nes_game_frame150 frame(.nes_clk(nes_clk),.host_clk(host_clk),.reset(reset),
 .cycle(cycle),.scanline(scanline),.color(color),.release_frame(release_frame),.ready(ready),
 .request(request),.byte_address(byte_address),.response(response),.data(frame_data));
 nes_game_bus150 bus(.host_clk(host_clk),.reset(reset),.active(1'b1),
 .address(address),.read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(data_in),
 .data_out(data_out),.oe_n(oe_n),.dir(dir),.frame_ready(ready),.frame_response(response),.frame_data(frame_data),
 .frame_request(request),.frame_address(byte_address),.release_frame(release_frame),.pad_commit(pad_commit),.pad_buttons(pad_buttons));
 reg strobe=0,read_clock=0;wire serial,host_ready;
 nes_game_pad150 pad(.host_clk(host_clk),.nes_clk(nes_clk),.reset(reset),.commit(pad_commit),
 .snes_buttons(pad_buttons),.host_ready(host_ready),.strobe(strobe),.read_clock(read_clock),.serial(serial));
 reg [8:0] pixels[0:61439];reg [7:0] expected[0:57343];
 integer checks=0;
 task capture(input integer corrupt);
  for(integer y=0;y<240;y=y+1)begin
   for(integer x=0;x<256;x=x+1)begin
    @(negedge nes_clk);cycle=x+2;scanline=y;color=pixels[y*256+x][5:0] ^ (corrupt?6'h3f:0);
    repeat(2)@(negedge nes_clk);
   end
  end
  @(negedge nes_clk);cycle=0;scanline=250;
 endtask
 task write_control(input [15:0] a,input [7:0] d);
  address={8'd0,a};data_in=d;read_n=1;write_n=0;#350;write_n=1;#150;
 endtask
 task read_frame;
  // READ remains asserted as the DMA address changes. Sample at270ns.
  read_n=0;write_n=1;romsel_n=1;
  for(integer j=0;j<57344;j=j+1)begin
   address={8'h40,(16'h8000+j[15:0])};#270;
   if(oe_n || !dir || data_out!==expected[j])$fatal(1,"PIXEL150 byte=%0d got=%h expected=%h oe=%b",j,data_out,expected[j],oe_n);
   checks=checks+1;#102;
  end
  read_n=1;#1;if(!oe_n)$fatal(1,"raw READ cancel");#100;
 endtask
 initial begin
  $readmemh("pixels.hex",pixels);$readmemh("expected.hex",expected);
  #200;reset=0;
  capture(0);#500;if(!ready)$fatal(1,"no publication");
  fork capture(1);read_frame();join
  // A second producer frame could not mutate the frozen snapshot.
  address=24'h408000;read_n=0;#270;
  if(oe_n || data_out!==expected[0])$fatal(1,"snapshot overwritten");read_n=1;
  for(integer b=0;b<8;b=b+1)begin:buttons
   reg [15:0] bits;
   case(b)0:bits=16'h0080;1:bits=16'h8000;2:bits=16'h2000;3:bits=16'h1000;
          4:bits=16'h0800;5:bits=16'h0400;6:bits=16'h0200;7:bits=16'h0100;endcase
   write_control(16'h6002,bits[7:0]);write_control(16'h6003,bits[15:8]);#500;
   strobe=1;#200;strobe=0;
   for(integer k=0;k<10;k=k+1)begin
    #100;if(serial!==(k==b || k>=8))$fatal(1,"pad150 button=%0d bit=%0d serial=%b",b,k,serial);
    read_clock=1;#150;
    if(serial!==(k==b || k>=8))$fatal(1,"shift before CPU samples");
    read_clock=0;#150;checks=checks+1;
   end
  end
  write_control(16'h6000,8'ha5);#500;if(ready)$fatal(1,"release failed");
  capture(0);#500;if(!ready)$fatal(1,"recapture failed");
  address=24'h405fff;read_n=0;#270;
  if(oe_n || data_out!==expected[57343])$fatal(1,"last recaptured byte");
  reset=1;#1;if(!oe_n)$fatal(1,"raw reset did not isolate");#500;
  reset=0;#500;if(ready)$fatal(1,"reset retained stale frame");
  $display("PASS GAME150 pixels=57344 pad=80 frozen_capture/release/recapture/reset checks=%0d",checks);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
