integer field1060=0;
reg measuring1060=0;
wire captured,valid_capture,collector_active;
wire [24:0] errors;
nes_native_frame201 #(.TILE_QUERY(0)) collector(
 .clk(clk),.reset(core_reset||!measuring1060),.release_frame(captured),.ppu_ce(ce),.rom_fault(1'b0),
 .snapshot_conflict(1'b0),.scanline(line_no),.dot(dot),.color(color),.emphasis(core.emphasis),
 .bg_low(core.native_bg_low),.bg_high(core.native_bg_high),.obj_low(core.native_obj_low),
 .obj_high(core.native_obj_high),.obj_valid(core.native_obj_valid),.extra_sprites(core.native_extra_sprites),
 .bg_attribute(core.tap_attribute),.obj_attribute(core.native_obj_attribute),.obj_x(core.native_obj_x),
 .ppu_read(pr),.ppu_valid(init_done && pa[21:13]==9'h100),.logical_address(core.native_chr_logical),.physical_address(pa),
 .scroll_v(core.native_scroll_v),.scroll_t(core.native_scroll_t),.fine_x(core.native_fine_x),
 .pattern_mode(core.native_pattern_mode),.display_mask(core.native_display_mask),.palette(core.native_palette),
 .scroll_access(core.native_scroll_access),.query(1'b0),.query_kind(3'd0),.query_index(14'd0),
 .query_generation(16'd0),.owned(captured),.geometry_valid(valid_capture),.errors(errors),.active(collector_active));
always @(posedge clk) if(measuring1060 && ce && line_no==7 && dot==257) field1060++;
always @(posedge clk) if(measuring1060 && ce && line_no>=7 && line_no<231 && core.native_obj_high && core.native_obj_valid && pr)
 $display("FETCH %0d %0d %0d %0d %0d %0d %0d %0d",field1060,line_no-7,(dot-257)/8,core.native_obj_x,
 core.native_obj_attribute,pa[12:4],pa[2:0],core.native_display_mask);
always @(posedge clk) if(captured && measuring1060)begin
 $display("FIELD %0d %b %h",field1060,valid_capture,errors);
 if(valid_capture)for(int i=0;i<collector.object_count;i++)
  $display("FRAGMENT %0d %013h",field1060,collector.compact.objects[i][49:0]);
end
// Independent read port verifies all 256 bytes written by the file walker.
task automatic oam_snapshot(input integer field);
 reg [7:0] value;
 for(int i=0;i<256;i++) begin
  @(negedge clk);inspect_oam=i;repeat(2)@(negedge clk);#1;
  value=core.native_oam_data;
  if(field<0 && value!==checkpoint[65+i/8][8*(i%8)+:8])$fatal(1,"OAM restore byte %0d %h expected %h",i,value,checkpoint[65+i/8][8*(i%8)+:8]);
  if($isunknown(value))$fatal(1,"OAM unknown %0d",i);
  $display("OAM %0d %0d %0d",field,i,value);
 end
endtask
initial begin
 wait(measuring1060);
 for(int i=1;i<=3;i++)begin
  wait(ce && dot==0 && line_no==6);oam_snapshot(i);wait(line_no==8);
 end
end
initial begin
 // Cyclone IV user registers power up low. The upstream evaluation counter
 // has no RTL reset assignment; in a four-state simulator X would never
 // enter its idle state and would overwrite secondary slot zero on every byte.
 core.core.ppu.spriteeval.eval_count=2'b00;
 fd=$fopen("prg.bin","rb");n=$fread(prg,fd);$fclose(fd);if(n!=$size(prg))$fatal;
 $readmemh("physical.hex",checkpoint);
 repeat(8)@(negedge clk);reset=0;wait(init_done);
 @(negedge clk);pause_req=1;wait(paused);@(negedge clk);load_req=1;
 @(negedge clk);load_req=0;wait(restored);wait(!sleeping);wait(paused);
 if(loads!=WORDS)$fatal(1,"incomplete restore");
 oam_snapshot(-1);
 @(negedge clk);pause_req=0;wait(!paused);measuring1060=1;
 wait(field1060==4);$display("PASS castle physical slot including full OAM, 3 fields of movement");$finish;
end
initial begin repeat(8000000)@(posedge clk);$fatal(1,"timeout");end
