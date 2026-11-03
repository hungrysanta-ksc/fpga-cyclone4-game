# SPDX-License-Identifier: MIT
# Original FIT/STA stays intact. Expose only the masked toggle->first-stage
# path in a second timing netlist so its earliest hold arrival can be read.
package require ::quartus::sta
project_open board
proc contents {name} {
 set f [open $name r];set s [read $f];close $f;return $s
}
proc save {name s} {set f [open $name w];puts -nonewline $f $s;close $f}
set skip {set_false_path -from [cdc181_exact {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|request_toggle}] -to [cdc181_exact {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|nes_rom_physical:reader|request_sync[0]}]}
set cdc [split [contents cdc181.sdc] "\n"]
set idx [lsearch -all -exact $cdc $skip]
if {[llength $idx]!=1} {error "unexpected toggle exception"}
save inventory563-cdc.sdc [join [lreplace $cdc $idx $idx] "\n"]
set original [contents board.sdc]
if {[regexp -all -line {^source cdc181\.sdc$} $original]!=1} {error "unexpected CDC include"}
save inventory563-board.sdc [string map {{source cdc181.sdc} {source inventory563-cdc.sdc}} $original]
set out [open capture563.tsv w]
puts $out "view\tcorner\tcut\tperiod\tslack\tlaunch\tlatch\tarrival\trequired\tfrom\tto"
proc emit {file view c cut period paths} {
 foreach_in_collection p $paths {
  set row [list $view $c $cut $period]
  foreach opt {-slack -launch_time -latch_time -arrival_time -required_time} {
   lappend row [get_path_info $opt $p]
  }
  foreach opt {-from -to} {lappend row [get_node_info -name [get_path_info $opt $p]]}
  puts $file [join $row "\t"]
 }
}
foreach view {original toggle_inventory} {
 create_timing_netlist
 if {$view eq "original"} {read_sdc} else {read_sdc inventory563-board.sdc}
 set data [get_registers {*|nes_rom_physical:reader|address_hold*}]
 set req [get_registers {*|nes_rom_physical:reader|request_toggle}]
 set sync [get_registers {*|nes_rom_physical:reader|request_sync*}]
 set release [get_registers {*|*memory_release|release_*}]
 if {[get_collection_size $release]!=2} {error "guard release register count"}
 foreach_in_collection clk [get_clocks *] {
  if {[string first {clk[1]} [get_clock_info -name $clk]]>=0} {set mem $clk}
  if {[string first {clk[0]} [get_clock_info -name $clk]]>=0} {set host $clk}
 }
 set period [get_clock_info -period $mem]
 foreach c [get_available_operating_conditions] {
  set_operating_conditions $c;update_timing_netlist
  foreach_in_collection bit $data {
   emit $out $view $c data $period [get_timing_paths -setup -from $bit -to_clock $mem -npaths 1]
  }
  emit $out $view $c toggle $period [get_timing_paths -hold -from $req -to $sync -npaths 1]
  if {$view eq "original"} {
   emit $out $view $c host_recovery $period [get_timing_paths -recovery -to_clock $host -npaths 1]
   foreach src {ref_qualified mem_qualified ref_fault mem_fault} {
    set reg [get_registers "*|nes_diag_clock_guard127:clock_guard|$src"]
    foreach kind {setup recovery} {
     emit $out $view $c guard_${src}_$kind $period [get_timing_paths -$kind -from $reg -to $release -npaths 1]
    }
   }
   foreach kind {setup hold} {
    emit $out $view $c guard_pipe_$kind $period [get_timing_paths -$kind -from $release -to $release -npaths 1]
   }
  }
 }
 delete_timing_netlist
}
close $out
project_close
