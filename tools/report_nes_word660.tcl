package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set fh [open word660.tsv w]
puts $fh "corner\tbit\tslack\tdelay\tfrom\tto"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 for {set i 0} {$i<8} {incr i} {
  set src [cdc181_exact [format {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|bg_hold[%d]} $i]]
  set dst [cdc181_exact [format {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|bg_word[%d]} $i]]
  set paths [get_timing_paths -setup -from $src -to $dst -npaths 1]
  if {[get_collection_size $paths]!=1} {error "missing BG return bit $i"}
  foreach_in_collection p $paths {
   puts $fh [join [list $corner $i [get_path_info -slack $p] [get_path_info -data_delay $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]]] "\t"]
  }
 }
}
close $fh
delete_timing_netlist
project_close
