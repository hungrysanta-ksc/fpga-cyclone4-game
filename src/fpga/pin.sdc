create_clock -name board8 -period 125 [get_ports CLKIN]
derive_pll_clocks
create_clock -name sys -period 29.801324503311
derive_clock_uncertainty
set_output_delay -clock sys -max 17.201324503311 [get_ports {ROM_ADDR[*] ROM_1CE ROM_2CE ROM_OE}]
set_output_delay -clock sys -min 0 [get_ports {ROM_ADDR[*] ROM_1CE ROM_2CE ROM_OE}]
set_input_delay -clock sys -max 87.6 [get_ports {ROM_DATA[*]}]
set_input_delay -clock sys -min 0 [get_ports {ROM_DATA[*]}]
set_multicycle_path -setup 3 -from [get_ports {ROM_DATA[*]}]
set_multicycle_path -hold 2 -from [get_ports {ROM_DATA[*]}]

# GBC SaveRAM PSRAM byte-lane controls.
set_output_delay -clock sys -max 17.201324503311 [get_ports {ROM_BHE ROM_BLE}]
set_output_delay -clock sys -min 0 [get_ports {ROM_BHE ROM_BLE}]

create_clock -name mcu_spi_sck -period 20.833 [get_ports SPI_SCK]
set_false_path -from [get_clocks mcu_spi_sck] -to [get_clocks {*|pll|*}]
set_false_path -to [get_registers {*renderer_loader|request_sync[0] *renderer_loader|ack_sync[0] *renderer_loader|run_sync[0]}]
set_max_delay 10 -from [get_registers {*renderer_loader|address_q[*] *renderer_loader|write_q[*] *renderer_loader|is_write}] -to [get_registers {*renderer_loader|ram_addr[*] *renderer_loader|data_q[*] *renderer_loader|writing *renderer_loader|drive}]
set_false_path -hold -from [get_registers {*renderer_loader|address_q[*] *renderer_loader|write_q[*] *renderer_loader|is_write}] -to [get_registers {*renderer_loader|ram_addr[*] *renderer_loader|data_q[*] *renderer_loader|writing *renderer_loader|drive}]
set_max_delay 15 -from [get_registers {*renderer_loader|result_q[*]}] -to [get_registers {*renderer_loader|read_data[*]}]
set_false_path -hold -from [get_registers {*renderer_loader|result_q[*]}] -to [get_registers {*renderer_loader|read_data[*]}]

# C19 bundled CDC. Word spacing >=380ns, source sampled before pop.
set_false_path -to [get_registers {*load_spi|rs[0] *load_spi|ts[0]}]
set_max_delay 15 -from [get_registers {*load_spi|held[*]}] -to [get_registers {*load_spi|rx_data[*]}]
set_false_path -hold -from [get_registers {*load_spi|held[*]}] -to [get_registers {*load_spi|rx_data[*]}]
set_max_delay 30 -from [get_registers {*load_engine|words|rf* *load_engine|words|ro[*] *load_engine|words|sent[*]}] -to [get_registers {*load_spi|tx_latch[*] *load_spi|miso_q}]
set_false_path -hold -from [get_registers {*load_engine|words|rf* *load_engine|words|ro[*] *load_engine|words|sent[*]}] -to [get_registers {*load_spi|tx_latch[*] *load_spi|miso_q}]

# FIFO head address (ro; bit 0 optimized into sent[0]) is bundled with data.
# Early tx_take changes head only after SCK has latched the complete word.
# Next capture occurs 16 SCK edges later (>=333ns at the 48MHz constraint).

# STM32F401 DS9716 table 61: master MISO setup 0ns, hold 6ns.
# Bound the new mode-0 output register against the stricter 48MHz SCK clock.
set_output_delay -clock mcu_spi_sck -max 0 [get_ports SPI_MISO]
set_output_delay -clock mcu_spi_sck -min -6 [get_ports SPI_MISO]
# Legacy status replies and mux control settle in the >=500ns command gap.
set_max_delay 40 -from [get_clocks {*|pll|*}] -to [get_ports SPI_MISO]
set_false_path -hold -from [get_clocks {*|pll|*}] -to [get_ports SPI_MISO]

# DS9716 table61 master MOSI launch bounds. Half-period at 48MHz also
# covers the 42MHz master duty tolerance (minimum half-cycle ~10.405ns).
set_input_delay -clock mcu_spi_sck -clock_fall -max 5 [get_ports SPI_MOSI]
set_input_delay -clock mcu_spi_sck -clock_fall -min 2 [get_ports SPI_MOSI]

# C20 exit observation crosses only this two-flop renderer RUN synchronizer.
set_false_path -to [get_registers {*observe_renderer_run[0]}]
