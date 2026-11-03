# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open mailbox567.tsv w]
puts $out "corner\tpath\tcheck\tslack\tfrom\tto"
proc record {out corner name check args} {
 set paths [get_timing_paths -$check {*}$args -npaths 1]
 if {![get_collection_size $paths]} {
  puts $out "$corner\t$name\t$check\tNONE\t\t"
 } else {
  foreach_in_collection p $paths {
   puts $out "$corner\t$name\t$check\t[get_path_info -slack $p]\t[get_node_info -name [get_path_info -from $p]]\t[get_node_info -name [get_path_info -to $p]]"
  }
 }
}
proc regs {pattern} {
 set r [get_registers $pattern]
 if {![get_collection_size $r]} {error "missing $pattern"}
 return $r
}
set core [regs {*|nes_domain_reset124:core_release|release_reset*}]
set valid [regs {*|nes_native_mailbox*:native_records|valid}]
set prep [regs {*|nes_native_mailbox*:native_prepared|held*}]
set recv [regs {*|nes_native_mailbox206:rearm|received*}]
set held [regs {*|nes_native_mailbox206:rearm|held*}]
set fault [regs {*|nes_diag_clock_guard127:clock_guard|ref_fault}]
set rel [regs {*|nes_clock_release563:memory_release|release_pipe*}]
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 record $out $corner reset_valid setup -from $core -to $valid
 record $out $corner reset_prepared setup -from $core -to $prep
 record $out $corner other_valid setup -to $valid
 record $out $corner rearm_data setup -from $held -to $recv
 record $out $corner memory_kill recovery -from $fault -to $rel
 foreach_in_collection clk [get_clocks *] {
  foreach kind {setup recovery} {record $out $corner [get_clock_info -name $clk] $kind -to_clock $clk}
 }
}
close $out
delete_timing_netlist
project_close
