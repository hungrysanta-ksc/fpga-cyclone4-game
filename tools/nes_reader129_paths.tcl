# SPDX-License-Identifier: MIT
# Read-only verification of the specific128 critical path and129 owner stages.
package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
proc one129 {name} {
 set r [get_registers $name]
 if {[get_collection_size $r]!=1} {error "Missing exact register $name"}
 foreach_in_collection n $r {if {[get_node_info -name $n] ne $name} {error "Unexpected register $name"}}
 return $r
}
set prefix {nes_spi_boot:loader_boot|nes_rom_boot:boot|}
set release [one129 "${prefix}nes_rom_loader:loader|release_reset\[1\]"]
set owner [one129 "${prefix}nes_rom_physical:reader|owner_check"]
set valid [one129 "${prefix}nes_rom_physical:reader|owner_valid"]
set targets [get_registers {*nes_rom_physical:reader|check_response_address*}]
if {[get_collection_size $targets]<16} {error "Reader response address inventory missing"}
set out [open reader129-paths.tsv w]
puts $out "corner\tgroup\tpaths\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {old_direct release_owner owner_address owner_input valid_input} {
  switch $group {
   old_direct {set ps [get_timing_paths -setup -from $release -to $targets -npaths 1000]}
   release_owner {set ps [get_timing_paths -setup -from $release -to $owner -npaths 1000]}
   owner_address {set ps [get_timing_paths -setup -from $owner -to $targets -npaths 1000]}
   owner_input {set ps [get_timing_paths -setup -to $owner -npaths 1000]}
   valid_input {set ps [get_timing_paths -setup -to $valid -npaths 1000]}
  }
  set count [get_collection_size $ps]
  if {$count>=1000} {error "Truncated path inventory"}
  if {$count==0} {puts $out "$corner\t$group\t0\t-\t-\t-"}
  foreach_in_collection p $ps {
   puts $out "$corner\t$group\t$count\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"
  }
 }
}
close $out
delete_timing_netlist
project_close
