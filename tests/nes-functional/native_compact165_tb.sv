// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_compact165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,release_scene=0,begin_scene=0,end_scene=0,source_fault=0,event_valid=0,query=0;
 reg [63:0] event_data=0;reg [1:0] query_kind=0;reg [10:0] query_address=0;
 wire active,owned,valid,response,hit;wire [7:0] errors,row_count,object_count,exception_count;wire [5:0] group_count;wire [63:0] data;
 nes_native_compact165 dut(.*);
 integer f,g,dummy,gap,mode,i,k;reg [63:0] word_value;string source_name,output_name;
 task read_item(input integer kind,input integer address,input bit expect_hit);
  begin
   @(negedge clk);query=1;query_kind=kind;query_address=address;
   @(negedge clk);
   if(response!==1 || hit!==expect_hit || (!expect_hit && data!==0))$fatal(1,"query contract kind=%0d address=%0d",kind,address);
   if(expect_hit)$fwrite(g,"%0d %0d %016h\n",kind,address,data);
   query=0;
  end
 endtask
 initial begin
  dummy=$value$plusargs("INPUT=%s",source_name);dummy=$value$plusargs("OUTPUT=%s",output_name);
  dummy=$value$plusargs("MODE=%d",mode);if(!dummy)mode=0;
  f=$fopen(source_name,"r");g=$fopen(output_name,"w");if(!f || !g)$fatal(1,"missing stream files");
  repeat(3)@(negedge clk);reset=0;begin_scene=1;if(mode==1)source_fault=1;
  @(negedge clk);begin_scene=0;source_fault=0;
  if(mode!=1)begin
   while(!$feof(f))begin
    dummy=$fscanf(f,"%d %h\n",gap,word_value);
    if(dummy==2)begin
     if(gap<1)$fatal(1,"nonpositive event interval");
     repeat(gap-1)@(negedge clk);event_valid=1;event_data=word_value;
     @(negedge clk);event_valid=0;
    end
   end
   repeat(40)@(negedge clk);end_scene=1;
   @(negedge clk);end_scene=0;
  end
  wait(owned);@(negedge clk);
  $fwrite(g,"H %0d %02h %0d %0d %0d %0d\n",valid,errors,row_count,group_count,object_count,exception_count);
  // Inputs after publication cannot replace the sealed data or error status.
  event_valid=1;event_data=64'hffffffffffffffff;@(negedge clk);event_valid=0;
  if(valid)begin
   for(i=0;i<group_count*33;i++)read_item(0,i,1);
   for(i=0;i<row_count;i++)read_item(1,i,1);
   for(i=0;i<object_count;i++)read_item(2,i,1);
   for(i=0;i<exception_count;i++)read_item(3,i,1);
   read_item(0,group_count*33,0);read_item(1,row_count,0);read_item(2,object_count,0);read_item(3,exception_count,0);
  end else begin read_item(0,0,0);read_item(1,0,0);read_item(2,0,0);end
  @(negedge clk);release_scene=1;@(negedge clk);release_scene=0;
  query=1;@(negedge clk);if(response || hit || owned || valid)$fatal(1,"stale read after release");query=0;
  // A second empty lease must not inherit RAM validity from the first.
  begin_scene=1;@(negedge clk);begin_scene=0;end_scene=1;@(negedge clk);end_scene=0;
  wait(owned);@(negedge clk);if(valid || !errors[7])$fatal(1,"stale RAM accepted in empty lease");
  $fclose(f);$fclose(g);$display("PASS COMPACT165 mode=%0d",mode);$finish;
 end
 initial begin #1000000000;$fatal(1,"compact watchdog");end
endmodule
