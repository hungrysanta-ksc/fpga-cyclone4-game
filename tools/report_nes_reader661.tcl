package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set f [open reader661.tsv w]
puts $f "corner\tgroup\tslack\tfrom\tto"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach {label filter} {reader {*nes_rom_physical:reader|*} miso {*nes_native_spi165:native_spi|miso_hold}} {
  set regs [get_registers $filter]
  if {$label eq "reader"} {
   set paths [get_timing_paths -setup -from $regs -to $regs -npaths 1]
  } else {
   set paths [get_timing_paths -setup -to $regs -npaths 1]
  }
  if {[get_collection_size $paths]!=1} {error "missing $label"}
  foreach_in_collection p $paths {
   puts $f [join [list $c $label [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]]] "\t"]
  }
 }
}
close $f
delete_timing_netlist
project_close
