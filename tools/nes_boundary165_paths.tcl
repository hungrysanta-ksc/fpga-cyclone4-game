# SPDX-License-Identifier: MIT
# Measurement only, on a COPY of the selected routed database. The 1000ns
# bounds expose otherwise-unconstrained paths; their slack is NOT signoff.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set f [open boundary165-ports.tsv w]
puts $f "name\tinput\toutput\tinout"
foreach_in_collection p [get_ports *] {puts $f "[get_node_info -name $p]\t[get_port_info -is_input_port $p]\t[get_port_info -is_output_port $p]\t[get_port_info -is_inout_port $p]"}
close $f
set f [open boundary165-registers.tsv w]
puts $f "name"
foreach_in_collection r [get_registers {*native_records* *native_prepared* *sink*release_reset* *native_spi_release*}] {puts $f [get_node_info -name $r]}
close $f
set f [open boundary165-topology.tsv w]
puts $f "from\tto"
foreach_in_collection r [get_registers {*native_records* *native_prepared* *native_spi_release*}] {
 set n [get_node_info -name $r]
 if {[regexp {\|(sr|dr|req_sync|ack_sync|up_src|up_dst|release_reset)\[0\]$} $n]} {
  set node [get_registers $n]
  if {[get_collection_size $node]!=1} {error "Missing topology node $n"}
  set fanouts [get_fanouts $node]
  if {[get_collection_size $fanouts]==0} {error "Empty first-stage fanout $n"}
  foreach_in_collection dst $fanouts {puts $f "$n\t[get_node_info -name $dst]"}
 }
}
close $f
set data_inputs [get_ports {ROM_DATA* SPI_* SNES_ADDR_IN* SNES_READ_IN SNES_WRITE_IN SNES_ROMSEL_IN SNES_DATA*}]
set data_outputs [get_ports {ROM_* SPI_MISO MCU_RDY SNES_DATA* SNES_DATABUS* DAC_*}]
set_max_delay 1000 -from $data_inputs -to [all_registers]
set_max_delay 1000 -from [all_registers] -to $data_outputs
set_max_delay 1000 -from $data_inputs -to $data_outputs
set f [open boundary165-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tdelay\tslack"
proc emit {f corner group paths limit} {
 if {[get_collection_size $paths]>=$limit} {error "Truncated $group inventory"}
 foreach_in_collection p $paths {
  puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -data_delay $p]\t[get_path_info -slack $p]"
 }
}
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 emit $f $corner input [get_timing_paths -setup -from $data_inputs -to [all_registers] -npaths 20000 -nworst 1] 20000
 emit $f $corner output [get_timing_paths -setup -from [all_registers] -to $data_outputs -npaths 20000 -nworst 1000] 20000
 emit $f $corner combinational [get_timing_paths -setup -from $data_inputs -to $data_outputs -npaths 20000 -nworst 1000] 20000
 foreach {group from to} {
  psram_input {ROM_DATA*} {*reader*data_hold*}
 } {
  emit $f $corner $group [get_timing_paths -setup -from [get_ports $from] -to [get_registers $to] -npaths 20000 -nworst 1000] 20000
 }
 foreach {group from to} {
  psram_address {*reader*address* *reader*chip*} {ROM_ADDR* ROM_1CE ROM_2CE}
  psram_active {*reader*reading_active} {ROM_1CE ROM_2CE ROM_OE}
 } {
  emit $f $corner $group [get_timing_paths -setup -from [get_registers $from] -to [get_ports $to] -npaths 20000 -nworst 1000] 20000
 }
 foreach {group from to} {
  records {*native_records*held*} {*native_records*received*}
  prepared {*native_prepared*held*} {*native_prepared*received*}
  pad {*pad*held_buttons*} {*pad*current_buttons*}
  records_req {*native_records*request} {*native_records*req_sync*}
  prepared_req {*native_prepared*request} {*native_prepared*req_sync*}
 } {
  set paths [get_timing_paths -setup -from [get_registers $from] -to [get_registers $to] -npaths 20000 -nworst 1000]
  if {[get_collection_size $paths]==0} {error "Missing $group"}
  emit $f $corner $group $paths 20000
 }
 emit $f $corner recovery [get_timing_paths -recovery -to [get_registers {*native_records* *native_prepared* *native_spi* *sink* *pad*}] -npaths 20000 -nworst 1] 20000
 emit $f $corner removal [get_timing_paths -removal -to [get_registers {*native_records* *native_prepared* *native_spi* *sink* *pad*}] -npaths 20000 -nworst 1] 20000
 foreach_in_collection a [get_clocks *] {
  foreach_in_collection b [get_clocks *] {
   if {[get_clock_info -name $a] ne [get_clock_info -name $b]} {
    emit $f $corner "mixed:[get_clock_info -name $a]:[get_clock_info -name $b]" [get_timing_paths -setup -from_clock $a -to_clock $b -npaths 100 -nworst 1] 101
   }
  }
 }
}
close $f
delete_timing_netlist
project_close
