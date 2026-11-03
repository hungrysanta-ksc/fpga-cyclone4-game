# SPDX-License-Identifier: MIT
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set out [open gate570.tsv w]
puts $out "corner\tpath\tcheck\tslack\tfrom\tto"
proc path570 {out c name kind from to} {
 set n 0
 if {[get_collection_size $from] && [get_collection_size $to]} {
  foreach_in_collection p [get_timing_paths -$kind -from $from -to $to -npaths 1] {
   puts $out [join [list $c $name $kind [get_path_info -slack $p] [get_node_info -name [get_path_info -from $p]] [get_node_info -name [get_path_info -to $p]]] "\t"]
   incr n
  }
 }
 if {!$n} {puts $out "$c\t$name\t$kind\tNONE\t\t"}
}
set guard {*|nes_diag_clock_guard127:clock_guard|}
set top {*|nes_direct206:direct_path|}
set ref [get_registers ${guard}ref_qualified]
set stage [get_registers -nowarn ${guard}ref_ok_mem*]
set rel [get_registers {*|nes_clock_release563:memory_release|release_pipe*}]
set fault [get_registers ${guard}ref_fault]
set nf [get_registers ${top}nf]
set parent [get_registers -nowarn ${top}nes_domain_reset124:hcancel|release_reset*]
set plan [get_registers -nowarn ${top}nes_plan_batch206:transport|nes_domain_reset124:hcancel|release_reset*]
set core [get_registers {*|nes_domain_reset124:core_release|release_reset*}]
set plan_hr [get_registers -nowarn ${top}nes_plan_batch206:transport|nes_domain_reset124:hrelease|release_reset*]
set bank [get_registers -nowarn ${top}nes_tile_bulk206:bulk|nes_native_mailbox206:tiles|dr*]
set meta [get_registers -nowarn ${top}n_to_h*]
set f [open gate570-registers.tsv w]
puts $f "ref\tstage\trelease\tnf\tparent\tplan\tmeta\tbank\tplan_hr"
puts $f [join [list [get_collection_size $ref] [get_collection_size $stage] [get_collection_size $rel] [get_collection_size $nf] [get_collection_size $parent] [get_collection_size $plan] [get_collection_size $meta] [get_collection_size $bank] [get_collection_size $plan_hr]] "\t"]
close $f
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 path570 $out $c ref_release setup $ref $rel
 path570 $out $c ref_stage setup $ref $stage
 path570 $out $c stage_release setup $stage $rel
 path570 $out $c memory_fault recovery $fault $rel
 path570 $out $c nf_plan recovery $nf $plan
 path570 $out $c nf_parent recovery $nf $parent
 path570 $out $c parent_plan recovery $parent $plan
 path570 $out $c nf_bank recovery $nf $bank
 path570 $out $c parent_bank recovery $parent $bank
 path570 $out $c core_plan_hr recovery $core $plan_hr
 path570 $out $c parent_plan_hr recovery $parent $plan_hr
 path570 $out $c nf_feedback setup $nf $meta
}
close $out
delete_timing_netlist
project_close
