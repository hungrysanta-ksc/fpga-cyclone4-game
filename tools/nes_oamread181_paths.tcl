# SPDX-License-Identifier: MIT
# Read-only post-FIT audit. No constraints or exceptions are added.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal181.sdc
set oam [get_registers {*spriteeval*}]
set ram [get_registers {*spriteeval*primary_run*}]
if {[get_collection_size $oam]==0 || [get_collection_size $ram]==0} {error "Missing OAM/RAM timing nodes"}
set f [open oamread181-paths.tsv w]
puts $f "corner\tgroup\tkind\tfrom\tto\tslack\tdelay\trelationship"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach group {to_ram from_ram all_oam} {
  foreach kind {setup hold} {
   if {$group eq "to_ram"} {
    set ps [get_timing_paths -$kind -to $ram -npaths 20000 -nworst 1]
   } elseif {$group eq "from_ram"} {
    set ps [get_timing_paths -$kind -from $ram -npaths 20000 -nworst 1]
   } else {
    set ps [get_timing_paths -$kind -to $oam -npaths 20000 -nworst 1]
   }
   set count [get_collection_size $ps]
   if {$count==0 || $count>=20000} {error "Missing/truncated $group $kind paths"}
   foreach_in_collection p $ps {
    puts $f "$corner\t$group\t$kind\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]\t[get_path_info -data_delay $p]\t[get_path_info -clock_relationship $p]"
   }
  }
 }
 report_timing -setup -to $ram -npaths 20 -detail full_path -file oamread181-$corner-to-ram.rpt
 report_timing -setup -from $ram -npaths 20 -detail full_path -file oamread181-$corner-from-ram.rpt
 report_min_pulse_width -file oamread181-$corner-pulse.rpt
}
close $f
delete_timing_netlist
project_close
