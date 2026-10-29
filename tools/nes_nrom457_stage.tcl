package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner;update_timing_netlist
 foreach which {ref_release mem_release} {
  set a {};set b {}
  foreach_in_collection r [get_registers {*clock_guard*release_reset*}] {
   set n [get_node_info -name $r]
   if {[string first ":$which|release_reset\[0\]" $n]>=0} {set a $r}
   if {[string first ":$which|release_reset\[1\]" $n]>=0} {set b $r}
  }
  if {$a eq "" || $b eq ""} {error "missing stage"}
  set paths [get_timing_paths -setup -from $a -to $b -npaths 1]
  foreach_in_collection p $paths {puts "GUARD457 $corner $which slack=[get_path_info -slack $p] delay=[get_path_info -data_delay $p]"}
 }
}
project_close
