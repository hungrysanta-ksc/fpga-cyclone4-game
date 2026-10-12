// SPDX-License-Identifier: MIT
`timescale 1ns/1ps
module native_scene165_tb;
 reg clk=0;always #5 clk=~clk;
 reg reset=1,ppu_ce=0,ppu_read=0,ppu_valid=1,rom_fault=0,release_scene=0;
 reg [13:0] ppu_logical=0;reg [21:0] ppu_physical=22'h200000;reg [7:0] ppu_data=0;
 reg [8:0] scanline=0,dot=0;reg [14:0] scroll_v=0,scroll_t=0;
 reg [2:0] fine_x=0,pattern_mode=0;reg [7:0] display_mask=8'h1e;
 reg [191:0] palette=0;reg scroll_access=0;
 wire [10:0] nt_address;wire [7:0] nt_data,oam_address,oam_data;wire nt_write,oam_write;
 reg chr_query=0,chr_obj4=0;reg [8:0] chr_slot=0;reg [17:0] chr_tag=18'h20000;reg [4:0] chr_offset=0;
 wire chr_response,chr_hit;wire [7:0] chr_data;wire [15:0] chr_mask;
 reg state_query=0,state_palette=0;reg [7:0] state_row=0;reg [4:0] state_bank=0,state_color=0;
 wire state_response,state_hit;wire [55:0] state_data;
 reg memory_query=0;reg [11:0] memory_address=0;
 wire memory_response,memory_hit;wire [7:0] memory_data;
 wire owned,snapshot_valid;wire [15:0] generation;wire [7:0] raster_errors,row_count;
 wire [2:0] memory_errors;wire [5:0] palette_count;
 nes_native_scene165 dut(.*);
 reg memory_reset=1;reg [24:0] cpumem_addr=0;reg cpumem_write=0;reg [7:0] cpumem_dout=0;
 reg [21:0] ppumem_addr=0;reg ppumem_write=0;reg [7:0] ppumem_dout=0;
 wire [7:0] cpumem_din,ppumem_din,ref_cpu,ref_ppu;wire init_done,ref_done;
 nes_local_memory local_memory(.clk(clk),.reset(memory_reset),.cpumem_addr(cpumem_addr),.cpumem_write(cpumem_write),.cpumem_dout(cpumem_dout),
  .ppumem_addr(ppumem_addr),.ppumem_write(ppumem_write),.ppumem_dout(ppumem_dout),.external_cpu_data(8'h45),.external_ppu_data(8'h67),
  .cpumem_din(cpumem_din),.ppumem_din(ppumem_din),.init_done(init_done),.native_nt_address(nt_address),.native_nt_data(nt_data),.native_nt_write(nt_write));
 nes_local_memory_ref reference_memory(.clk(clk),.reset(memory_reset),.cpumem_addr(cpumem_addr),.cpumem_write(cpumem_write),.cpumem_dout(cpumem_dout),
  .ppumem_addr(ppumem_addr),.ppumem_write(ppumem_write),.ppumem_dout(ppumem_dout),.external_cpu_data(8'h45),.external_ppu_data(8'h67),
  .cpumem_din(ref_cpu),.ppumem_din(ref_ppu),.init_done(ref_done));
 reg oreset=1,oce=0,rendering_enabled=0,oam_addr_write=0,oam_data_write=0;
 reg [7:0] oam_din=0,ss_addr=0,ss_data=0;reg ss_write=0;
 wire [7:0] old_oam;reg oam_known=0;
 OAMEval actual_oam(.clk(clk),.reset(oreset),.ce(oce),.clear_signal(1'b0),.end_of_line(1'b0),.rendering_enabled(rendering_enabled),
  .obj_size(1'b0),.scanline(9'd10),.cycle(9'd65),.oam_addr_write(oam_addr_write),.oam_data_write(oam_data_write),.oam_din(oam_din),
  .is_vbe(1'b0),.PAL(1'b0),.is_pre_render(1'b0),.SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b1),
  .Savestate_OAMAddr(ss_addr),.Savestate_OAMRdEn(1'b0),.Savestate_OAMWrEn(ss_write),.Savestate_OAMWriteData(ss_data),
  .native_oam_address(oam_address),.native_oam_data(oam_data),.native_oam_write(oam_write));
 OAMEval_ref reference_oam(.clk(clk),.reset(oreset),.ce(oce),.clear_signal(1'b0),.end_of_line(1'b0),.rendering_enabled(rendering_enabled),
  .obj_size(1'b0),.scanline(9'd10),.cycle(9'd65),.oam_addr_write(oam_addr_write),.oam_data_write(oam_data_write),.oam_din(oam_din),
  .is_vbe(1'b0),.PAL(1'b0),.is_pre_render(1'b0),.SaveStateBus_Din(64'd0),.SaveStateBus_Adr(10'd0),.SaveStateBus_wren(1'b0),.SaveStateBus_rst(1'b1),
  .Savestate_OAMAddr(ss_addr),.Savestate_OAMRdEn(1'b0),.Savestate_OAMWrEn(ss_write),.Savestate_OAMWriteData(ss_data));
 assign old_oam=reference_oam.oam_read(oam_address);
 integer checks=0,port_checks=0,frames=0,rejects=0,i,j;
 reg [7:0] live[0:2303],frozen[0:2303];
 task check(input bit ok,input string what);
  begin checks=checks+1;if(!ok)$fatal(1,"SCENE165 %s gen=%0d memerr=%h raster=%h",what,generation,memory_errors,raster_errors);end
 endtask
 always @(posedge clk)begin
  #1;if(cpumem_din!==ref_cpu || ppumem_din!==ref_ppu || init_done!==ref_done)$fatal(1,"game memory port changed");
  if(oam_known && oam_data!==old_oam)$fatal(1,"OAM observation changed data");
  port_checks=port_checks+1;
 end
 task idle(input integer n);begin repeat(n)@(negedge clk);end endtask
 task tick(input integer line,input integer x);
  begin @(negedge clk);scanline=line;dot=x;ppu_ce=1;@(negedge clk);ppu_ce=0;end
 endtask
 task nt_put(input integer a,input integer d);
  begin @(negedge clk);ppumem_addr=22'h3a0000+a;ppumem_dout=d;ppumem_write=1;
   #1;check(nt_write,"actual CIRAM write observed");@(negedge clk);ppumem_write=0;live[a]=d;end
 endtask
 task oam_put(input integer a,input integer d);
  begin @(negedge clk);ss_addr=a;ss_data=d;ss_write=1;#1;check(oam_write,"actual OAM savestate write observed");
   @(negedge clk);ss_write=0;live[2048+a]=d;end
 endtask
 task release_it;
  begin @(negedge clk);release_scene=1;chr_query=1;state_query=1;memory_query=1;
   @(negedge clk);check(!owned && !snapshot_valid && !chr_response && !state_response && !memory_response,"common release cancels all queries");
   release_scene=0;chr_query=0;state_query=0;memory_query=0;end
 endtask
 task mem_ask(input integer a,input bit good,input integer want);
  begin @(negedge clk);memory_query=1;memory_address=a;@(posedge clk);#2;
   check(memory_response && memory_hit==good && memory_data===want[7:0],"snapshot byte query");
   @(negedge clk);memory_query=0;end
 endtask
 task components(input bit good);
  begin @(negedge clk);chr_query=1;state_query=1;state_row=0;chr_offset=0;
   @(posedge clk);#2;check(state_response && state_hit==good,"raster query shares lease validity");
   @(negedge clk);state_query=0;chr_query=0;@(posedge clk);#2;
   check(chr_response && chr_hit==good,"CHR query shares lease validity");
   if(good)check(chr_data===8'h80 && chr_mask==16'hffff,"CHR byte retained");
   else check(chr_data==0 && state_data==0,"invalid components withheld");end
 endtask
 task fill_chr;
  integer b;begin for(b=0;b<18;b=b+1)begin
   @(negedge clk);ppu_read=1;ppu_ce=1;ppu_logical=b;ppu_physical=22'h200000+b;ppu_data=8'h80+b;
  end @(negedge clk);ppu_read=0;ppu_ce=0;idle(3);end
 endtask
 task frame(input integer mode);
  integer r;begin
   for(r=0;r<2304;r=r+1)frozen[r]=live[r];
   for(r=0;r<224;r=r+1)begin
    tick(r+8,1);if(mode!=4)idle(16);
    if(mode==0 && r==4)begin
     @(negedge clk);ppumem_addr=22'h3a0800;ppumem_write=1;cpumem_addr=25'h380032;cpumem_write=1;cpumem_dout=8'h21;
     #1;check(!nt_write,"non-CIRAM activity is not a snapshot write");
     @(negedge clk);ppumem_write=0;cpumem_write=0;
    end
    if(mode==1 && r==1)nt_put(12,8'h99);
    if(mode==2 && r==180)oam_put(19,8'h55);
    tick(r+8,128);tick(r+8,256);
   end
   if(mode==3)begin @(negedge clk);ppumem_addr=22'h3a0033;ppumem_dout=8'hfe;ppumem_write=1;end
   tick(232,1);ppumem_write=0;if(mode==3)live[51]=8'hfe;idle(6);frames=frames+1;
   check(owned,"all three components sealed");
   if(mode==0)check(snapshot_valid && memory_errors==0 && raster_errors==0,"stable memory snapshot valid");
   else begin check(!snapshot_valid,"changing/incomplete snapshot rejected");rejects=rejects+1;end
   if(mode==1 || mode==3)check(memory_errors[0],"CIRAM write including terminal edge rejected");
   if(mode==2)check(memory_errors[1],"OAM change after copy rejected");
   if(mode==4)check(memory_errors[2],"incomplete copy rejected");
  end
 endtask
 initial begin
  idle(4);memory_reset=0;oreset=0;wait(init_done);idle(3);
  for(i=0;i<2048;i=i+1)nt_put(i,(i^(i>>3))&255);
  for(i=0;i<256;i=i+1)oam_put(i,(i*7)&255);
  oam_known=1;
  // Actual $2003/$2004 path masks attribute bits, not raw CPU write mirroring.
  @(negedge clk);oce=1;oam_addr_write=1;oam_din=2;@(negedge clk);oam_addr_write=0;oam_data_write=1;oam_din=255;
  #1;check(oam_write,"CPU OAM write observed");@(negedge clk);oam_data_write=0;oce=0;live[2050]=8'he3;
  check(actual_oam.oam_read(2)===8'he3,"actual OAM attribute mask");
  // Seed only evaluator phase to exercise the existing eight-lane row copy.
  actual_oam.old_rendering=0;actual_oam.old_using_secondary=1;actual_oam.oam_secondary_addr=8;actual_oam.oam_addr=24;
  reference_oam.old_rendering=0;reference_oam.old_using_secondary=1;reference_oam.oam_secondary_addr=8;reference_oam.oam_addr=24;
  rendering_enabled=1;oce=1;#1;check(oam_write,"render-rise OAM row copy observed");
  @(negedge clk);oce=0;rendering_enabled=0;
  for(i=0;i<8;i=i+1)begin live[2072+i]=live[2112+i];check(actual_oam.oam_read(24+i)===live[2112+i],"actual row copy byte");end
  // Rendering $2004 changes evaluator addressing but must not fabricate a RAM write.
  actual_oam.old_rendering=1;reference_oam.old_rendering=1;
  rendering_enabled=1;oce=1;oam_data_write=1;oam_din=8'hff;
  #1;check(!oam_write,"rendering CPU OAM write is ignored by primary RAM");
  @(negedge clk);oce=0;rendering_enabled=0;oam_data_write=0;
  reset=0;idle(520);fill_chr();
  frame(0);components(1);
  @(negedge clk);chr_slot=1;chr_tag=18'h20001;chr_query=1;
  @(negedge clk);chr_query=0;@(posedge clk);#2;
  check(snapshot_valid && chr_response && !chr_hit && chr_mask==16'h0003 && chr_data==0,"partial tile is not a ready frame");
  chr_slot=0;chr_tag=18'h20000;
  // Live vblank writes after sealing must not alter the leased image.
  nt_put(23,8'hab);oam_put(45,8'hcd);tick(8,1);check(generation==1,"lease skips a new frame");
  for(i=0;i<2304;i=i+1)mem_ask(i,1,frozen[i]);mem_ask(2304,0,0);
  release_it();frame(0);for(i=0;i<2304;i=i+1)mem_ask(i,1,frozen[i]);components(1);release_it();
  for(j=1;j<=4;j=j+1)begin frame(j);mem_ask(0,0,0);components(0);release_it();end
  // A ROM fault before copy completion freezes all clients despite PPU CE stop.
  tick(8,1);idle(10);rom_fault=1;idle(6);
  check(owned && !snapshot_valid && raster_errors[5] && memory_errors[2],"fault with stopped PPU retires common lease");
  rejects=rejects+1;rom_fault=0;release_it();
  tick(8,1);idle(10);release_it();check(!dut.copy_pending && !dut.copying,"release aborts in-flight copy");
  frame(0);components(1);mem_ask(51,1,live[51]);mem_ask(12,1,live[12]);mem_ask(2067,1,live[2067]);
  @(negedge clk);reset=1;memory_query=1;chr_query=1;state_query=1;@(negedge clk);
  check(!owned && !snapshot_valid && !memory_response && !state_response && !chr_response && generation==0,"reset cancels common lease");
  $display("PASS SCENE165 checks=%0d game_port_checks=%0d frames=%0d rejects=%0d",checks,port_checks,frames,rejects);$finish;
 end
 initial begin #5000000;$fatal(1,"watchdog");end
endmodule
