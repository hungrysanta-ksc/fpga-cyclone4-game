"""Publish an aligned direct DMA job instead of fetched bytes for canonical BG tiles."""
from nes_raw506 import once


def producer(s):
    s=once(s," wire zero_byte=", """ // This experimental CHR-ROM profile has a typed payload for BG.
 // Non-identity BG jobs fault before publishing a descriptor. OBJ and
 // the explicit blank-tile operation retain their original data format.
 wire simple_bg=kind==0 && rows==48'hfac688fac688 && alt_mask==0;
 wire [16:0] offset659={tag,4'b0};
 reg [7:0] descriptor659;
 always @* case(index[3:0])
  0:descriptor659=offset659[7:0]; 1:descriptor659=offset659[15:8];
  2:descriptor659={7'b0101000,offset659[16]}; 3:descriptor659=8'hd6;
  4:descriptor659=~offset659[7:0];5:descriptor659=~offset659[15:8];
  6:descriptor659=generation[7:0];7:descriptor659=generation[15:8];
  8:descriptor659=slot[7:0];9:descriptor659={6'b0,slot[9:8]};
  10:descriptor659=~generation[7:0];11:descriptor659=~generation[15:8];
  12:descriptor659=~slot[7:0];13:descriptor659=~{6'b0,slot[9:8]};
  14:descriptor659=~{7'b0101000,offset659[16]};15:descriptor659=8'h29;
 endcase
 wire zero_byte=""")
    # The 16 rows are two plane lanes per raster row.
    rows=sum((i//2)<<(3*i) for i in range(16))
    s=once(s,"48'hfac688fac688",f"48'h{rows:012x}")
    assert s.count("state==FETCH&&!zero_byte")==2; s=s.replace("state==FETCH&&!zero_byte","state==FETCH&&kind!=0&&!zero_byte")
    return once(s,"FETCH:if(zero_byte)", """FETCH:if(kind==0)begin
     if(!simple_bg)begin fault<=1;state<=IDLE;end
     else begin held_byte<=descriptor659;state<=EMIT;end
    end else if(zero_byte)""")
