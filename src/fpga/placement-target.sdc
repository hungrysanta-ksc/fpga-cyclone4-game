# Four-entry Gray-pointer FIFO. No blanket asynchronous clock-group exception.
proc required_regs {pattern} {
 set nodes [get_registers $pattern]
 if {[get_collection_size $nodes]==0} {error "Missing CDC registers: $pattern"}
 return $nodes
}
foreach {source target} {
 {*writer|write_gray* *writer|write_bin[2]} {*writer|write_sync0*}
 {*writer|read_gray* *writer|read_bin[2]} {*writer|read_sync0*}
 {*uploader|request_toggle} {*uploader|req_sync*}
 {*uploader|response_toggle} {*uploader|ack_sync*}
} {
 set_false_path -from [required_regs $source] -to [required_regs $target]
 set_net_delay -max 10.0 -from [required_regs $source] -to [required_regs $target]
}
# Gray MSB equals binary MSB. Quartus merges that duplicate register into
# *_bin[2]; include exactly that bit, not the lower binary pointer bits.
# A slot stays immutable from enqueue until the committed read pointer returns.
# The receiver cannot use a new slot before its two pointer synchronizers.
foreach {source target} {
 {*writer|entries*} {*host_frontend|writer|data_next* *host_frontend|writer|held_high* *host_frontend|writer|held_word *host_frontend|writer|addr_next* *host_frontend|writer|slot_violation}
 {*uploader|held_*} {*uploader|bus_page *uploader|bus_front_valid}
} {
 set from [required_regs $source];set to [required_regs $target]
 set_max_delay 10.0 -from $from -to $to
 set_net_delay -max 10.0 -from $from -to $to
 set_false_path -hold -from $from -to $to
}
set reset_pipes [required_regs {*writer|source_reset* *writer|bus_reset* *uploader|brst* *uploader|srst*}]
set_false_path -from [required_regs {*guard|release_pipe*}] -to $reset_pipes
set bus_clock [get_clocks {*bus_pll*}]
if {[get_collection_size $bus_clock]!=1} {error "Expected one bus PLL clock"}
set_input_delay -clock $bus_clock -max 0 [get_ports {SNES_DATA[*]}]
set_input_delay -clock $bus_clock -min 0 [get_ports {SNES_DATA[*]}]

# SRAM pad constraints here bound routing to one bus clock only. External
# tAA/tWP/setup/hold must be checked with a board-level pin model separately.
set_false_path -from [required_regs {*guard|release_pipe*}] -to [required_regs {*host_frontend|reset_pipe*}]
set_input_delay -clock $bus_clock -max 0 [get_ports {SNES_CPU_CLK_IN SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_ADDR_IN[*] RAM_DATA[*]}]
set_input_delay -clock $bus_clock -min 0 [get_ports {SNES_CPU_CLK_IN SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_ADDR_IN[*] RAM_DATA[*]}]
set_output_delay -clock $bus_clock -max 0 [get_ports {RAM_ADDR[*] RAM_DATA[*] RAM_WE RAM_OE}]
set_output_delay -clock $bus_clock -min 0 [get_ports {RAM_ADDR[*] RAM_DATA[*] RAM_WE RAM_OE}]

set_output_delay -clock $bus_clock -max -11.9047619 [get_ports {RAM_ADDR[*] RAM_DATA[*] RAM_WE RAM_OE}]

set_false_path -from [required_regs {*guard|release_pipe*}] -to [required_regs {*host_frontend|reset_pipe*}]
# Tighten the original PSRAM OE output requirement by 2 ns to guide placement
# toward the output pad. This does not extend the memory read allowance.
set_output_delay -clock sys -max 19.201324503311 [get_ports {ROM_OE}]

# Virtual input envelope only; asynchronous SNES pad/CDC timing is NOT signed off.

# Joypad bundled-data CDC. The commit toggle traverses two synchronizers; the
# source data remains stable before that toggle and is bounded to 10 ns so it
# has settled well before the destination observes the synchronized event.
set joy_toggle_source [required_regs {*host_frontend|registers|joy_update[9]}]
set joy_toggle_target [required_regs {*joy_transfer|toggle_sync[0]}]
set_false_path -from $joy_toggle_source -to $joy_toggle_target
set_net_delay -max 10.0 -from $joy_toggle_source -to $joy_toggle_target
set joy_data_source [required_regs {*host_frontend|registers|joy_update[*]}]
set joy_data_target [required_regs {*joy_transfer|joystick[*]}]
set_max_delay 10.0 -from $joy_data_source -to $joy_data_target
set_net_delay -max 10.0 -from $joy_data_source -to $joy_data_target
set_false_path -hold -from $joy_data_source -to $joy_data_target
# Only the first sampling registers are asynchronous endpoints.  Their second
# stages remain normally timed.  Raw pad use in the transceiver-release path is
# intentionally not cut and still requires the physical SNES timing model.
set_false_path -from [get_ports {SNES_CPU_CLK_IN}] -to [required_regs {*host_frontend|slots|phi_sync[0]}]
set_false_path -from [get_ports {SNES_READ_IN}] -to [required_regs {*host_frontend|slots|rd_sync[0]}]
set_false_path -from [get_ports {SNES_WRITE_IN}] -to [required_regs {*host_frontend|slots|wr_sync[0] *host_frontend|bridge|wr_sync[0]}]
set_false_path -from [get_ports {SNES_ROMSEL_IN}] -to [required_regs {*host_frontend|slots|cs_sync[0]}]
set_false_path -from [get_ports {SNES_ADDR_IN[*]}] -to [required_regs {*host_frontend|slots|addr_meta[*] *host_frontend|bridge|addr_meta[*]}]
set_false_path -from [get_ports {SNES_DATA[*]}] -to [required_regs {*host_frontend|bridge|data_meta[*]}]

# GBC audio samples are filtered in the source domain and held for 64 source
# enables.  The stereo bundle settles before its commit toggle crosses two
# synchronizer stages into the 84 MHz DAC domain.
set audio_toggle_source [required_regs {*dac_output|sample_toggle}]
set audio_toggle_target [required_regs {*dac_output|toggle_sync[0]}]
set_false_path -from $audio_toggle_source -to $audio_toggle_target
set_net_delay -max 10.0 -from $audio_toggle_source -to $audio_toggle_target
set audio_data_source [required_regs {*dac_output|playback_l[*] *dac_output|playback_r[*]}]
set audio_data_target [required_regs {*dac_output|dac_sample_l[*] *dac_output|dac_sample_r[*]}]
set_max_delay 10.0 -from $audio_data_source -to $audio_data_target
set_net_delay -max 10.0 -from $audio_data_source -to $audio_data_target
set_false_path -hold -from $audio_data_source -to $audio_data_target
set_false_path -from [required_regs {*guard|release_pipe*}] -to [required_regs {*dac_output|dac_reset_pipe*}]
# This bounds FPGA routing to the pins.  It is not a substitute for the
# external DAC's setup/hold specification, which remains a hardware gate.
set_output_delay -clock $bus_clock -max 0 [get_ports {DAC_MCLK DAC_LRCK DAC_SDOUT}]
set_output_delay -clock $bus_clock -min 0 [get_ports {DAC_MCLK DAC_LRCK DAC_SDOUT}]

# Fitter-only extra hold relationships; removed for original-constraint signoff.
# Signoff uses original VRAM hold relationships.
# Signoff uses original DMA-to-VRAM hold relationships.

# G4 diagnostic bundle: held before the two-flop acknowledge is observed;
# remains stable through destination capture until the next request.
set_false_path -from [required_regs {*diagnostic|request_toggle}] -to [required_regs {*diagnostic|request_sync[0]}]
set_false_path -from [required_regs {*diagnostic|acknowledge}] -to [required_regs {*diagnostic|ack_sync[0]}]
set_max_delay 10.0 -from [required_regs {*diagnostic|held[*]}] -to [required_regs {*diagnostic|snapshot[*]}]
set_net_delay -max 10.0 -from [required_regs {*diagnostic|held[*]}] -to [required_regs {*diagnostic|snapshot[*]}]
set_false_path -hold -from [required_regs {*diagnostic|held[*]}] -to [required_regs {*diagnostic|snapshot[*]}]
set_false_path -from [required_regs {*guard|release_pipe*}] -to [required_regs {*diagnostic|reset_pipe*}]

# Fitter-only additional hold margin; original SDC restored for signoff.
set_min_delay -from [required_regs {*video|bg_tile*}] -to [required_regs {*vram*|*porta_address_reg*}] 1.000
set_min_delay -from [required_regs {*video|dma_cnt*}] -to [required_regs {*vram*|*porta_address_reg*}] 0.500

# Fitter-only ROM_OE routing target; signoff restores original SDC.
set_max_delay 10.5 -from [required_regs {*memory|rom_oe_r}] -to [get_ports {ROM_OE}]

# C29 one-request/one-response held menu bundles.
set_false_path -from [required_regs {*menu_link|request_toggle}] -to [required_regs {*menu_link|request_sync[0]}]
set_false_path -from [required_regs {*menu_link|acknowledge}] -to [required_regs {*menu_link|ack_sync[0]}]
set_max_delay 10.0 -from [required_regs {*menu_link|request_held[*]}] -to [required_regs {*menu_link|request_core[*]}]
set_net_delay -max 10.0 -from [required_regs {*menu_link|request_held[*]}] -to [required_regs {*menu_link|request_core[*]}]
set_false_path -hold -from [required_regs {*menu_link|request_held[*]}] -to [required_regs {*menu_link|request_core[*]}]
set_max_delay 10.0 -from [required_regs {*menu_link|reply_held[*]}] -to [required_regs {*menu_link|reply_bus[*]}]
set_net_delay -max 10.0 -from [required_regs {*menu_link|reply_held[*]}] -to [required_regs {*menu_link|reply_bus[*]}]
set_false_path -hold -from [required_regs {*menu_link|reply_held[*]}] -to [required_regs {*menu_link|reply_bus[*]}]
set_false_path -from [required_regs {*guard|release_pipe*}] -to [required_regs {*menu_link|reset_pipe*}]
set_false_path -from [required_regs {*menu_link|flags[*]}] -to [required_regs {*dac_output|mute_sync[0]}]
set_net_delay -max 10.0 -from [required_regs {*menu_link|flags[*]}] -to [required_regs {*dac_output|mute_sync[0]}]

set fast_mute_source [required_regs {*core|fast|active}]
set_false_path -from $fast_mute_source -to [required_regs {*dac_output|mute_sync[0]}]
set_net_delay -max 10.0 -from $fast_mute_source -to [required_regs {*dac_output|mute_sync[0]}]
