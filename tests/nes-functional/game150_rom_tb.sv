`timescale 1ns/1ps
module game150_rom_tb;
 reg host_clk=0,reset=1;always #5.952 host_clk=~host_clk;
 reg [23:0] address=0;reg read_n=1,write_n=1,romsel_n=1;
 wire [7:0] data_out;wire oe_n,dir;
 nes_game_bus150 bus(.host_clk(host_clk),.reset(reset),.active(1'b1),.address(address),
 .read_n(read_n),.write_n(write_n),.romsel_n(romsel_n),.data_in(8'd0),.data_out(data_out),.oe_n(oe_n),.dir(dir),
 .frame_ready(1'b0),.frame_response(1'b0),.frame_data(8'd0),
 .frame_request(),.frame_address(),.release_frame(),.pad_commit(),.pad_buttons());
 reg [7:0] expected[0:2047];
 initial begin
  $readmemh("game-program.hex",expected);#100;reset=0;#100;
  read_n=0;romsel_n=0;
  for(integer i=0;i<32768;i=i+1)begin
   address=24'h008000+i;#70;
   if(oe_n || !dir || data_out!==expected[i%2048])$fatal(1,"program byte %h",address);
   #50;
  end
  // RAM, other banks, write and raw reset must not drive program data.
  address=24'h7e8000;#1;if(!oe_n || dir)$fatal(1,"WRAM ownership");
  address=24'h008000;write_n=0;#1;if(!oe_n || dir)$fatal(1,"write ownership");
  write_n=1;#100;reset=1;#1;if(!oe_n || dir)$fatal(1,"reset ownership");
  $display("PASS GAME150 ROM32768 compact mirrors/vectors/raw ownership");$finish;
 end
endmodule
