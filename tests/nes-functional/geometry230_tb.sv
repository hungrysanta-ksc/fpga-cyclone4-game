// SPDX-License-Identifier: MIT
// Observed Mesen stimulus -> unchanged selected collector/exporter.
// PREPARED is a host fixture here; it is NOT a real SNES display ACK.
`timescale 1ns/1ps
module geometry230_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,manual_release=0,ppu_ce=0,rom_fault=0;
 reg [8:0] scanline=0,dot=0;reg [106:0] drive=0;
 wire [5:0] color=drive[105:100];wire [2:0] emphasis=0;
 wire bg_low=drive[49],bg_high=drive[50],obj_low=drive[51],obj_high=drive[52],obj_valid=drive[53],extra_sprites=0;
 wire [1:0] bg_attribute=drive[32:31];wire [7:0] obj_attribute=drive[40:33],obj_x=drive[48:41];
 wire ppu_read=drive[54],ppu_valid=drive[55];wire [13:0] logical_address=drive[30:17];
 wire [21:0] physical_address={5'h10,drive[16:0]};
 wire [14:0] scroll_v=drive[70:56],scroll_t=drive[85:71];
 wire [2:0] fine_x=drive[88:86],pattern_mode=drive[91:89];
 wire [7:0] display_mask=drive[99:92];reg [191:0] palette;
 wire scroll_access=drive[106];
 wire query,response,hit;wire [2:0] query_kind;wire [12:0] query_index;wire [15:0] query_generation;
 wire [63:0] data;wire capture_begin,owned,geometry_valid,initialized,active;
 wire [15:0] generation;wire [24:0] errors,observe_errors180;
 wire observe_collecting180,scroll_seen;wire [7:0] row_count,object_count,exception_count,patch_errors;
 wire [5:0] group_count,palette_count;wire [2:0] patch_count;
 wire exporter_release;wire release_frame=manual_release|exporter_release;
 nes_native_frame201 frame(.*);
 reg enable=0;wire tx_valid;reg tx_ready=1;wire [95:0] tx_data;
 reg ack_valid=0;wire ack_accept=1;reg [15:0] ack_generation=0;wire ack_ready,busy;
 wire [3:0] export_error,observe_state177;
 nes_native_export203 exporter(.clk(clk),.reset(reset),.enable(enable),
  .frame_owned(owned),.geometry_valid(geometry_valid),.frame_generation(generation),
  .patch_count(patch_count),.row_count(row_count),.object_count(object_count),.exception_count(exception_count),
  .group_count(group_count),.palette_count(palette_count),.release_frame(exporter_release),
  .query(query),.query_kind(query_kind),.query_index(query_index),.query_generation(query_generation),
  .response(response),.hit(hit),.data(data),.tx_valid(tx_valid),.tx_ready(tx_ready),.tx_data(tx_data),
  .ack_valid(ack_valid),.ack_accept(ack_accept),.ack_generation(ack_generation),.ack_ready(ack_ready),
  .observe_state177(observe_state177),.busy(busy),.error(export_error));
 reg [106:0] stimulus[0:233*341-1];reg [191:0] palfile[0:0];
 integer first,last,f,t,fd,cf,rc,done,records,frames=0;string name;
 always @(posedge clk)begin
  ack_valid<=0;
  if(!reset&&enable&&tx_valid&&tx_ready)begin
   $fwrite(fd,"%024h\n",tx_data);records++;
   if(tx_data[95:93]==7&&tx_data[76:64]==1)begin ack_valid<=1;ack_generation<=generation;end
   if(tx_data[95:93]==7&&tx_data[76:64]==2)$fatal(1,"source ABORT frame %0d error %0d",f,export_error);
   if(tx_data[95:93]==7&&tx_data[76:64]==3)done=1;
  end
 end
 initial begin
  if(!$value$plusargs("FIRST=%d",first))first=905;
  if(!$value$plusargs("LAST=%d",last))last=975;
  repeat(4)@(negedge clk);reset=0;
  for(f=first;f<=last;f++)begin
   wait(initialized);@(negedge clk);
   name=$sformatf("frame%0d.hex",f);$readmemh(name,stimulus);
   name=$sformatf("frame%0d.palette",f);$readmemh(name,palfile);palette=palfile[0];
   for(t=7*341+257;t<=232*341+1;t++)begin
    @(negedge clk);scanline=t/341;dot=t%341;drive=stimulus[t];ppu_ce=1;
    @(negedge clk);ppu_ce=0;repeat(2)@(negedge clk);
   end
   repeat(64)@(negedge clk);
   if(!owned||!geometry_valid)$fatal(1,"collector frame=%0d owned=%0d valid=%0d errors=%h patch=%h rows=%0d groups=%0d objects=%0d exceptions=%0d patches=%0d",f,owned,geometry_valid,errors,patch_errors,row_count,group_count,object_count,exception_count,patch_count);
   name=$sformatf("frame%0d.cfg",f);cf=$fopen(name,"w");
   $fwrite(cf,"%0d %0d %0d %0d %0d %0d\n",generation,patch_count,object_count,exception_count,group_count,palette_count);$fclose(cf);
   name=$sformatf("frame%0d.wire",f);fd=$fopen(name,"w");if(!fd)$fatal(1,"open wire");
   done=0;records=0;enable=1;
   wait(done);wait(!busy);@(negedge clk);enable=0;$fclose(fd);
   if(export_error)$fatal(1,"exporter frame %0d error %0d",f,export_error);
   frames++;$display("GEOMETRY230 frame=%0d records=%0d",f,records);
  end
  $display("PASS GEOMETRY230 frames=%0d",frames);$finish;
 end
 initial begin #1000000000;$fatal(1,"watchdog");end
endmodule
