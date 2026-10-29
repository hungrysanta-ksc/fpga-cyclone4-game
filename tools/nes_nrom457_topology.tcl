package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
update_timing_netlist
set f [open guard457-topology.tsv w]
puts $f "node\tfanout"
set count 0
foreach_in_collection r [get_registers {*clock_guard*release_reset*}] {
 set n [get_node_info -name $r]
 if {[regexp {:(ref_release|mem_release)\|release_reset\[0\]$} $n]} {
  incr count
  set node [get_registers $n]
  set fo [get_fanouts $node]
  if {[get_collection_size $fo]!=1} {error "first-stage fanout is not unique: $n"}
  foreach_in_collection x $fo {
   set target [get_node_info -name $x]
   if {$target ne [string replace $n end-1 end-1 1]} {error "unexpected fanout $n -> $target"}
   puts $f "$n\t$target"
  }
 }
}
if {$count!=2} {error "expected two first-stage registers, got $count"}
close $f
project_close
