// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module collect181_tb;
 reg clk=0,reset=1,release_frame=0,ppu_ce=0,rom_fault=0;
 always #5 clk=~clk;
 reg [8:0] scanline=7,dot=0;reg [5:0] color=0;reg [2:0] emphasis=0;
 reg bg_low=0,bg_high=0,obj_low=0,obj_high=0,obj_valid=0,extra_sprites=0;
 reg [1:0] bg_attribute=0;reg [7:0] obj_attribute=0,obj_x=0;
 reg ppu_read=0,ppu_valid=1;reg [13:0] logical_address=0;reg [21:0] physical_address=0;
 reg [14:0] scroll_v=0,scroll_t=0;reg [2:0] fine_x=0,pattern_mode=0;
 reg [7:0] display_mask=8'h18;reg [191:0] palette=0;reg scroll_access=0;
 reg query=0;reg [2:0] query_kind=0;reg [12:0] query_index=0;reg [15:0] query_generation=0;
 wire owned,geometry_valid,initialized,active,observe_collecting180,scroll_seen,response,hit;
 wire [15:0] generation;wire [24:0] errors,observe_errors180;wire [63:0] data;
 wire [7:0] row_count,object_count,exception_count,patch_errors;wire [5:0] group_count,palette_count;
 wire [2:0] patch_count;
 nes_native_frame181 dut(.*);
 wire old_owned,old_valid,old_response,old_hit;wire [63:0] old_data;
 wire [7:0] old_rows;wire [5:0] old_groups;
 nes_native_frame165 old(.clk(clk),.reset(reset),.release_frame(release_frame),.ppu_ce(ppu_ce),.rom_fault(rom_fault),
  .scanline(scanline),.dot(dot),.bg_low(bg_low),.bg_high(bg_high),.obj_low(obj_low),.obj_high(obj_high),
  .obj_valid(obj_valid),.extra_sprites(extra_sprites),.bg_attribute(bg_attribute),.obj_attribute(obj_attribute),.obj_x(obj_x),
  .ppu_read(ppu_read),.ppu_valid(ppu_valid),.logical_address(logical_address),.physical_address(physical_address),
  .scroll_v(scroll_v),.scroll_t(scroll_t),.fine_x(fine_x),.pattern_mode(pattern_mode),.display_mask(display_mask),
  .palette(palette),.scroll_access(scroll_access),.query(query),.query_kind(query_kind),.query_index(query_index),
  .query_generation(query_generation),.owned(old_owned),.geometry_valid(old_valid),.initialized(),.active(),.generation(),
  .errors(),.observe_errors180(),.observe_collecting180(),.scroll_seen(),.row_count(old_rows),.object_count(),
  .exception_count(),.group_count(old_groups),.palette_count(),.response(old_response),.hit(old_hit),.data(old_data));
 integer scenario=0,checks=0,reads=0,baseline_words=0,commits=0,recovered_cells=0;
 function automatic [5:0] pixel(input integer y,input integer x);
  pixel=(y*11+x*3+(x/7))&63;
 endfunction
 function automatic integer rawrow(input integer y);
  case(scenario)
   1:rawrow=(y==185 || y==186);
   2:rawrow=(y==7);
   3:rawrow=(y>=185 && y<192);
   4:rawrow=(y>=184 && y<192);
   7:rawrow=(y==85);
   default:rawrow=0;
  endcase
 endfunction
 task tick;@(posedge clk);#1;@(negedge clk);endtask
 task clear(input integer s);
  scenario=s;release_frame=1;ppu_ce=0;rom_fault=0;emphasis=0;query=0;tick();release_frame=0;
  bg_low=0;bg_high=0;obj_low=0;obj_high=0;obj_valid=0;ppu_read=0;display_mask=8'h18;fine_x=0;
  for(integer i=0;i<32;i++)palette[i*6+:6]=i;
  scanline=7;dot=0;commits=0;
  wait(initialized);@(negedge clk);
 endtask
 always @(negedge clk)if(dut.row_commit)begin
  if(dut.committed_row!=commits)$fatal(1,"commit order got%0d expected%0d",dut.committed_row,commits);
  if((scenario<5 || scenario==7) && dut.row_patched!==rawrow(commits))$fatal(1,"patch row%0d got%b case%0d",commits,dut.row_patched,scenario);
  commits++;
 end
 task one_dot;
  integer target,col,lane,ny,nx,omit;
  target=(dot>=257)?scanline+1:scanline;
  col=(dot>=321)?((dot>=329)?1:0):(((dot+7)>>3)+1);
  lane=dot%8;
  bg_low=target>=8 && target<232 && col<=32 && ((dot>=321 && dot<336 && lane==1)||(dot<256 && lane==5));
  bg_high=target>=8 && target<232 && col<=32 && ((dot>=321 && dot<336 && lane==3)||(dot<256 && lane==7));
  // Missing complete pairs reproduce fetch-valid/compact82, including the
  // next row's prefetch. No stale tile or missing source response is accepted.
  omit=rawrow(target-8) && scenario!=2 && scenario!=7;
  if(omit && (col==0 || (col>=15 && col<=20)))begin bg_low=0;bg_high=0;end
  obj_low=target>=8 && target<232 && dot==261;
  obj_high=target>=8 && target<232 && dot==263;obj_valid=obj_low||obj_high;
  obj_attribute=8'h20;obj_x=40;
  physical_address=22'h200000+(obj_valid?64:col+1+(rawrow(target-8)?128:0))*16+((target-8)%8)+((bg_high||obj_high)?8:0);
  logical_address=physical_address[12:0];ppu_read=bg_low||bg_high||obj_low||obj_high;
  if(scenario==5 && scanline==40 && dot==7)ppu_valid=0;else ppu_valid=1;
  if(scenario==6 && scanline==40 && dot==100)emphasis=1;
  display_mask=(rawrow(scanline-8) && scenario!=2 && scenario!=7 && dot>=120 && dot<156)?8'h00:8'h18;
  if(scenario==7 && scanline==93 && dot==120)palette[11:6]=6'd31;
  if(scenario==8 && scanline==88 && dot==0)palette[11:6]=6'd31;
  if(scenario==8 && scanline==168 && dot==0)palette[11:6]=6'd30;
  fine_x=(scenario==2 && scanline==15 && dot>=100)?1:0;
  scroll_v=((scanline-8)%8)<<12;scroll_t=0;
  // Pixel output changes in NBA with coordinates, like the selected PPU.
  ny=(dot==340)?scanline+1:scanline;nx=(dot==340)?0:dot+1;
  ppu_ce=1;
  @(posedge clk);scanline<=ny;dot<=nx;color<=pixel(ny-8,nx-2);
  #1;@(negedge clk);ppu_ce=0;bg_low=0;bg_high=0;obj_low=0;obj_high=0;obj_valid=0;ppu_read=0;
  tick();tick();tick();
  if(dot%37==0)repeat(3)tick(); // independent CE gaps must not duplicate pixels
 endtask
 task frame;
  while(scanline<232 || dot<3)one_dot();
  repeat(40)tick();
  if(!owned)$fatal(1,"not retired case%0d",scenario);
 endtask
 task readword(input integer k,input integer a);
  query=1;query_kind=k;query_index=a;query_generation=generation;tick();
  if(!response || !hit)$fatal(1,"read failed kind%0d addr%0d",k,a);
  query=0;
 endtask
 task check_rows(input integer expected);
  integer slot,g;
  if(!geometry_valid || errors!=0 || patch_errors!=0 || patch_count!=expected || row_count!=224 || commits!=224)
   $fatal(1,"candidate case%0d valid%b err%h patch%h count%0d rows%0d commits%0d",scenario,geometry_valid,errors,patch_errors,patch_count,row_count,commits);
  slot=0;
  for(integer y=0;y<224;y++)begin
   readword(4,y);
   if(data[49]!==rawrow(y))$fatal(1,"descriptor flag row%0d",y);
   if(rawrow(y))begin
    if(data[52:50]!=slot || data[48:0]!=0)$fatal(1,"descriptor slot row%0d",y);
    for(integer x=0;x<256;x++)begin
     readword(7,slot*256+x);
     if(data!=={58'd0,pixel(y,x)})$fatal(1,"pixel y%0d x%0d got%h",y,x,data);
     reads++;
    end
    slot++;
   end else begin
    readword(1,y);g=data>>3;
    if(data[2:0]!=(y%8) || g>=group_count)$fatal(1,"normal row descriptor y%0d",y);
    for(integer x=0;x<33;x++)begin
     readword(0,g*33+x);
     if(data!==64'(x+1))$fatal(1,"stale map after raw row y%0d x%0d got%h",y,x,data);
     recovered_cells++;
    end
   end
  end
  checks++;
 endtask
 initial begin
  for(integer i=0;i<32;i++)palette[i*6+:6]=i;
  repeat(3)tick();reset=0;
  clear(0);frame();check_rows(0);
  if(!old_valid || old_rows!=224 || old_groups!=group_count)$fatal(1,"baseline not valid");
  for(integer k=0;k<7;k++)begin
   for(integer a=0;a<(k==0?group_count*33:(k==1||k==4)?224:k==2?object_count:k==5?32:k==6?8192:0);a++)begin
    readword(k,a);if(!old_hit || data!==old_data)$fatal(1,"normal differs k%0d a%0d new%h old%h",k,a,data,old_data);
    baseline_words++;
   end
  end
  clear(1);frame();check_rows(2);if(old_valid)$fatal(1,"old collector should reject missing BG");
  clear(2);frame();check_rows(1);if(old_valid)$fatal(1,"old raster should reject fineX change");
  clear(3);frame();check_rows(7);
  clear(4);frame();if(geometry_valid || !patch_errors[3])$fatal(1,"eighth raw row accepted");checks++;
  clear(5);frame();if(geometry_valid || !errors[2])$fatal(1,"invalid CHR response hidden");checks++;
  clear(6);frame();if(geometry_valid || !patch_errors[5])$fatal(1,"emphasis lost");checks++;
  clear(7);frame();check_rows(1);if(palette_count!=2)$fatal(1,"palette epoch lost");
  clear(8);frame();if(geometry_valid || !errors[18])$fatal(1,"third palette accepted");checks++;
  clear(1);frame();check_rows(2);
  query=1;query_kind=7;query_index=0;query_generation=generation-1;tick();if(hit)$fatal(1,"stale generation");checks++;
  query_generation=generation;query_index=7*256;tick();if(hit)$fatal(1,"scratch exposed");checks++;
  query=0;rom_fault=1;tick();if(geometry_valid || !owned)$fatal(1,"sealed fault");checks++;
  query=1;tick();if(hit)$fatal(1,"fault read exposed");query=0;
  clear(0);repeat(300)one_dot();rom_fault=1;ppu_ce=0;repeat(8)tick();
  if(!owned || geometry_valid)$fatal(1,"CE stopped fault hangs");checks++;
  $display("PASS COLLECT181 cases=%0d pixels=%0d baseline_words=%0d recovered_cells=%0d",checks,reads,baseline_words,recovered_cells);$finish;
 end
 initial begin #100000000;$fatal(1,"watchdog");end
endmodule
