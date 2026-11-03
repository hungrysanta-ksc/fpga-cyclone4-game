# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set file [open start572.tsv w]
puts $file "corner\tcut\tcheck\tslack\tfrom\tto"
set pending [get_registers {*|nes_rom_spi_check:control|pending}]
set start [get_registers {*|nes_rom_spi_check:control|start}]
set fault [get_registers {*|nes_diag_clock_guard127:clock_guard|ref_fault}]
set grant [get_registers {*|nes_diag_clock_guard127:clock_guard|ref_qualified}]
set bridge [get_registers -nowarn {*|nes_diag_clock_guard127:clock_guard|ref_ok_mem*}]
set release [get_registers {*|*:memory_release|release*}]
foreach coll [list $pending $start $fault $release] {
 if {![get_collection_size $coll]} {error "missing endpoint"}
}
proc measure {file c name kind args} {
 set paths [get_timing_paths -$kind {*}$args -npaths 1]
 if {![get_collection_size $paths]} {puts $file "$c\t$name\t$kind\tNONE\t\t";return}
 foreach_in_collection p $paths {
  puts $file [join [list $c $name $kind [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]]] "\t"]
 }
}
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 measure $file $c pending_start setup -from $pending -to $start
 measure $file $c any_start setup -to $start
 measure $file $c ref_release recovery -from $fault -to $release
 measure $file $c ref_any recovery -from $fault
 measure $file $c any_release recovery -to $release
 measure $file $c grant_any recovery -from $grant
 if {[get_collection_size $bridge]} {
  measure $file $c grant_bridge recovery -from $grant -to $bridge
  measure $file $c bridge_release recovery -from $bridge -to $release
 }
 measure $file $c nes_setup setup -to_clock [get_clocks nes]
}
close $file
delete_timing_netlist
project_close
