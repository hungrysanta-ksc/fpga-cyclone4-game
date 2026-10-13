# SPDX-License-Identifier: MIT
# Exact nominal clocks, same routed DB. No path exceptions or period changes.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal165.sdc
set memory_clock [get_clocks {core|pll|altpll_component|auto_generated|pll1|clk[1]}]
if {[get_collection_size $memory_clock]!=1} {error "Memory clock missing"}
set f [open predecode165-paths.tsv w]
puts $f "corner\tgroup\tfrom\tto\tslack"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {counter capture address} {
  if {$group eq "counter"} {set targets [get_registers {*|control|check_next*}]} elseif {$group eq "capture"} {
   set targets [get_registers {*|control|pending_counter*}]
  } else {set targets [get_registers {*|loader|load_address*}]}
  set paths [get_timing_paths -setup -from_clock $memory_clock -to $targets -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing group $group"}
  foreach_in_collection path $paths {
   puts $f "$corner\t$group\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]"
  }
 }
}
close $f
delete_timing_netlist
project_close
