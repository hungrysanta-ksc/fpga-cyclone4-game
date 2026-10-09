# SPDX-License-Identifier: MIT
# Run only in a writable copy of the pinned124 fitted project.
package require ::quartus::sta
project_open live
create_timing_netlist
read_sdc
source chains126.tcl
proc exact126 {name} {
 set r [get_registers $name]
 if {[get_collection_size $r]!=1} {error "Absent/ambiguous register $name"}
 foreach_in_collection n $r {if {[get_node_info -name $n] ne $name} {error "Wrong register $name"}}
 return $r
}
set out [open topology126.tsv w]
puts $out "kind\tchain\tstage\tfrom\tto\tlocation"
foreach row $chains126 {
 lassign $row kind name first second
 foreach {stage src} [list 0 $first 1 $second] {
  set node [exact126 $src]
  foreach_in_collection dst [get_fanouts $node] {
   puts $out "$kind\t$name\t$stage\t$src\t[get_node_info -name $dst]\t[get_node_info -location $dst]"
  }
 }
}
close $out
set resets [open local-reset126.tsv w]
puts $resets "corner\tchain\ttype\tfrom\tto\tslack"
set out [open timing126.tsv w]
puts $out "corner\tkind\tchain\ttype\tfrom\tto\tslack\tdelay\tskew\trelationship"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach row $chains126 {
  lassign $row kind name first second
  foreach type {setup hold} {
   set ps [get_timing_paths -$type -from [exact126 $first] -to [exact126 $second] -npaths 1]
   if {[get_collection_size $ps]!=1} {error "Missing stage path $name $type"}
   foreach_in_collection p $ps {puts $out "$corner\t$kind\t$name\t$type\t$first\t$second\t[get_path_info -slack $p]\t[get_path_info -data_delay $p]\t[get_path_info -clock_skew $p]\t[get_path_info -clock_relationship $p]"}
  }
  if {$kind eq "release"} {
   foreach type {recovery removal} {
    set ps [get_timing_paths -$type -from [exact126 $second] -npaths 10000 -nworst 1000]
    if {[get_collection_size $ps]>=10000} {error "Reset inventory truncated"}
    foreach_in_collection p $ps {puts $resets "$corner\t$name\t$type\t$second\t[get_node_info -name [get_path_info -to $p]]\t[get_path_info -slack $p]"}
   }
  }
 }
 report_metastability -nchains 100 -file metastability-$corner.rpt
}
close $out
close $resets
delete_timing_netlist
project_close
