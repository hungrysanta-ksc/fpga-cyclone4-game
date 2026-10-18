# SPDX-License-Identifier: MIT
"""Read-only observer of240 row decisions and accepted shift/raster bytes."""
from nes_operand243 import LAYOUT,FIELDS


def observe(source):
    fields=[]
    for n,addresses in LAYOUT.items():
        width=8*len(addresses)
        fields.append(('{'+str(width-FIELDS[n])+"'b0,"+n+'}') if FIELDS[n]<width else n)
    packed='{'+','.join(reversed(fields))+'}'
    observer=r'''
 integer rr_fd,rr_kind=-1,rr_seen[0:4],rr_i,rr_size,rr_bytes,rr_arg,rr_result,rr_pick;
 reg [191:0] rr_pre,rr_post;reg [527:0] rr_o,rr_n;reg [63:0] rr_m,rr_m1;
 reg [103:0] rr_packet;
 initial begin rr_fd=$fopen("rows-observed.txt","w");for(rr_i=0;rr_i<5;rr_i=rr_i+1)rr_seen[rr_i]=0;end
 task automatic rr_dump;begin
  rr_post=PACKED;
  for(rr_i=0;rr_i<8;rr_i=rr_i+1)rr_m1[rr_i*8+:8]=scratch[96+rr_i];
  $fwrite(rr_fd,"%0d %0d %0d %048x %048x %0132x %0132x %016x %016x %0d %026x\n",
   rr_kind,rr_arg,rr_result,rr_pre,rr_post,rr_o,rr_n,rr_m,rr_m1,rr_size,rr_packet);
  $fflush(rr_fd);rr_kind=-1;
 end endtask
 always @(posedge clk)begin
  if(reset||abort_source||fault||!lease_ok)rr_kind=-1;
  else begin
   rr_pick=-1;
   if(rr_kind<0)begin
    if(state==ROWREAD&&row_i==0)rr_pick=0;
    if(state==MASKREAD&&row_i==0&&rows!=0)rr_pick=1;
    if(state==MASKSETREAD&&row_i==0)rr_pick=2;
    if(state==SHIFTDONE)rr_pick=3;
    if(state==RASTERDONE)rr_pick=4;
    if(rr_pick>=0)begin
     rr_seen[rr_pick]=rr_seen[rr_pick]+1;
     if(rr_seen[rr_pick]<=32||rr_seen[rr_pick]%41==0)begin
      rr_kind=rr_pick;rr_pre=PACKED;rr_result=0;rr_arg=left_row?1:255;
      rr_size=rr_kind==3?7:rr_kind==4?13:0;rr_bytes=0;rr_packet=0;
      for(rr_i=0;rr_i<66;rr_i=rr_i+1)begin rr_o[rr_i*8+:8]=scratch[rr_i];rr_n[rr_i*8+:8]=scratch[128+rr_i];end
      for(rr_i=0;rr_i<8;rr_i=rr_i+1)rr_m[rr_i*8+:8]=scratch[96+rr_i];
     end
    end
   end
   if(rr_kind==0&&state==ROWDECIDE)begin rr_result={right_row,left_row,equal_row};rr_dump();end
   else if(rr_kind==1&&state==MASKDECIDE&&row_i==7)begin #1;rr_result=mask_equal;rr_dump();end
   else if(rr_kind==2&&state==MASKSETWRITE&&row_i==7)begin #1;rr_result=mask_nonzero;rr_dump();end
   else if(rr_kind>=3&&state==SBYTE&&byte_ready)begin
    rr_packet[rr_bytes*8+:8]=byte_data;rr_bytes=rr_bytes+1;
    if(rr_bytes==rr_size)rr_dump();
   end
  end
 end
'''.replace('PACKED',packed)
    assert source.count('endmodule')==1
    return '`timescale 1ns/1ps\n'+source.replace('endmodule',observer+'\nendmodule')
