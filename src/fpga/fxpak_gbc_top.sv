// FXPAK Pro MK3 physical boundary for the replacement GBC core.
//
// This shell deliberately leaves the FPGA SD pins unowned.  The paired
// firmware loads the renderer, CGB boot image, game ROM, and SaveRAM through
// the standard MCU SPI memory commands.  sgb_feat[15] is asserted only after
// those payloads and masks have been installed, so the handheld core cannot
// execute partially loaded memory.
module fxpak_gbc_top(
 input wire CLKIN,
 input wire SNES_CIC_CLK,
 input wire[23:0]SNES_ADDR_IN,
 input wire SNES_READ_IN,SNES_WRITE_IN,SNES_ROMSEL_IN,SNES_CPU_CLK_IN,
 input wire SNES_REFRESH,SNES_SYSCLK,
 input wire[7:0]SNES_PA_IN,input wire SNES_PARD_IN,SNES_PAWR_IN,
 inout wire[7:0]SNES_DATA,
 output wire SNES_IRQ,SNES_DATABUS_OE,SNES_DATABUS_DIR,
 input wire SPI_MOSI,input wire SPI_SS,input wire SPI_SCK,inout wire SPI_MISO,
 output wire MCU_RDY,
 output wire[21:0]ROM_ADDR,output wire ROM_1CE,ROM_2CE,ROM_ZZ,
 output wire ROM_OE,ROM_WE,ROM_BHE,ROM_BLE,inout wire[15:0]ROM_DATA,
 output wire[18:0]RAM_ADDR,output wire RAM_OE,RAM_WE,inout wire[7:0]RAM_DATA,
 output wire DAC_MCLK,DAC_LRCK,DAC_SDOUT
);
 // The two core-domain guards already assert reset asynchronously while
 // either PLL is unlocked, then release it through a two-flop pipeline in the
 // destination clock domain.  Do not introduce a board-clock reset counter:
 // that would create a false synchronous path from 8 MHz into both PLL
 // domains and would also make reset removal dependent on unrelated clocks.
 wire power_reset=1'b0;

 wire core_clock,bus_clock,renderer_run,loader_reset;
 wire spi_cmd_ready,spi_param_ready,spi_endmessage,spi_startmessage;
 wire[7:0]spi_cmd_data,spi_param_data,spi_input_data,legacy_spi_data;
 wire legacy_miso,stream_miso,stream_payload,load_mode,load_primed,load_lock,load_inhibit;
 wire load_rx_valid,load_tx_take,load_valid,load_write,load_ready,load_response;
 wire[15:0]load_rx_data,load_tx_data,load_data,load_read_data;
 wire[22:0]load_addr;wire[7:0]load_status;
 wire[15:0]raw_features;
 wire[15:0]sgb_features={raw_features[15]&&!load_inhibit,raw_features[14:0]};
 assign SPI_MISO=SPI_SS?1'bz:(stream_payload?stream_miso:legacy_miso);
 // D5 latches an exit-only observation; D6..D8 read the same held bundle.
 wire[23:0]boot_observation;reg[31:0]boot_snapshot=0;
 (* async_reg="true" *)reg[1:0]observe_renderer_run=0;
 always @(posedge core_clock)begin
  if(loader_reset)observe_renderer_run<=0;
  else observe_renderer_run<={observe_renderer_run[0],renderer_run};
 end
 always @(posedge core_clock)begin
  if(loader_reset)boot_snapshot<=0;
  else if(spi_cmd_ready&&spi_cmd_data==8'hd5)
   boot_snapshot<={4'hc,raw_features[15],sgb_features[15],observe_renderer_run[1],load_inhibit,boot_observation};
 end
 wire[7:0]menu_command;wire[7:0]save_snapshot_status;wire[31:0]save_generation,save_snapshot_generation;
 reg[31:0]save_observation=0;
 always @(posedge core_clock)begin
  if(loader_reset)save_observation<=0;
  else if(spi_cmd_ready&&spi_cmd_data==8'hd9)save_observation<=save_generation;
  else if(spi_cmd_ready&&spi_cmd_data==8'he0)save_observation<=save_snapshot_generation;
 end
 assign spi_input_data=spi_cmd_data==8'he4 ?menu_command:(spi_cmd_data==8'hd9||spi_cmd_data==8'he0)?save_observation[7:0]:
 (spi_cmd_data==8'hda||spi_cmd_data==8'he1)?save_observation[15:8]:
 (spi_cmd_data==8'hdb||spi_cmd_data==8'he2)?save_observation[23:16]:
 (spi_cmd_data==8'hdc||spi_cmd_data==8'he3)?save_observation[31:24]:
 spi_cmd_data==8'hde ?save_snapshot_status:spi_cmd_data==8'hd5 ?boot_snapshot[7:0]:
  spi_cmd_data==8'hd6 ?boot_snapshot[15:8]:spi_cmd_data==8'hd7 ?boot_snapshot[23:16]:
  spi_cmd_data==8'hd8 ?boot_snapshot[31:24]:
  spi_cmd_data==8'hd4 ?8'hdf:spi_cmd_data==8'hd3 ?load_status:legacy_spi_data;
 wire[31:0]spi_byte_count;wire[2:0]spi_bit_count;
 gbc_spi mcu_spi(core_clock,SPI_SCK,SPI_MOSI,legacy_miso,SPI_SS,
  spi_cmd_ready,spi_param_ready,spi_cmd_data,spi_param_data,
  spi_endmessage,spi_startmessage,spi_input_data,spi_byte_count,spi_bit_count);

 wire mcu_rrq,mcu_wrq,mcu_write,mcu_completion;
 wire[3:0]cart_mapper;
 wire[23:0]mcu_address,rom_mask;wire[16:0]ram_mask;
 wire[7:0]mcu_write_data,mcu_read_data;

 wire diagnostic_access=mcu_address[23:16]==8'hf0;
 wire[7:0]diagnostic_data;
 reg[1:0]diagnostic_pending=0;reg diagnostic_selected=0;
 always @(posedge core_clock)begin
  if(loader_reset)begin diagnostic_pending<=0;diagnostic_selected<=0;end
  else begin
   diagnostic_pending<={diagnostic_pending[0],(mcu_rrq||mcu_wrq)&&diagnostic_access};
   if(mcu_rrq||mcu_wrq)diagnostic_selected<=diagnostic_access;
  end
 end
 wire renderer_access=mcu_address[23:19]==5'b10001;
 wire psram_completion,renderer_completion;
 wire[7:0]psram_read_data,renderer_read_data;
 reg renderer_selected=0;
 always @(posedge core_clock)
  if(mcu_rrq||mcu_wrq)renderer_selected<=renderer_access;
 assign mcu_completion=psram_completion||renderer_completion||diagnostic_pending[1];
 assign mcu_read_data=diagnostic_selected?(sgb_features[15]?8'hff:diagnostic_data):renderer_selected?renderer_read_data:psram_read_data;
 wire[18:0]core_ram_addr,loader_ram_addr;
 wire core_ram_oe,core_ram_we,loader_ram_oe,loader_ram_we;
 gbc_sram_loader renderer_loader(core_clock,bus_clock,sgb_features[15]||raw_features[14],
  mcu_rrq&&renderer_access,mcu_wrq&&renderer_access,mcu_address[18:0],mcu_write_data,
  renderer_completion,renderer_read_data,renderer_run,loader_ram_addr,loader_ram_oe,loader_ram_we,RAM_DATA);
 assign RAM_ADDR=renderer_run?core_ram_addr:loader_ram_addr;
 assign RAM_OE=renderer_run?core_ram_oe:loader_ram_oe;
 assign RAM_WE=renderer_run?core_ram_we:loader_ram_we;
 reg mcu_ready_level=1'b1;
 always @(posedge core_clock)begin
  if(mcu_rrq||mcu_wrq)mcu_ready_level<=1'b0;
  else if(mcu_completion)mcu_ready_level<=1'b1;
 end
 assign MCU_RDY=load_mode?load_primed:mcu_ready_level;
 gbc_load_spi load_spi(core_clock,loader_reset,SPI_SCK,SPI_SS,SPI_MOSI,load_mode,
  load_tx_data,stream_miso,stream_payload,load_rx_valid,load_rx_data,load_tx_take);
 gbc_load_duplex load_engine(core_clock,loader_reset,raw_features[15],spi_cmd_ready,spi_cmd_data,spi_endmessage,spi_byte_count,
  load_rx_valid,load_rx_data,load_tx_take,load_tx_data,load_mode,load_primed,load_lock,load_inhibit,
  load_status,load_valid,load_write,load_addr,load_data,load_ready,load_response,load_read_data);

 gbc_mcu_cmd command_decoder(core_clock,spi_cmd_ready,spi_param_ready,
  spi_cmd_data,spi_param_data,spi_byte_count,mcu_ready_level,mcu_read_data,
  mcu_rrq,mcu_wrq,mcu_write_data,legacy_spi_data,mcu_address,rom_mask,raw_features,ram_mask,cart_mapper);
 assign mcu_write=1'b1;

 wire[7:0]snes_data_out;
 wire snes_oe_n;
 wire capture_error,snes_slot_error,sram_slot_error,bus_error;
 wire upload_busy,upload_done,mcu_adapter_ready;
 wire[7:0]foreground_data;
 wire[15:0]audio_l,audio_r,word_data;
 wire[14:0]pixel_rgb,palette_rgb;
 wire[16:0]save_address;
 wire[7:0]save_write_data,palette_after_row;
 wire[6:0]fifo_level;wire[5:0]palette_slot;wire[3:0]capture_error_code;
 wire[1:0]processing_bank;
 wire[15:0]word_addr;
 wire pixel_valid,lcd_on,lcd_vsync,speed,dma_active,rom_not_ready;
 wire capture_active,capture_done,sram_busy,save_read,save_write;
 wire front_page,front_valid,published,word_valid,palette_valid,palette_initial;

 full_core_link core(
  .menu_command(menu_command),.menu_reply_write(spi_param_ready&&spi_cmd_data==8'he5&&spi_byte_count==2),.menu_reply_data(spi_param_data),
  .save_snapshot_start(spi_cmd_ready&&spi_cmd_data==8'hdd),.save_snapshot_status(save_snapshot_status),.save_generation(save_generation),.save_snapshot_generation(save_snapshot_generation),
  .load_ui_active(raw_features[14]&&!raw_features[15]),.load_ui_status(raw_features[7:0]),
  .diag_addr(mcu_address[15:0]),.diag_data(diagnostic_data),
  .CLKIN(CLKIN),.reset(power_reset),.run_core(sgb_features[15]),
  .capture_start(sgb_features[15]),.mcu_clock(core_clock),.loader_clock(bus_clock),
  .loader_reset(loader_reset),.boot_observation(boot_observation),.load_lock(load_lock),.load_valid(load_valid),.load_write(load_write),
  .load_addr(load_addr),.load_data(load_data),.load_ready(load_ready),.load_response(load_response),.load_read_data(load_read_data),
  .snes_phi(SNES_CPU_CLK_IN),.snes_read_n(SNES_READ_IN||!renderer_run),
  .snes_write_n(SNES_WRITE_IN||!renderer_run),.snes_romsel_n(SNES_ROMSEL_IN),
  .snes_address(SNES_ADDR_IN),.snes_slot_error(snes_slot_error),
  .foreground_data(foreground_data),.sram_busy(sram_busy),
  .sram_slot_error(sram_slot_error),.RAM_ADDR(core_ram_addr),.RAM_OE(core_ram_oe),
  .RAM_WE(core_ram_we),.RAM_DATA(RAM_DATA),.joystick(8'h00),
  .mcu_rrq(mcu_rrq&&!renderer_access&&!diagnostic_access),.mcu_wrq(mcu_wrq&&!renderer_access&&!diagnostic_access),.mcu_addr(mcu_address),
  .mcu_data_out(mcu_write_data),.mcu_rq_rdy(psram_completion),
  .mcu_data_in(psram_read_data),.cart_mapper(cart_mapper),.rom_bank_mask(rom_mask[22:14]),.ram_mask(ram_mask),
  .boot_download(1'b0),.boot_wr(1'b0),.boot_addr(25'h0),.boot_data(16'h0),
  .save_address(save_address),.save_write_data(save_write_data),
  .save_read(save_read),.save_write(save_write),.audio_l(audio_l),.audio_r(audio_r),
  .DAC_MCLK(DAC_MCLK),.DAC_LRCK(DAC_LRCK),.DAC_SDOUT(DAC_SDOUT),
  .pixel_valid(pixel_valid),.pixel_rgb(pixel_rgb),.lcd_on(lcd_on),
  .lcd_vsync(lcd_vsync),.speed(speed),.dma_active(dma_active),
  .rom_not_ready(rom_not_ready),.capture_active(capture_active),
  .capture_done(capture_done),.capture_error(capture_error),
  .capture_error_code(capture_error_code),.upload_busy(upload_busy),
  .upload_done(upload_done),.bus_error(bus_error),.snes_data_in(SNES_DATA),
  .snes_databus_oe_n(snes_oe_n),.snes_databus_dir(SNES_DATABUS_DIR),
  .front_page(front_page),.front_valid(front_valid),.published(published),
  .word_ready(1'b1),.word_valid(word_valid),.palette_valid(palette_valid),
  .palette_initial(palette_initial),.word_addr(word_addr),.palette_rgb(palette_rgb),
  .word_data(word_data),.palette_after_row(palette_after_row),
  .palette_slot(palette_slot),.processing_bank(processing_bank),
  .fifo_level(fifo_level),.ROM_ADDR(ROM_ADDR),.ROM_1CE(ROM_1CE),
  .ROM_2CE(ROM_2CE),.ROM_OE(ROM_OE),.ROM_WE(ROM_WE),
  .ROM_BHE(ROM_BHE),.ROM_BLE(ROM_BLE),.ROM_DATA(ROM_DATA));

 assign SNES_DATA=!snes_oe_n?snes_data_out:8'hzz;
 assign snes_data_out=foreground_data;
 assign SNES_DATABUS_OE=snes_oe_n;
 assign SNES_IRQ=1'b0;
 assign ROM_ZZ=1'b1;

 // Explicitly consume board inputs that are intentionally not part of this
 // core so synthesis reports cannot disguise accidental floating outputs.
 wire unused_inputs=&{1'b0,SNES_CIC_CLK,SNES_REFRESH,SNES_PA_IN,
                      SNES_PARD_IN,SNES_PAWR_IN,spi_endmessage,
                      spi_startmessage,mcu_write,capture_error,bus_error};
endmodule
