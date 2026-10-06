# SPDX-License-Identifier: MIT
# Run in a COPY of the fitted034 project. Pure delay inventory, not IO signoff.
project_open board -revision board
create_timing_netlist -model slow
read_sdc board.sdc
update_timing_netlist
file mkdir io-audit
set f [open io-audit/delays.tsv w]
puts $f "group\tpaths\tlongest_ns"
foreach {name from to} {
 snes_pad_enable {SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_ADDR_IN[*]} {SNES_DATABUS_OE SNES_DATABUS_DIR SNES_DATA[*]}
 snes_input_capture {SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_ADDR_IN[*] SNES_DATA[*]} *
 spi_input_capture {SPI_SCK SPI_SS SPI_MOSI} *
 spi_ss_release {SPI_SS} {SPI_MISO}
 register_to_snes * {SNES_DATA[*] SNES_DATABUS_OE SNES_DATABUS_DIR}
 register_to_miso * {SPI_MISO}
} {
 if {$from eq "*"} {set src [all_registers]} else {set src [get_ports $from]}
 if {$to eq "*"} {set dst [all_registers]} else {set dst [get_ports $to]}
 set result [report_path -from $src -to $dst -npaths 16 -pairs_only -file io-audit/$name.txt]
 puts $f "$name\t[lindex $result 0]\t[lindex $result 1]"
}
close $f
report_ucp -file io-audit/unconstrained.txt
delete_timing_netlist
project_close
