// FF3 PRG is supplied only at runtime from the user's local cartridge image.
`timescale 1ns/1ps
module ff3_checkpoint_tb;
 reg clk=0; always #5 clk=!clk;
 reg reset=1, pause_req=0, save_req=0, load_req=0;
 wire paused,sleeping,restored,init_done;
 wire [24:0] ca,sa; wire [21:0] pa; wire [7:0] cd,pd,cq,pq,sd,sq;
 wire cw,pw,cr,pr,sr,sw,ce;
 wire [8:0] line_no,dot; wire [5:0] color;
 wire [63:0] put; reg [63:0] get;
 wire [25:0] ptr; wire rnw,request; wire [7:0] be; reg ack=0;
 wire [15:0] audio;
 reg [7:0] prg[0:524287];
 localparam WORDS=2658, BASE=58720256;
 reg [63:0] checkpoint[0:WORDS-1];
 bit saved_word[0:WORDS-1],loaded_word[0:WORDS-1];
 reg [31:0] resume_fetch[0:63];
 reg [31:0] cold_fetch[0:63];
 wire [191:0] live_palette;
 for(genvar cell_index=0;cell_index<32;cell_index++) begin : raw_palette
   assign live_palette[6*cell_index+:6]=core.core.ppu.palette_ram.palette[cell_index];
 end
 wire [191:0] live_mapper={core.core.multi_mapper.mapper.SS_MAP3_BACK,
                           core.core.multi_mapper.mapper.SS_MAP2_BACK,
                           core.core.multi_mapper.mapper.SS_MAP1_BACK};
 // File indices include the header. Observe the owners, independently of
 // the RTL address decoder. Reserved bits are excluded from comparisons.
 function automatic logic [63:0] core_word(input int word_no);
   case(word_no)
     1: return core.core.cpu.ss_1_back;
     2: return core.core.cpu.ss_2_back;
     3: return core.core.cpu.ss_3_back;
     5: return core.core.ppu.SS_PPU_BACK;
     6: return core.core.ppu.SS_PPU_DECAY_BACK;
     17: return core.core.apu.SS_APU_BACK;
     18: return core.core.apu.Dmc.SS_DMC1_BACK;
     19: return core.core.apu.Dmc.SS_DMC2_BACK;
     20: return core.core.apu.frame_counter.SS_FCT_BACK;
     default: return 0;
   endcase
 endfunction
 function automatic logic [63:0] word_mask(input int word_no);
   case(word_no)
     1: return '1;
     2: return (64'd1<<44)-1;
     3: return (64'd1<<58)-1;
     5: return (64'hff<<50) | (((64'd1<<47)-1) ^ (64'd1<<22));
     6,19: return (64'd1<<48)-1;
     17: return (64'd1<<11)-1;
     18: return (64'd1<<53)-1;
     20: return (64'd1<<23)-1;
     default: return 0;
   endcase
 endfunction
 reg [63:0] cold_core[1:20];
 task automatic check_core_word(input int n,input logic [63:0] expected);
   logic [63:0] observed,mask;
   mask=word_mask(n);
   observed=core_word(n)&mask;
   if($isunknown(observed) || observed!==(expected&mask))
     $fatal(1,"state word %0d live=%h expected=%h mask=%h",n,observed,expected,mask);
 endtask
 reg [191:0] cold_palette,cold_mapper;
 reg [191:0] saved_palette,saved_mapper;
 localparam [63:0] REG_PATTERN=64'h25301c12a318352b;
 function automatic logic [63:0] partial_word(input int word_no);
   // Exercise the two CHR low bits differently in MAP1 and MAP3.
   if(word_mask(word_no)!=0) return REG_PATTERN ^ {32'd0,{4{word_no[7:0]}}};
   return word_no==35 ? REG_PATTERN ^ 64'h0003_0000_0000_0000 : REG_PATTERN;
 endfunction
 integer stop_before=-1;
 integer saves=0,loads=0,chr_writes=0,prg_reads=0,nt_writes=0;
 integer k,j,idx,fd,n;
 bit withhold_ack=0;
 // The SPI endpoint reads the walker's file index and bytes throughout a
 // response and its retries. Check them under backpressure on every word.
 int reply_delay;
 reg [25:0] held_ptr;
 reg [63:0] held_put;
 reg [7:0] held_be;
 bit held_rnw;
 reg [7:0] sram_image[0:8191];
 reg battery=0,bw=0;reg [12:0] ba; reg [7:0] bv;
 wire accepted,rvalid;
 wire core_reset=reset || !init_done;
 integer alignment[0:3]='{default:0};
 always @(posedge clk) if(!core_reset && core.core.is_in_vblank_paused &&
     core.core.div_cpu==1 && core.core.div_ppu==1 && core.core.cpu_Instrnew)
   alignment[core.core.div_sys]++;
 // Same post-read shift edge and active-high button order as nes_game_pad150.
 reg [7:0] pad_shift=0;
 wire [1:0] pad_clock;
 wire [2:0] pad_strobe;
 reg pad_old=0;
 reg [3:0] input_phase=0;
 always @(posedge clk)if(reset || pause_req)input_phase<=0;
 else if(ce && line_no==232 && dot==0)input_phase<=input_phase==9?0:input_phase+1'b1;
 wire [7:0] buttons=$test$plusargs("attack") ? {7'd0,input_phase<3} :
                    $test$plusargs("move_up") ? 8'h10 : ($test$plusargs("walk_down") ? 8'h20 : 8'h00);
 always @(posedge clk)begin
   pad_old<=pad_clock[0];
   if(pad_strobe[0])pad_shift<=buttons;
   else if(pad_old && !pad_clock[0])pad_shift<={1'b1,pad_shift[7:1]};
 end
 nes_probe core(.clk(clk),.cold_reset(core_reset),.reset_nes(core_reset),
  .request_pause(pause_req),.request_save(save_req),.request_load(load_req),.paused(paused),.state_sleep(sleeping),.restored(restored),
  .stream_write(put),.stream_read(get),.stream_addr(ptr),.stream_rnw(rnw),.stream_ena(request),.stream_be(be),.stream_done(ack),
  .state_address(sa),.state_read(sr),.state_write(sw),.state_wdata(sd),.state_rdata(sq),
  .cpumem_addr(ca),.cpumem_read(cr),.cpumem_write(cw),.cpumem_dout(cd),.cpumem_din(cq),
  .ppumem_addr(pa),.ppumem_read(pr),.ppumem_write(pw),.ppumem_dout(pd),.ppumem_din(pq),
  .native_oam_address(11'd0),.chr_32k(1'b0),.joypad_clock(pad_clock),.joypad_out(pad_strobe),.joypad1_data({4'b0,pad_strobe[0]?buttons[0]:pad_shift[0]}),.joypad2_data(5'd0),
  .sample(audio),.tap_ce(ce),.color(color),.cycle(dot),.scanline(line_no));
 reg [12:0] scan_address=0;
 wire [7:0] scan_byte;
 `ifdef FF3_FITTED
 localparam USE_M9K=1;
 `else
 localparam USE_M9K=0;
 `endif
 nes_checkpoint_memory #(.DEVICE_CHR(USE_M9K)) mem(.clk(clk),.reset(reset),.paused(paused),
  .chr_scan_address(scan_address),.chr_scan_data(scan_byte),
  .cpumem_addr(ca),.cpumem_write(cw),.cpumem_dout(cd),.cpumem_din(cq),
  .ppumem_addr(pa),.ppumem_write(pw),.ppumem_dout(pd),.ppumem_din(pq),
  .external_cpu_data(prg[ca[18:0]]),.external_ppu_data(8'hff),.native_nt_address(11'd0),.init_done(init_done),
  .state_address(battery?{12'h1e0,ba}:sa),.state_write(battery?bw:sw),.state_read(battery?!bw:sr),
  .state_wdata(battery?bv:sd),.state_rdata(sq),.state_rvalid(rvalid),.state_accepted(accepted));
 always @(posedge clk) begin
   ack<=0;
   if(!core_reset && core.core.Savestate_RAMType==6 &&
      (!paused || !sleeping || sr || sw || core.core.Savestate_OAMWrEn || core.core.Savestate_MAPRAMWrEn))
     $fatal(1,"palette byte reached another port or ran outside pause");
   if(core_reset) reply_delay=0;
   else if(reply_delay>0)begin
     if(request || ptr!==held_ptr || be!==held_be || rnw!==held_rnw ||
        (!rnw && put!==held_put)) $fatal(1,"unstable file word while waiting for ACK");
     reply_delay--;
     if(!reply_delay) ack<=1;
   end
   if(request && !withhold_ack && !(rnw && ptr==BASE+2*stop_before))begin
     if(ptr<BASE || ptr>=BASE+WORDS*2 || ptr[0]) $fatal(1,"stream address %h",ptr);
     idx=(ptr-BASE)>>1;
     if(idx!=(rnw?loads:(saves+1)%WORDS)) $fatal(1,"out-of-order word %0d",idx);
     if(rnw)begin
       if(loaded_word[idx]) $fatal(1,"repeated state read %d",idx);
       loaded_word[idx]=1;
       // Deliberately different palette, mapper banks and IRQ values.
       get<=stop_before<0 || idx==0 ? checkpoint[idx] : partial_word(idx);
       loads++;
     end
     else begin
       if(saved_word[idx]) $fatal(1,"repeated state write %d",idx);
       if(word_mask(idx)!=0) check_core_word(idx,put);
       saved_word[idx]=1;
       for(j=0;j<8;j++) if(be[j])checkpoint[idx][8*j+:8]<=put[8*j+:8];
       saves++;
     end
     held_ptr=ptr;held_put=put;held_be=be;held_rnw=rnw;
     reply_delay=1+(idx%7);
   end
   if(!core_reset && !paused) begin
     if(pw && pa[21:13]==9'h100)chr_writes++;
     if(pw && pa[21:11]==11'h740)nt_writes++;
     if(cr && ca<524288)prg_reads++;
   end
 end
 task automatic battery_byte(input integer address,input bit writing,input byte value);
   begin
     @(negedge clk);battery=1; ba=address;bw=writing;bv=value; #1;
     if(!accepted)$fatal(1,"battery port denied");
     @(posedge clk);#1;
     if(!writing && (!rvalid || sq!==value)) $fatal(1,"battery mismatch %0d %h/%h",address,sq,value);
   end
 endtask
 task automatic check_cold_cpu(input bit compare);
   reg [31:0] fetch;
   foreach(cold_fetch[i])begin
     do @(posedge clk);while(!(core.core.cpu_ce && core.core.cpu_Instrnew && !core.core.cpu_reset));
     fetch={7'd0,core.core.cpu_rnw,core.core.cpu_addr_full[15:0],core.core.internal_data_bus};
     if($isunknown(fetch) || (compare && cold_fetch[i]!==fetch)) $fatal(1,"cold CPU fetch %0d",i);
     cold_fetch[i]=fetch;
   end
 endtask
 task automatic abort_partial_restore(input int boundary,input bit mid_palette=0);
   localparam [63:0] map3=REG_PATTERN ^ 64'h0003_0000_0000_0000;
   @(negedge clk);pause_req=1;wait(paused);
   foreach(loaded_word[i]) loaded_word[i]=0;
   @(negedge clk);loads=0;stop_before=boundary;withhold_ack=0;load_req=1;
   @(negedge clk);load_req=0;
   if(mid_palette)
     wait(core.core.Savestate_RAMType==6 && sa[4:0]==14 && core.core.loading_savestate);
   else wait(request && rnw && ptr==BASE+boundary*2);
   @(negedge clk);
   if(!sleeping || !paused || restored) $fatal(1,"partial state exposed");
   for(int n=1;n<boundary && n<=20;n++)
     if(word_mask(n)!=0) check_core_word(n,partial_word(n));
   for(int bank=0;bank<4;bank++)
     for(int lane=0;lane<8;lane++)
       if(mid_palette ? (bank<2 || (bank==2 && lane<3)) : 8+bank<boundary)
       if(live_palette[6*(4*lane+bank)+:6]!==REG_PATTERN[8*lane+:6])
         $fatal(1,"partial palette not applied");
   if(boundary>33 && live_mapper[62:0]!==REG_PATTERN[62:0]) $fatal(1,"partial MAP1");
   if(boundary>34 && live_mapper[127:64]!==REG_PATTERN) $fatal(1,"partial MAP2");
   if(boundary>35 && live_mapper[177:128]!==map3[49:0]) $fatal(1,"partial MAP3");
   reset=1;pause_req=0;repeat(8)@(negedge clk);
   foreach(cold_core[n]) if(word_mask(n)!=0) check_core_word(n,cold_core[n]);
   if(live_palette!==cold_palette || live_mapper!==cold_mapper || sleeping || restored || ack || sw || sr)
     $fatal(1,"STOP failed to discard partial state before cold release");
   reset=0;wait(init_done);check_cold_cpu(1);
   repeat(200)@(negedge clk);
   if(sleeping || restored || request || sw || sr) $fatal(1,"aborted word revived");
   stop_before=-1;
   $display("PASS partial restore STOP/cold boundary=%0d mid_palette=%b",boundary,mid_palette);
 endtask
 task automatic check_resumed_cpu(input bit compare);
   reg [31:0] fetch;
   for(int n=0;n<64;n++)begin
     do @(posedge clk); while(!(core.core.cpu_ce && core.core.cpu_Instrnew && !paused));
     fetch={7'b0,core.core.cpu_rnw,core.core.cpu_addr_full[15:0],
            core.core.cpu_rnw ? core.core.internal_data_bus : core.core.cpu_dout};
     if($isunknown(fetch)) $fatal(1,"undefined resumed CPU bus %0d",n);
     if(compare && resume_fetch[n]!==fetch)
       $fatal(1,"resumed CPU bus %0d %h/%h",n,resume_fetch[n],fetch);
     resume_fetch[n]=fetch;
   end
 endtask
 reg [5:0] reference_pixels[0:2*256*240-1];
 task automatic compare_resumed_picture(input bit compare);
   reg [63:0] colors;
   colors=0;
   for(int frame=0;frame<2;frame++)begin
     do @(posedge clk); while(!(ce && line_no==0 && dot==1));
     for(int y=0;y<240;y++)for(int x=0;x<256;x++)begin
       if(x!=0 || y!=0)do @(posedge clk);while(!(ce && line_no==y && dot==x+1));
       if($isunknown(color))$fatal(1,"undefined pixel %d,%d",x,y);
       if(compare && color!==reference_pixels[(frame*240+y)*256+x])
         $fatal(1,"restored PPU pixel frame=%0d x=%0d y=%0d",frame,x,y);
       reference_pixels[(frame*240+y)*256+x]=color;
       colors[color]=1;
     end
   end
   $display("FF3 restored=%d visible pixels=122880 distinct_colors=%0d",compare,$countones(colors));
 endtask
 function automatic byte file_byte(input int offset);
   return checkpoint[offset/8][8*(offset%8)+:8];
 endfunction
 task automatic cancel_stream(input bit loading);
   @(negedge clk); pause_req=1;wait(paused);
   @(negedge clk);withhold_ack=1;load_req=loading;save_req=!loading;
   @(negedge clk);load_req=0;save_req=0;
   wait(request);repeat(3)@(negedge clk);reset=1;pause_req=0;
   repeat(4)@(negedge clk);
   if(sleeping || request || sw || sr || restored)$fatal(1,"STOP left state operation active");
   reset=0;wait(init_done);repeat(200)@(negedge clk);
   if(sleeping || request || sw || sr || restored)$fatal(1,"stale request after STOP");
 endtask
 task automatic verify_memory;
   // One header word, 64 register words, 256 OAM bytes, 8 mapper bytes.
   localparam CHR=784, NT=CHR+8192, CPU=NT+2048, PRG=CPU+2048;
   for(int n=0;n<8192;n++) begin
     scan_address=n;repeat(2)@(negedge clk);
     if(file_byte(CHR+n)!==scan_byte ||
        file_byte(PRG+n)!==sram_image[n]) $fatal(1,"CHR or cartridge RAM offset %d",n);
     if(n<2048 && (file_byte(NT+n)!==mem.region[1].nametable.ram.mem[n] ||
                   file_byte(CPU+n)!==mem.region[0].local_ram.ram.mem[n]))
       $fatal(1,"nametable or CPU RAM offset %d",n);
   end
 endtask
 // Replay the physical cartridge save, or cold opening, against the routed
 // snapshot FSM. Retire immediately at the end of the visible field to isolate
 // CHR eligibility from downstream SPI, ARM, and SNES backpressure.
 wire scene_mode=$test$plusargs("scene_replay");
 wire scene_ready,scene_conflict;
 reg measuring=0,active_scene=0;
 wire gate=ce && line_no==7 && dot==257;
 wire end_scene=ce && line_no==232 && dot==0;
 `ifdef FF3_SCENE
 wire captured,valid_capture,capture_clk,collector_active;
 wire scene_start=capture_clk,scene_retire=captured,scene_collect=collector_active;
 `else
 wire scene_start=measuring && gate && scene_ready,scene_retire=end_scene,scene_collect=active_scene;
 `endif
 wire observed_unchanged;
 nes_chr_snapshot trace_copy(.clk(clk),.reset(core_reset),.changed(mem.chr_changed),
     .start(scene_start),.can_start(scene_ready),.start_gen(16'd1),
     `ifdef FF3_PAGES
     .changed_page(mem.ppu_address[12:10]),
     `ifdef FF3_CHR_HISTORY
     .frame_unchanged(observed_unchanged),
     `endif
 `endif
     .collecting(scene_collect),.discard(1'b0),.retire(scene_retire),.retire_gen(16'd1),
     .conflict(scene_conflict),.read_req(1'b0),.cancel(1'b0),.read_addr(18'd0),
     .read_gen(16'd0),.scan_data(scan_byte),.ram_q(8'd0));
 always @(posedge clk) if(reset || end_scene)active_scene<=0;else if(scene_start)active_scene<=1;
 `ifdef FF3_SCENE
 wire [24:0] errors;
 nes_native_frame201 #(.TILE_QUERY(0)) collector(.clk(clk),.reset(core_reset||!measuring),
     .release_frame(captured),.ppu_ce(ce && (!gate || scene_ready)),.rom_fault(1'b0),
     .scanline(line_no),.dot(dot),.color(color),.emphasis(core.emphasis),
     .bg_low(core.native_bg_low),.bg_high(core.native_bg_high),.obj_low(core.native_obj_low),
     .obj_high(core.native_obj_high),.obj_valid(core.native_obj_valid),.extra_sprites(core.native_extra_sprites),
     .bg_attribute(core.tap_attribute),.obj_attribute(core.native_obj_attribute),.obj_x(core.native_obj_x),
     .ppu_read(pr),.ppu_valid(init_done && pa[21:13]==9'h100),.logical_address(core.native_chr_logical),
     .physical_address(pa),.scroll_v(core.native_scroll_v),.scroll_t(core.native_scroll_t),.fine_x(core.native_fine_x),
     .pattern_mode(core.native_pattern_mode),.display_mask(core.native_display_mask),.palette(core.native_palette),
     .scroll_access(core.native_scroll_access),.query(1'b0),.query_kind(3'd0),.query_index(14'd0),
     .query_generation(16'd0),.snapshot_conflict(scene_conflict),.owned(captured),.geometry_valid(valid_capture),
     .errors(errors),.capture_begin(capture_clk),.active(collector_active));
 `ifdef FF3_BACKDROP
 // Independent observation on the same settled PPU edge as the physical taps.
 reg monitor_after;
 reg [223:0] nonuniform;
 reg [5:0] origin_color;
 integer samples;
 integer proof_frame=0;
 always @(posedge clk)if(measuring && end_scene)proof_frame<=proof_frame+1;
 always @(posedge clk) begin
  monitor_after<=ce;
  if(monitor_after && line_no>=8 && line_no<232)begin
   if(dot==1)begin nonuniform[line_no-8]<=0;origin_color<=core.native_palette[5:0];samples<=0;end
   if(dot>=2 && dot<=257)begin
    if(color!==origin_color)nonuniform[line_no-8]<=1;
    samples<=samples+1;
   end
   if(dot==258 && measuring && collector_active && samples!=256)$fatal(1,"short observed row");
  end
  if(captured && valid_capture)begin : verify_band
   integer count;
   count=0;
   for(int y=0;y<224;y++)if(!collector.raster.rows[y][49] && collector.raster.rows[y][43:36]==0)begin
    if(nonuniform[y]!==0)$fatal(1,"backdrop claims visible ink on row %0d",y);
    count++;
   end
   $display("CHECKED_BACKDROP rows=%0d raw=%0d",count,collector.patch_count);
   if($test$plusargs("walk_down") || $test$plusargs("attack") || (count!=0 && proof_frame%8==0))begin
    if($test$plusargs("attack") || $test$plusargs("walk_down"))$display("CHR_HISTORY %0d %b",proof_frame,observed_unchanged);
    `ifdef FF3_PAGE_HISTORY
    $display("CLEAN_PAGES %0d %02h",proof_frame,trace_copy.clean_pages);
    `endif
    $display("GEOMETRY %0d %0d %0d %0d %0d %0d",proof_frame,collector.group_count,collector.object_count,
             collector.exception_count,collector.palette_count,collector.patch_count);
    for(int i=0;i<collector.group_count*33;i++)$write("%04h",collector.compact.group_count==0?16'd0:collector.compact.maps[i]);
    $display("");
    for(int i=0;i<224;i++)$write("%02h",collector.compact.maps[1280+i][7:0]);
    $display("");
    for(int i=0;i<224;i++)$write("%014h",collector.raster.rows[i]);
    $display("");
    for(int i=0;i<collector.object_count;i++)$write("%013h",collector.compact.objects[i][49:0]);
    $display("");
    for(int i=0;i<collector.exception_count;i++)$write("%09h",collector.compact.exceptions[i]);
    $display("");
    for(int i=0;i<collector.palette_count*32;i++)$write("%02h",collector.raster.colors[i]);
    $display("");
    for(int i=0;i<collector.patch_count*256;i++)$write("%02h",collector.pixels.rows.pixels[i]);
    $display("");
   end
  end
 end
 `endif
 integer rb,cb,fb,blank,solid,dirtylines;
 reg [63:0] line_colors;
 reg [5:0] firstcolor;
 always @(posedge clk) if(ce && $test$plusargs("move_up"))begin
   if(line_no==7 && dot==257)begin rb=0;cb=0;fb=0;blank=0;solid=0;dirtylines=0;end
   if(line_no>=8 && line_no<232)begin
    if(dot==1)begin line_colors=0;firstcolor=color;end
    if(dot>=1 && dot<=256)line_colors[color]=1;
    if(dot==257)begin
     rb+=collector.raster_patch;cb+=collector.compact_patch;fb+=collector.fetch_patch;
     blank+=(core.native_display_mask[4:3]==0);
     solid+=($countones(line_colors)==1);
     if(line_no==8 || (line_no[3:0]==0 && (collector.raster_patch || core.native_display_mask[4:3]==0)))
      $display("ROW line=%0d mask=%h v=%h t=%h colors=%016h bgcol=%h rb=%b cb=%b",line_no,core.native_display_mask,core.native_scroll_v,core.native_scroll_t,line_colors,core.native_palette[5:0],collector.raster_patch,collector.compact_patch);
    end
   end
   if(line_no==232 && dot==0)$display("BOSS raster=%0d compact=%0d fetch=%0d disabled=%0d solid=%0d",rb,cb,fb,blank,solid);
 end
 always @(posedge clk)if(captured)
   $display("COLLECT valid=%b errors=%h fetch=%h raster=%h compact=%h raw_errors=%h raw_rows=%d mask=%h", valid_capture,errors,collector.fetch_errors,collector.raster_errors,collector.compact_errors,collector.patch_errors,collector.patch_count,core.native_display_mask);
 `endif
 task automatic scene_replay;
   int frames,count,writes,visible,starts;
   reg nonuniform;
   logic [63:0] colors;
   if(!$value$plusargs("frames=%d",frames))frames=8;
   if($test$plusargs("physical_slot"))begin
     $readmemh("physical.hex",checkpoint);
     @(negedge clk);pause_req=1;wait(paused);
     @(negedge clk);load_req=1;@(negedge clk);load_req=0;
     wait(restored);wait(!sleeping);wait(paused);
     if(loads!=WORDS)$fatal(1,"physical slot word count");
     @(negedge clk);pause_req=0;wait(!paused);
   end
   count=0;measuring=1;writes=0;visible=0;starts=0;colors=0;
   while(count<frames)begin
     @(posedge clk);
     if(mem.chr_changed)begin writes++;if(line_no>=8 && line_no<232)visible++;end
     if(ce && line_no>=8 && line_no<232 && dot>0 && dot<=256)colors[color]=1;
     if(gate)begin starts=scene_ready;end
     if(end_scene)begin
       $display("SCENE f=%0d eligible=%0d conflict=%0d CHR_write_clocks=%0d visible_write_clocks=%0d colors=%0d",count,starts,scene_conflict,writes,visible,$countones(colors));
       count++;writes=0;visible=0;starts=0;colors=0;
     end
   end
   $display("PASS FF3 physical scene replay");$finish;
 endtask
 initial begin
   fd=$fopen("prg.bin","rb"); if(!fd)$fatal(1,"missing ROM");
   n=$fread(prg,fd);$fclose(fd);if(n!=524288)$fatal(1,"wrong PRG size");
   repeat(8) @(negedge clk);cold_palette=live_palette;cold_mapper=live_mapper;
   foreach(cold_core[n])begin
     cold_core[n]=core_word(n);
     if(word_mask(n)!=0) check_core_word(n,cold_core[n]);
   end
   if($isunknown({cold_palette,cold_mapper})) $fatal(1,"undefined cold state");
   reset=0;wait(init_done);if(scene_mode)scene_replay();check_cold_cpu(0);
   // The 0x59 endpoint supplies zero on the four disabled header lanes.
   checkpoint[0]={32'd5316,32'd0};
   abort_partial_restore(2);abort_partial_restore(7);abort_partial_restore(20);
   abort_partial_restore(11,1);abort_partial_restore(10);abort_partial_restore(34);abort_partial_restore(36);
   foreach(loaded_word[i]) loaded_word[i]=0;
   loads=0;
   wait(prg_reads>100);
   $display("FF3 CPU active after scrub at %t",$time);$fflush();
   wait(chr_writes>0 && nt_writes>0);
   $display("FF3 wrote pattern and nametable at %t",$time);$fflush();
   begin : wait_for_artwork
     reg [63:0] seen_colors;
     seen_colors=0;
     while($countones(seen_colors)<3)begin
       @(posedge clk);
       if(ce && line_no==0 && dot==0)seen_colors=0;
       if(ce && line_no<240 && dot>=1 && dot<=256 && !$isunknown(color))
         seen_colors[color]=1;
     end
   end
   @(negedge clk);pause_req=1;wait(paused);
   // Verify a nonuniform battery payload across cold initialization and a full state restore.
   for(k=0;k<8192;k++)begin
     sram_image[k]=(k*97)^(k>>5);
     battery_byte(k,1,sram_image[k]);
   end
   for(k=0;k<8192;k++)battery_byte(k,0,sram_image[k]);
   @(negedge clk);battery=0;saved_palette=live_palette;saved_mapper=live_mapper;
   save_req=1;@(negedge clk);save_req=0;
   wait(sleeping);wait(!sleeping);if(saves!=WORDS)$fatal(1,"saved %d",saves);
   $display("FF3 serialized %d words",saves);$fflush();
   if(checkpoint[0][63:32]!==5316)$fatal(1,"bad size header");
   for(int bank=0;bank<4;bank++) for(int lane=0;lane<8;lane++)
     if(checkpoint[8+bank][8*lane+:8]!=={2'b00,saved_palette[6*(4*lane+bank)+:6]})
       $fatal(1,"palette save layout %0d/%0d",bank,lane);
   if({checkpoint[35],checkpoint[34],checkpoint[33]}!==saved_mapper)
     $fatal(1,"mapper save layout");
   verify_memory();
   if($test$plusargs("fatfs_roundtrip"))begin : file_service
     integer fd, invalid;
     logic [63:0] unknown_bits;
     invalid=0;
     fd=$fopen("core-state.hex","w");
     if(!fd)$fatal(1,"cannot write checkpoint");
     foreach(checkpoint[n])begin
       if($isunknown(checkpoint[n]))begin
         for(int b=0;b<64;b++)unknown_bits[b]=$isunknown(checkpoint[n][b]);
         if(invalid<64)$display("undefined checkpoint index=%0d mask=%016h",n,unknown_bits);
         invalid++;
       end
       $fdisplay(fd,"%016h",checkpoint[n]);
     end
     $fclose(fd);
     if(invalid)$fatal(1,"undefined checkpoint words %0d",invalid);
     if($system("python.exe ff3_disk_bridge.py")!=0)$fatal(1,"linked ARM save or load failed");
     // Clear the local copy so a missing or short disk result cannot pass.
     foreach(checkpoint[n])checkpoint[n]='x;
     $readmemh("restarted-state.hex",checkpoint);
     foreach(checkpoint[n])if($isunknown(checkpoint[n]))$fatal(1,"missing disk word %0d",n);
   end
   @(negedge clk);pause_req=0;wait(!paused);check_resumed_cpu(0);compare_resumed_picture(0);
   @(negedge clk);reset=1;pause_req=0;repeat(10)@(negedge clk);reset=0;wait(init_done);
   @(negedge clk);pause_req=1;wait(paused);battery_byte(1,0,0);
   @(negedge clk);battery=0;load_req=1;@(negedge clk);load_req=0;
   wait(restored);wait(!sleeping); if(loads!=WORDS)$fatal(1,"loaded %d",loads);
   wait(paused);
   verify_memory();
   for(k=0;k<8192;k++)battery_byte(k,0,sram_image[k]);
   @(negedge clk);battery=0;pause_req=0;wait(!paused);
   check_resumed_cpu(1);compare_resumed_picture(1);
   cancel_stream(0);cancel_stream(1);
   $display("PASS FF3 checkpoint words=%0d PRGreads=%0d CHRwrites=%0d NTwrites=%0d battery=8192",saves,prg_reads,chr_writes,nt_writes);
   $finish;
 end
 initial begin
   int target_frames;
   if(!$value$plusargs("frames=%d",target_frames))target_frames=8;
   repeat(target_frames>64?2*target_frames:78) begin
     repeat(350000) @(posedge clk);
     $display("FF3 at %t PRGreads=%0d CHRwrites=%0d NTwrites=%0d saves=%0d loads=%0d PA=%b line=%d addr=%h phase=%p",$time,prg_reads,chr_writes,nt_writes,saves,loads,paused,line_no,ca,alignment);$fflush();
   end
   $fatal(1,"checkpoint timed out");
 end
endmodule

