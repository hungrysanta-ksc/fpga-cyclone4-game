// Integration candidate, NOT loadable firmware. Loader and save RAM are ports.
module full_core_link(
 output wire[7:0]menu_command,input wire menu_reply_write,input wire[7:0]menu_reply_data,
 input wire save_snapshot_start,output wire[7:0]save_snapshot_status,output wire[31:0]save_generation,save_snapshot_generation,
 input wire load_ui_active,input wire[7:0]load_ui_status,
 input wire[15:0]diag_addr,output wire[7:0]diag_data,

 input wire CLKIN,reset,run_core,capture_start,
 output wire mcu_clock,loader_clock,loader_reset,output wire[23:0]boot_observation,
 input wire load_lock,load_valid,load_write,input wire[22:0]load_addr,input wire[15:0]load_data,
 output wire load_ready,load_response,output wire[15:0]load_read_data,
 input wire snes_phi,snes_read_n,snes_write_n,snes_romsel_n,input wire[23:0]snes_address,
 output wire snes_slot_error,
 output wire[7:0]foreground_data,output wire sram_busy,sram_slot_error,
 output wire[18:0]RAM_ADDR,output wire RAM_OE,RAM_WE,inout wire[7:0]RAM_DATA,
 input wire[7:0]joystick,
 input wire mcu_rrq,mcu_wrq,input wire[23:0]mcu_addr,input wire[7:0]mcu_data_out,
 output wire mcu_rq_rdy,output wire[7:0]mcu_data_in,
 input wire[3:0]cart_mapper,input wire[8:0]rom_bank_mask,input wire[16:0]ram_mask,
 input wire boot_download,boot_wr,input wire[24:0]boot_addr,input wire[15:0]boot_data,
 output wire[16:0]save_address,output wire[7:0]save_write_data,
 output wire save_read,save_write,
 output wire[15:0]audio_l,audio_r,
 output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT,
 output wire pixel_valid,output wire[14:0]pixel_rgb,
 output wire lcd_on,lcd_vsync,speed,dma_active,rom_not_ready,
 output wire capture_active,capture_done,capture_error,output wire[3:0]capture_error_code,
 output wire upload_busy,upload_done,bus_error,
 input wire[7:0]snes_data_in,output wire snes_databus_oe_n,snes_databus_dir,
 output wire front_page,front_valid,published,
 input wire word_ready,output wire word_valid,palette_valid,palette_initial,
 output wire[15:0]word_addr,output wire[14:0]palette_rgb,output wire[15:0]word_data,
 output wire[7:0]palette_after_row,output wire[5:0]palette_slot,output wire[1:0]processing_bank,
 output wire[6:0]fifo_level,
 output wire[21:0]ROM_ADDR,output wire ROM_1CE,ROM_2CE,ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,
 inout wire[15:0]ROM_DATA);
 wire rtc_dirty,rtc_watchdog_tick;
 wire metadata_ready,metadata_valid,metadata_word,committed_frame;wire[15:0]metadata_addr,metadata_data;
 wire clk,locked,logic_reset,bus_clk,bus_locked,source_page,source_front_valid;
 gbc_bus_pll0 bus_pll(reset,CLKIN,bus_clk,bus_locked);
 gbc_pll0 pll(.areset(reset),.inclk0(CLKIN),.c0(clk),.locked(locked));
 assign mcu_clock=clk;
 assign loader_clock=bus_clk;
 assign loader_reset=logic_reset;
 clock_reset_guard guard(clk,reset,locked&&bus_locked,logic_reset);
 wire save_pause,snap_valid,snap_write,snap_ready,snap_rsp;
 wire[22:0]snap_addr;wire[15:0]snap_data,snap_rdata;
 gbc_save_snapshot save_snapshot(clk,logic_reset,run_core,save_snapshot_start,ram_mask,
  (save_req_valid&&save_req_ready&&save_req_write)||rtc_dirty,save_client_busy,
  save_pause,save_snapshot_status,save_generation,save_snapshot_generation,
  snap_valid,snap_write,snap_addr,snap_data,snap_ready,snap_rsp,snap_rdata,rtc_enabled,mcu_rrq&&rtc_access&&mcu_addr[3:0]==15,rtc_watchdog_tick);
 wire menu_write;wire[7:0]menu_data,menu_status,menu_flags;
 gbc_menu_mailbox menu_link(clk,bus_clk,logic_reset,menu_write,menu_data,menu_status,
 menu_command,menu_reply_write,menu_reply_data,menu_flags);
 wire core_reset;wire host_upload_boundary;
 gbc_host_start_guard startup(clk,logic_reset,run_core,capture_active,host_upload_boundary,core_reset);
 wire[14:0]cart_addr,lcd_data;wire a15,rd,wr,ncs,phi,sdram_rd,lcd_clkena,ppu_ce,audio_ce,cart_guard_ce;
 wire[7:0]cart_out,cart_in;wire[1:0]lcd_gb,lcd_mode;
 wire save_req_valid,save_req_write,save_req_ready,save_rsp_valid;
 wire save_client_busy,save_client_completed,save_timing_error;
 wire[16:0]save_req_addr;wire[7:0]save_req_data,save_client_data,save_rsp_data;
 wire mcu_req_valid,mcu_req_write,mcu_req_ready,mcu_rsp_valid,mcu_busy,mcu_error;
 wire[23:0]mcu_req_addr;wire[7:0]mcu_req_data,mcu_rsp_data;
 gbc_save_client save_client(clk,logic_reset,save_read,save_write,save_address,save_write_data,
  save_client_data,save_client_busy,save_client_completed,save_timing_error,
  save_req_valid,save_req_write,save_req_addr,save_req_data,
  save_req_ready,save_rsp_valid,save_rsp_data);
 wire session_locked,session_seek,session_hold,session_access,session_writes,session_drain,session_flush,session_start;
 wire video_state_safe,output_state_drained;wire[7:0]session_status;
 wire session_control=mcu_addr==24'hf10801;
 reg session_reply,session_selected;reg[7:0]session_rdata;
 always @(posedge clk)begin
  if(core_reset)begin session_reply<=0;session_selected<=0;session_rdata<=0;end
  else begin
   session_reply<=(mcu_rrq||mcu_wrq)&&session_control;
   if(mcu_rrq||mcu_wrq)session_selected<=session_control;
   if((mcu_rrq||mcu_wrq)&&session_control)session_rdata<=session_status;
  end
 end
 gbc_state_session session(clk,core_reset,mcu_wrq&&session_control,mcu_data_out,
  menu_flags[7],video_state_safe,state_paused,state_io_busy,
  cap_req&&cap_ready,cap_rsp,audio_req&&audio_ready,audio_rsp,
  output_state_drained,capture_active,
  session_locked,session_seek,session_hold,session_access,session_writes,
  session_drain,session_flush,session_start,session_status,rtc_watchdog_tick);
 reg session_access_q;
 always @(posedge clk)begin
  if(core_reset)session_access_q<=0;
  else session_access_q<=session_access;
 end
 wire state_access=mcu_addr[23:16]==8'hf1;
 wire state_done,state_error,psram_mcu_done;wire[7:0]state_rdata,psram_mcu_rdata;
 reg state_selected;wire[9:0]state_addr;wire[63:0]state_data,state_read,state_ext_read;
 wire state_commit,state_mem_active,state_mem_write;wire[1:0]state_mem_sel;wire[14:0]state_mem_addr;wire[7:0]state_mem_read;
 reg[4:0]state_quiet_count;
 wire state_io_busy;reg state_rom_pending;
 wire core_pause=save_pause||(menu_flags[7]&&!session_seek)||session_hold||state_io_busy;
 wire state_paused=&state_quiet_count;
 always @(posedge clk)begin
  if(core_reset)begin state_selected<=0;state_quiet_count<=0;state_rom_pending<=0;end
  else begin
   if(mcu_rrq||mcu_wrq)state_selected<=state_access;
   if(request&&ready)state_rom_pending<=1;
   if(response)state_rom_pending<=0;
   if(!core_pause||session_seek||ppu_ce||cart_guard_ce||save_client_busy||request||state_rom_pending)state_quiet_count<=0;
   else if(!state_paused)state_quiet_count<=state_quiet_count+1'b1;
  end
 end
 wire rtc_access=mcu_addr[23:16]==8'hf2;
 wire rtc_done;wire[7:0]rtc_result;reg rtc_selected;
 always @(posedge clk)if(mcu_rrq||mcu_wrq)rtc_selected<=rtc_access;
 assign mcu_rq_rdy=session_reply||state_done||psram_mcu_done||rtc_done;
 assign mcu_data_in=rtc_selected?rtc_result:session_selected?session_rdata:state_selected?state_rdata:psram_mcu_rdata;
 gbc_state_io state_io(clk,core_reset,session_access_q,session_writes,mcu_rrq&&state_access&&!session_control,mcu_wrq&&state_access&&!session_control,
  mcu_addr[15:0],mcu_data_out,state_io_busy,state_done,state_rdata,state_error,state_addr,state_data,state_commit,state_read,
  state_mem_active,state_mem_sel,state_mem_addr,state_mem_write,state_mem_read);
 mcu_psram_client mcu_client(clk,logic_reset,mcu_rrq&&!state_access&&!rtc_access,mcu_wrq&&!state_access&&!rtc_access,mcu_addr,mcu_data_out,
  psram_mcu_done,psram_mcu_rdata,mcu_busy,mcu_error,mcu_req_valid,mcu_req_write,mcu_req_addr,mcu_req_data,
  mcu_req_ready,mcu_rsp_valid,mcu_rsp_data);
 wire serial_clk,serial_data;wire fast_active,keep_pixels,raw_pixel_valid;
 wire debug_boot,debug_fetch;
 wire[4:0]debug_state;wire[23:0]fault_context;wire[4:0]fault_stage;
 gbc_live_core core(.fast_requested(joystick_core[8]&&!menu_flags[7]&&!session_locked),.save_busy(save_client_busy),.video_restart(session_flush),.fast_active(fast_active),.keep_pixels(keep_pixels),.state_safe(video_state_safe),.state_addr(state_addr),.state_data(state_data),.state_commit(state_commit),
 .state_mem_active(state_mem_active),.state_mem_sel(state_mem_sel),.state_mem_addr(state_mem_addr),.state_mem_write(state_mem_write),
 .state_read(state_read),.state_mem_read(state_mem_read),.state_ext_read(state_ext_read),.pause_core(core_pause),.cart_ready(hit),.diag_addr(diag_addr),.diag_data(diag_data),.debug_boot(debug_boot),.debug_fetch(debug_fetch),.clk_sys(clk),.reset(core_reset),.joystick((menu_flags[7]||session_locked)?8'b0:joystick_core[7:0]),.cart_do(cart_in),
 .cart_oe(!a15||ram_enabled),.real_cgb_boot(1'b0),.serial_clk_in(1'b1),.serial_data_in(1'b1),
 .boot_download(boot_download),.boot_wr(boot_wr),.boot_addr(boot_addr),.boot_data(boot_data),
 .ext_bus_addr(cart_addr),.ext_bus_a15(a15),.cart_rd(rd),.cart_wr(wr),.cart_di(cart_out),
 .nCS(ncs),.PHI(phi),.sdram_rd(sdram_rd),.audio_l(audio_l),.audio_r(audio_r),.audio_ce(audio_ce),
 .lcd_clkena(lcd_clkena),.lcd_data(lcd_data),.lcd_data_gb(lcd_gb),.lcd_mode(lcd_mode),
 .lcd_on(lcd_on),.lcd_vsync(lcd_vsync),.speed(speed),.serial_clk_out(serial_clk),.serial_data_out(serial_data),
 .ppu_ce(ppu_ce),.cart_guard_ce(cart_guard_ce),.dma_active(dma_active));
 // C41: runtime cartridge selection; MBC5 register/state bits stay compatible.
 wire mbc1=cart_mapper[2:0]==3'd1;
 wire mbc3=cart_mapper[2:0]==3'd3;
 wire rtc_enabled=mbc3&&cart_mapper[3];
 wire rtc_chosen=mbc3&&ram_bank>=8&&ram_bank<=12;
 wire ram_chosen=!mbc3||ram_bank<4;
 wire[28:0]rtc_state;wire[7:0]rtc_cart_read;
 wire[6:0]low_bank_value=mbc1?{2'b0,cart_out[4:0]}:cart_out[6:0];
 reg[8:0]rom_bank;reg[3:0]ram_bank;reg ram_enabled,old_wr,mbc1_mode;
 always @(posedge clk)begin
  if(core_reset)begin rom_bank<=1;ram_bank<=0;ram_enabled<=0;old_wr<=0;mbc1_mode<=0;end
  else if(state_commit&&state_addr==32)begin rom_bank<=state_data[8:0];ram_bank<=state_data[12:9];ram_enabled<=state_data[13];old_wr<=state_data[14];mbc1_mode<=state_data[15];end
  else if(!state_paused)begin
   old_wr<=wr;
   if(wr&&!old_wr&&!a15)case(cart_addr[14:12])
    0,1:ram_enabled<=(cart_out[3:0]==4'ha)&&((|ram_mask)||rtc_enabled);
    2,3:if(mbc1||mbc3)rom_bank<={2'b0,(low_bank_value==0?7'd1:low_bank_value)};
        else if(!cart_addr[12])rom_bank[7:0]<=cart_out;
        else rom_bank[8]<=cart_out[0];
    4,5:ram_bank<=mbc1?{2'b0,cart_out[1:0]}:cart_out[3:0];
    6,7:if(mbc1)mbc1_mode<=cart_out[0];
   endcase
  end
 end
 // Bit15 was zero/reserved in C35..C40. MBC5 saved fields retain their positions.
 assign state_ext_read=state_addr==32?{19'b0,(rtc_enabled?rtc_state:29'b0),mbc1_mode,old_wr,ram_enabled,ram_bank,rom_bank}:64'b0;
 wire[3:0]selected_ram_bank=mbc1?(mbc1_mode?ram_bank:4'b0):ram_bank;
 assign save_address={selected_ram_bank,cart_addr[12:0]} & ram_mask;assign save_write_data=cart_out;
 assign save_read=ram_chosen&&(|ram_mask)&&!state_paused&&ram_enabled&&a15&&!ncs&&!cart_addr[14]&&rd;
 assign save_write=ram_chosen&&(|ram_mask)&&!state_paused&&ram_enabled&&a15&&!ncs&&!cart_addr[14]&&wr;
 gbc_mbc3_rtc rtc(clk,logic_reset,run_core,rtc_enabled,core_reset,
  !core_reset&&!state_paused&&wr&&!old_wr&&!a15&&cart_addr[14:13]==2'b11,cart_out,
  !core_reset&&!state_paused&&wr&&!old_wr&&ram_enabled&&rtc_chosen&&a15&&!ncs&&!cart_addr[14],ram_bank,rtc_cart_read,
  !run_core||save_pause,mcu_rrq&&rtc_access,mcu_wrq&&rtc_access,mcu_addr[3:0],mcu_data_out,rtc_done,rtc_result,
  state_commit&&state_addr==32,state_data,rtc_state,rtc_dirty,rtc_watchdog_tick);
 // MBC1M uses four low address bits; the zero test above still uses all five.
 wire[8:0]mbc1_upper=cart_mapper[3]?{3'b0,ram_bank[1:0],4'b0}:{2'b0,ram_bank[1:0],5'b0};
 wire[8:0]mbc1_lower={4'b0,(cart_mapper[3]?{1'b0,rom_bank[3:0]}:rom_bank[4:0])};
 wire[8:0]selected_rom_bank=mbc1?
  ((cart_addr[14]?mbc1_upper|mbc1_lower:(mbc1_mode?mbc1_upper:9'b0))&rom_bank_mask):
  (cart_addr[14]?(rom_bank&rom_bank_mask):9'b0);
 wire[21:0]tag={selected_rom_bank,cart_addr[13:1]};
 wire[7:0]rom_byte;wire request,ready,response,hit;wire[21:0]request_addr;wire[15:0]response_data;
 rom_prefetch cache(clk,core_reset,!a15&&!state_paused,tag,cart_addr[0],request,ready,request_addr,response,response_data,hit,rom_byte);
 assign cart_in=!a15?rom_byte:rtc_chosen?rtc_cart_read:ram_chosen?save_client_data:8'hff;
 assign rom_not_ready=!a15&&rd&&!hit; // Status only; not proof of a CPU sample miss.
 ppu_stream stream(clk,core_reset||session_flush,ppu_ce,lcd_on,lcd_clkena,lcd_data,raw_pixel_valid,pixel_rgb);
 assign pixel_valid=raw_pixel_valid&&keep_pixels;
 wire cap_req,cap_write,cap_ready,cap_rsp;
 wire audio_delay_protocol_error,audio_delay_overrun;
 wire[22:0]cap_word_addr;wire[15:0]cap_data,cap_response;
 wire palette_ready,pipeline_error,metadata_error;
 wire[3:0]pipeline_error_code;
 assign capture_error=pipeline_error||metadata_error||save_timing_error||mcu_error||audio_delay_protocol_error||audio_delay_overrun;
 assign capture_error_code=audio_delay_overrun?4'd13:audio_delay_protocol_error?4'd12:mcu_error?4'd11:save_timing_error?4'd10:metadata_error?4'd9:pipeline_error_code;
 wire pixel_write_valid,pixel_write_ready;
 wire[14:0]pixel_write_addr;wire[15:0]pixel_write_data;
 wire upload_boundary;
 wire[9:0]host_joy_update;
 board_output_ring3_link output_pages(clk,bus_clk,logic_reset,capture_done,lcd_on,pixel_valid&&capture_active,processing_bank,
 pixel_write_valid,pixel_write_addr,pixel_write_data,pixel_write_ready,
 palette_valid,palette_initial,palette_after_row,palette_slot,palette_rgb,palette_ready,
 upload_boundary,read_idle,upload_busy,upload_done,front_page,front_valid,frontend_upload_error,
 metadata_valid,metadata_ready,metadata_addr,metadata_data,metadata_word,committed_frame,source_page,source_front_valid,published,metadata_error,host_upload_boundary,session_flush,session_drain,output_state_drained);
 wire read_idle,frontend_upload_error;wire[9:0]joy_update;wire[8:0]joystick_core;
 joypad_cdc joy_transfer(clk,logic_reset,joy_update,joystick_core);
 // Seen flags persist for this FPGA configuration; count is not a game FPS.
 wire[7:0]diag_live={core_reset,rom_not_ready,source_front_valid,capture_active,
                     pixel_valid,lcd_on,debug_boot,run_core};
 reg[7:0]diag_seen;reg[3:0]diag_error;
 always @(posedge clk)begin
  if(logic_reset)begin diag_seen<=0;diag_error<=0;end
  else if(run_core)begin
   diag_seen<=diag_seen|{capture_error,published,committed_frame,capture_done,
                        pixel_valid,lcd_on,!core_reset&&!debug_boot,!core_reset&&debug_fetch};
   if(capture_error&&!diag_seen[7])diag_error<=capture_error_code;
  end
 end
 // Exit-only observation: seen flags, live startup flags, first error and pipeline state.
 assign boot_observation={diag_seen,diag_live,diag_error,debug_state[3:0]};
 gbc_fault_stage stage_probe(clk,logic_reset,run_core&&capture_error&&!diag_seen[7],debug_state,fault_stage);
 wire diag_request,diag_busy,diag_valid;wire[31:0]diag_snapshot;
 gbc_diagnostic_snapshot diagnostic(clk,bus_clk,logic_reset,
  load_ui_active ? {8'h26,16'b0,load_ui_status} : {3'b0,fault_stage,4'b0,diag_error,fault_context[15:0]},
  diag_request,diag_busy,diag_valid,diag_snapshot);
 snes_frontend host_frontend(menu_write,menu_data,menu_status,bus_clk,logic_reset,snes_phi,snes_address,
 snes_read_n,snes_write_n,snes_romsel_n,snes_data_in,foreground_data,snes_databus_oe_n,snes_databus_dir,
 upload_boundary,read_idle,upload_busy,upload_done,front_page,front_valid,frontend_upload_error,
 metadata_valid,metadata_addr,metadata_data,metadata_word,metadata_ready,sram_busy,bus_error,
 RAM_ADDR,RAM_OE,RAM_WE,RAM_DATA,joy_update,diag_request,diag_busy,diag_valid,diag_snapshot);
 assign snes_slot_error=bus_error;assign sram_slot_error=bus_error;
 assign word_valid=0;assign word_addr=0;assign word_data=0;

 frame_pipeline_ring3 pipeline(clk,logic_reset||session_flush,capture_start||session_start,lcd_on,pixel_valid,pixel_rgb,
 capture_active,fifo_level,pipeline_error,pipeline_error_code,
 cap_req,cap_write,cap_word_addr,cap_data,cap_ready,cap_rsp,cap_response,
 pixel_write_valid,pixel_write_ready,pixel_write_addr,pixel_write_data,palette_valid,palette_ready,
 palette_initial,palette_after_row,palette_slot,palette_rgb,capture_done,processing_bank,debug_state,fault_context);
 wire audio_req,audio_write,audio_ready,audio_rsp;
 wire[22:0]audio_req_addr;wire[15:0]audio_req_data,audio_rsp_data;
 wire bg_req,bg_write,bg_ready,bg_rsp;wire[22:0]bg_addr;wire[15:0]bg_data,bg_response;
 wire cap_gate_ready,audio_gate_ready;
 assign cap_ready=cap_gate_ready&&!session_drain;
 assign audio_ready=audio_gate_ready&&!session_drain;
 psram_bg_arbiter bg_arbiter(clk,logic_reset,
  cap_req&&!session_drain,cap_write,cap_word_addr,cap_data,cap_gate_ready,cap_rsp,cap_response,
  audio_req&&!session_drain,audio_write,audio_req_addr,audio_req_data,audio_gate_ready,audio_rsp,audio_rsp_data,
  bg_req,bg_write,bg_addr,bg_data,bg_ready,bg_rsp,bg_response);
 wire boot_bg_valid,boot_bg_write,boot_bg_ready,boot_bg_rsp;
 wire[22:0]boot_bg_addr;wire[15:0]boot_bg_data,boot_bg_response;
 gbc_load_bus_mux load_mux(clk,logic_reset,load_lock,
  load_valid,load_write,load_addr,load_data,load_ready,load_response,load_read_data,
  bg_req,bg_write,bg_addr,bg_data,bg_ready,bg_rsp,bg_response,
  boot_bg_valid,boot_bg_write,boot_bg_addr,boot_bg_data,boot_bg_ready,boot_bg_rsp,boot_bg_response);
 wire merged_valid,merged_write,merged_ready,merged_rsp;wire[22:0]merged_addr;wire[15:0]merged_data,merged_rdata;
 psram_bg_arbiter snapshot_mux(clk,logic_reset,
  boot_bg_valid,boot_bg_write,boot_bg_addr,boot_bg_data,boot_bg_ready,boot_bg_rsp,boot_bg_response,
  snap_valid,snap_write,snap_addr,snap_data,snap_ready,snap_rsp,snap_rdata,
  merged_valid,merged_write,merged_addr,merged_data,merged_ready,merged_rsp,merged_rdata);
 rom_bus_bridge_save bridge(clk,logic_reset,!cart_guard_ce||load_lock,
  save_req_valid,save_req_write,save_req_addr,save_req_data,save_req_ready,save_rsp_valid,save_rsp_data,
  request,request_addr,ready,response,response_data,
  mcu_req_valid,mcu_req_write,mcu_req_addr,mcu_req_data,mcu_req_ready,mcu_rsp_valid,mcu_rsp_data,
  merged_valid,merged_write,merged_addr,merged_data,merged_ready,merged_rsp,merged_rdata,
  ROM_ADDR,ROM_1CE,ROM_2CE,ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,ROM_DATA);
 gbc_dac_psram dac_output(
  // The clock enable runs while the CPU is reset. Do not enqueue audio
  // until the host/capture guards release the CPU; boot DMA owns PSRAM.
  .mute(menu_flags[7]||menu_flags[1]||session_locked||fast_active),.clk_audio(clk),.reset_audio(logic_reset||session_flush),.audio_ce(audio_ce&&!core_reset&&!session_drain&&!fast_active),
  .audio_l(audio_l),.audio_r(audio_r),.clk_dac(bus_clk),
  .DAC_MCLK(DAC_MCLK),.DAC_LRCK(DAC_LRCK),.DAC_SDOUT(DAC_SDOUT),
  .req_valid(audio_req),.req_write(audio_write),.req_addr(audio_req_addr),.req_wdata(audio_req_data),
  .req_ready(audio_ready),.rsp_valid(audio_rsp),.rsp_rdata(audio_rsp_data),
  .delay_protocol_error(audio_delay_protocol_error),.delay_sample_overrun(audio_delay_overrun));
endmodule
