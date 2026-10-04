// Resource probe only: no board pins, ROM service, SNES bridge or bitstream.
// Keeps upstream GBC CPU/PPU/APU and RAM. Optional UI features are tied off.
module gbc_live_core (
 output wire state_safe,
 input wire[9:0]state_addr,input wire[63:0]state_data,input wire state_commit,
 input wire state_mem_active,input wire[1:0]state_mem_sel,input wire[14:0]state_mem_addr,input wire state_mem_write,
 output wire[63:0]state_read,output wire[7:0]state_mem_read,input wire[63:0]state_ext_read,

 input wire pause_core,fast_requested,save_busy,video_restart,
 output wire fast_active,keep_pixels,
 input wire cart_ready,
 input wire[15:0]diag_addr,output wire[7:0]diag_data,

 output wire debug_boot,debug_fetch,
    input wire clk_sys, reset,
    input wire [7:0] joystick, cart_do,
    input wire cart_oe, real_cgb_boot,
    input wire serial_clk_in, serial_data_in,
    input wire boot_download, boot_wr,
    input wire [24:0] boot_addr,
    input wire [15:0] boot_data,
    output wire [14:0] ext_bus_addr,
    output wire ext_bus_a15, cart_rd, cart_wr,
    output wire [7:0] cart_di,
    output wire nCS, PHI, sdram_rd,
    output wire [15:0] audio_l, audio_r,
    output wire audio_ce,
    output wire lcd_clkena,
    output wire [14:0] lcd_data,
    output wire [1:0] lcd_data_gb, lcd_mode,
    output wire lcd_on, lcd_vsync, speed,
    output wire ppu_ce,cart_guard_ce,dma_active,
    output wire serial_clk_out, serial_data_out
);
    wire ce,ce_n,ce_2x,dma_on,raw_ce,raw_ce_n,raw_ce_2x,fast_speed;
    reg memory_wait;
    // Freeze all emulated clocks during external RAM accesses when fast mode
    // is active. Hold the gate across R release until the response completes.
    // Falling-edge update preserves the existing gated-RAM clock waveform.
    always @(negedge clk_sys)begin
      if(reset)memory_wait<=0;
      else memory_wait<=save_busy&&(fast_active||memory_wait);
    end
    assign ce=raw_ce&&!memory_wait;
    assign ce_n=raw_ce_n&&!memory_wait;
    assign ce_2x=raw_ce_2x&&!memory_wait;
    gbc_fast_forward fast(clk_sys,reset||video_restart,fast_requested,lcd_on,lcd_vsync,fast_speed,keep_pixels,fast_active);
    wire[7:0] normal_diag;
    assign diag_data=normal_diag;
    wire[1:0]joy_p54;
    wire[3:0]joy_din;
    gbc_joypad joypad(joystick,joy_p54,joy_din);
    assign ppu_ce=ce;assign audio_ce=ce;assign cart_guard_ce=ce_2x;assign dma_active=dma_on;
    speedcontrol clock_enables (
        .clk_sys(clk_sys), .pause(pause_core), .speedup(fast_speed&&!pause_core),
        .cart_act(1'b0), .save_act(save_busy), .DMA_on(dma_on),
        .ce(raw_ce), .ce_n(raw_ce_n), .ce_2x(raw_ce_2x), .refresh(), .ff_on()
    );
    gb core (.state_safe(state_safe),.state_addr(state_addr),.state_data(state_data),.state_commit(state_commit),
 .state_mem_active(state_mem_active),.state_mem_sel(state_mem_sel),.state_mem_addr(state_mem_addr),.state_mem_write(state_mem_write),
 .state_read(state_read),.state_mem_read(state_mem_read),.state_ext_read(state_ext_read),.cart_ready(cart_ready),.diag_addr(diag_addr),.diag_data(normal_diag),.debug_boot(debug_boot),.debug_fetch(debug_fetch),
        .reset(reset), .clk_sys(clk_sys), .ce(ce), .ce_n(ce_n), .ce_2x(ce_2x),
        .joystick(joystick), .isGBC(1'b1), .real_cgb_boot(real_cgb_boot),
        .isSGB(1'b0), .extra_spr_en(1'b0),
        .ext_bus_addr(ext_bus_addr), .ext_bus_a15(ext_bus_a15),
        .cart_rd(cart_rd), .cart_wr(cart_wr), .cart_do(cart_do),
        .cart_di(cart_di), .cart_oe(cart_oe), .nCS(nCS), .PHI(PHI),
        .sdram_rd(sdram_rd),
        .cgb_boot_download(boot_download), .dmg_boot_download(1'b0),
        .sgb_boot_download(1'b0), .ioctl_wr(boot_wr),
        .ioctl_addr(boot_addr), .ioctl_dout(boot_data),
        .boot_gba_en(1'b0), .fast_boot_en(1'b0),
        .audio_l(audio_l), .audio_r(audio_r), .audio_no_pops(1'b0),
        .megaduck(1'b0), .lcd_clkena(lcd_clkena), .lcd_data(lcd_data),
        .lcd_data_gb(lcd_data_gb), .lcd_mode(lcd_mode),
        .lcd_on(lcd_on), .lcd_vsync(lcd_vsync), .joy_p54(joy_p54), .joy_din(joy_din),
        .speed(speed), .DMA_on(dma_on),
        .gg_reset(reset), .gg_en(1'b0), .gg_code(129'b0), .gg_available(),
        .sc_int_clock2(), .serial_clk_in(serial_clk_in),
        .serial_clk_out(serial_clk_out), .serial_data_in(serial_data_in),
        .serial_data_out(serial_data_out),
        .increaseSSHeaderCount(1'b0), .cart_ram_size(8'd2),
        .save_state(1'b0), .load_state(1'b0), .savestate_number(2'b0),
        .sleep_savestate(), .savestate_ovr(),
        .SaveStateExt_Din(), .SaveStateExt_Adr(), .SaveStateExt_wren(),
        .SaveStateExt_rst(), .SaveStateExt_Dout(64'b0), .SaveStateExt_load(),
        .Savestate_CRAMAddr(), .Savestate_CRAMRdEn(), .Savestate_CRAMRWrEn(),
        .Savestate_CRAMWriteData(), .Savestate_CRAMReadData({cart_do,cart_do}),
        .SAVE_out_Din(), .SAVE_out_Dout(64'b0), .SAVE_out_Adr(),
        .SAVE_out_rnw(), .SAVE_out_ena(), .SAVE_out_be(), .SAVE_out_done(cart_ready),
        .savestate_sdram_busy(1'b0), .rewind_on(1'b0), .rewind_active(1'b0)
    );
endmodule
