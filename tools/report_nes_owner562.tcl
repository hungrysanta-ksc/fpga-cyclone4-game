# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open owner562-paths.tsv w]
puts $out "corner\tcut\tcheck\tslack\tdata_delay\tfrom\tto"
proc emit {file corner name kind args} {
 set coll [get_timing_paths -$kind {*}$args -npaths 1]
 foreach_in_collection p $coll {
  puts $file "$corner\t$name\t$kind\t[get_path_info -slack $p]\t[get_path_info -data_delay $p]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]"
 }
}
set phase [get_registers {*|nes_rom_loader:loader|phase*}]
set req [get_registers {*|nes_rom_physical:reader|request_toggle}]
set init [get_registers {*|nes_local_memory:local_memory|init_done}]
set mr [get_registers {*|nes_rom_physical:reader|memory_reset*}]
set addr [get_registers {*|nes_rom_physical:reader|address_hold*}]
set sync [get_registers {*|nes_rom_physical:reader|request_sync*}]
foreach group [list $phase $req $init $mr $addr $sync] {
 if {[get_collection_size $group]==0} {error "missing fitted register"}
}
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 emit $out $corner loader_to_request setup -from $phase -to $req
 emit $out $corner scrub_to_memory_reset recovery -from $init -to $mr
 emit $out $corner request_to_synchronizer setup -from $req -to $sync
 foreach_in_collection clk [get_clocks *] {
  set name [get_clock_info -name $clk]
  if {$name eq "nes"} {emit $out $corner NES setup -to_clock $clk}
  if {[string first {clk[1]} $name]>=0} {
   emit $out $corner bundled_address setup -from $addr -to_clock $clk
   foreach kind {setup recovery} {emit $out $corner MEM $kind -to_clock $clk}
  }
 }
}
close $out
delete_timing_netlist
project_close
