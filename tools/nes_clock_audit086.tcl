# SPDX-License-Identifier: MIT
# Fresh clone of the final routed DB. Enumerate CDC BEFORE exact exceptions.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc audit-unwaived.sdc
set f [open crossings.tsv w]
puts $f "corner\ttype\tsource_clock\ttarget_clock\tfrom\tto\tslack\tdata_delay"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach_in_collection other [get_clocks *] {
  set othername [get_clock_info -name $other]
  if {$othername eq "board8" || $othername eq "snes_ref"} {continue}
  foreach type {setup hold recovery removal} {
   if {[get_collection_size [get_timing_paths -$type -from_clock [get_clocks snes_ref] -to_clock $other -npaths 0]]!=0 ||
       [get_collection_size [get_timing_paths -$type -from_clock $other -to_clock [get_clocks snes_ref] -npaths 0]]!=0} {
    error "Unexpected reference/PLL crossing: $corner/$type/$othername"
   }
  }
 }
 foreach direction {out in} {
  if {$direction eq "out"} {set fromclk [get_clocks snes_ref]; set toclk [get_clocks board8]} else {
   set fromclk [get_clocks board8];set toclk [get_clocks snes_ref]
  }
  foreach type {setup hold recovery removal} {
   set paths [get_timing_paths -$type -from_clock $fromclk -to_clock $toclk -npaths 0]
   foreach_in_collection path $paths {
    puts $f "$corner\t$type\t$direction\treference_crossing\t[get_node_info -name [get_path_info -from $path]]\t[get_node_info -name [get_path_info -to $path]]\t[get_path_info -slack $path]\t[get_path_info -data_delay $path]"
   }
   report_timing -$type -from_clock $fromclk -to_clock $toclk -npaths 12 -detail full_path -file "cross-$direction-$type-$corner.rpt"
  }
 }
}
close $f
# The normal timing run must not waive first->second synchronizer data paths.
source clock-cdc086.sdc
update_timing_netlist
report_timing -setup -from [get_registers {*clock_guard|mem_sync[0] *clock_guard|ref_sync[0]}] -to [get_registers {*clock_guard|mem_sync[1] *clock_guard|ref_sync[1]}] -npaths 8 -detail full_path -file synchronizer-stages.rpt
report_timing -setup -from [get_registers {*boundary|memory_release[0]}] -to [get_registers {*boundary|memory_release[1]}] -npaths 4 -detail full_path -file reset-stages.rpt
report_exceptions -file exceptions.rpt
report_ucp -file unconstrained.rpt
delete_timing_netlist
project_close
