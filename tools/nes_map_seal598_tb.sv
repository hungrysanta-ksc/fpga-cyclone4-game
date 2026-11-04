// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module map_seal598_tb;
 reg clk=0;always #22.727 clk=~clk;
 reg reset=1,release_scene=0,begin_scene=0,end_scene=0,source_fault=0;
 reg event_valid=0,row_commit=0,row_patched=0,read_summary=0;
 reg [63:0] event_data=0;
 reg [7:0] committed_row=0;
 reg [4:0] read_group=0;
 wire owned,valid,summary_hit;
 wire [5:0] group_count;
 wire [63:0] summary;
 wire [15:0] map_crc;
 nes_native_compact181 dut(.clk(clk),.reset(reset),.release_scene(release_scene),.begin_scene(begin_scene),
  .end_scene(end_scene),.source_fault(source_fault),.event_valid(event_valid),.event_data(event_data),
  .row_commit(row_commit),.row_patched(row_patched),.committed_row(committed_row),
  .query(1'b0),.query_kind(2'd0),.query_address(11'd0),.owned(owned),.valid(valid),.group_count(group_count),
  .read_summary(read_summary),.read_group(read_group),.summary_hit(summary_hit),.summary(summary),.map_crc(map_crc));
 reg [14:0] cells[0:1055];reg [8:0] row_info[0:223];
 reg [63:0] gold[0:31];
 integer file,n,expected_crc,g,r,c,group_no,total=0,first,last;
 string base;
 task step;begin @(posedge clk);#1;end endtask
 task start_capture;begin begin_scene=1;step;begin_scene=0;end endtask
 task capture_row(input integer y);
  reg [14:0] cell_word;
  begin
   group_no=row_info[y][7:3];row_patched=row_info[y][8];
   if(!row_patched)for(c=0;c<33;c=c+1)begin
    cell_word=cells[group_no*33+c];event_data=0;event_data[12:0]=cell_word[12:0];
    event_data[15:13]=row_info[y][2:0];event_data[32:25]=y;
    event_data[40:33]=c;event_data[42:41]=cell_word[14:13];event_valid=1;step;
   end
   event_valid=0;row_commit=1;committed_row=y;step;row_commit=0;row_patched=0;
  end
 endtask
 initial begin
  step;reset=0;read_summary=1;
  for(g=905;g<=957;g=g+1)begin
   base=$sformatf("f%0d",g);file=$fopen({base,".count"},"r");
   if($fscanf(file,"%d %d",n,expected_crc)!=2)$fatal(1,"fixture");$fclose(file);
   $readmemh({base,".map"},cells,0,n*33-1);$readmemh({base,".row"},row_info);
   $readmemh({base,".gold"},gold,0,n-1);
   if(g==905)begin
    start_capture;capture_row(0);repeat(3)step;
    if(!dut.copy_busy || summary_hit || summary!=0)$fatal(1,"partial copy scope");
    release_scene=1;step;release_scene=0;
   end
   start_capture;
   for(r=0;r<224;r=r+1)begin
    capture_row(r);repeat(33)step;
    if(summary_hit || summary!=0 || map_crc!=0)$fatal(1,"tentative row visible");
   end
   end_scene=1;step;end_scene=0;step;
   if(!owned || !valid || group_count!=n || map_crc!=expected_crc)$fatal(1,"sealed geometry %d",g);
   for(r=0;r<n;r=r+1)begin
    read_group=r;step;
    if(!summary_hit || summary!==gold[r])$fatal(1,"summary %d/%d",g,r);
   end
   if(n<32)begin read_group=n;step;if(summary_hit || summary!=0)$fatal(1,"range");end
   total=total+n;release_scene=1;step;release_scene=0;
   if(summary_hit || map_crc!=0 || summary!=0)$fatal(1,"release");
  end
  start_capture;source_fault=1;step;source_fault=0;step;step;
  if(!owned || valid || summary_hit || summary!=0 || map_crc!=0)$fatal(1,"invalid seal");
  $display("PASS598 frames=53 groups=%0d",total);$finish;
 end
endmodule
