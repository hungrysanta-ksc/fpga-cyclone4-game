// SPDX-License-Identifier: MIT
// Exercise every source palette bit through the actual sequential copy path.
module palette181_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_packet=0,begin_packet=0,end_packet=0,ppu_ce=0,source_fault=0;
 reg [8:0] scanline=8,dot=0;reg [14:0] scroll_v=0,scroll_t=0;
 reg [2:0] fine_x=0,pattern_mode=0;reg [7:0] display_mask=8'h18;
 reg [191:0] palette=0;reg scroll_access=0,row_commit=0,row_patched=0;
 reg [7:0] committed_row=0;reg [2:0] row_slot=0;
 reg query=0,query_palette=0;reg [7:0] query_row=0;reg [4:0] query_bank=0,query_color=0;
 wire row_needs_patch,owned,valid,scroll_seen,response,hit;
 wire [7:0] errors,row_count;wire [5:0] palette_count;wire [55:0] data;
 nes_native_raster181 dut(.*);
 task step;begin @(negedge clk);end endtask
 integer p,c,checks=0,copies=0;
 reg [191:0] expected;
 task copy_row(input integer row);
 begin
  scanline=8+row;dot=1;ppu_ce=1;step();ppu_ce=0;dot=2;
  committed_row=row;row_commit=1;step();row_commit=0;
  repeat(33)step();
 end endtask
 task inspect(input integer bank);
 begin
  for(c=0;c<32;c=c+1)begin
   if(dut.colors[bank*32+c] !== {2'b0,expected[c*6+:6]})
    $fatal(1,"palette storage pattern=%0d bank=%0d color=%0d",p,bank,c);
   checks=checks+1;
  end
  copies=copies+1;
 end endtask
 initial begin
  step();step();reset=0;
  for(p=0;p<194;p=p+1)begin
   release_packet=1;step();release_packet=0;begin_packet=1;step();begin_packet=0;
   palette=0;
   if(p<192)palette[p]=1;else if(p==193)palette={192{1'b1}};
   expected=palette;copy_row(0);inspect(0);
   // Keep backdrop stable, invert the other 31 colors for bank1.
   palette[191:6]=~palette[191:6];expected=palette;copy_row(1);inspect(1);
   if(errors!=0 || palette_count!=2)$fatal(1,"palette state");
   // A third distinct palette must still set the original capacity error.
   palette[191:6]=0;palette[11:6]=6'h35;copy_row(2);
   if(!errors[2] || palette_count!=2)$fatal(1,"third palette guard");
   inspect(1);
  end
  $display("PASS PALETTEBITS181 patterns=194 checks=%0d inspections=%0d",checks,copies);
  $finish;
 end
endmodule
