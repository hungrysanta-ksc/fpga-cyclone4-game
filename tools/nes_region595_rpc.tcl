onerror {quit -code 1}
run 1 ns
set io [socket 127.0.0.1 $env(NES595_PORT)]
fconfigure $io -translation lf -buffering line
set seq 0
proc getval {name} {return [examine -radix unsigned /region595_tb/$name]}
proc putval {name val} {
 if {[string first "#" $val] < 0} {set val "10#$val"}
 force -deposit /region595_tb/$name $val
}
puts $io READY
while {[gets $io line] >= 0} {
 set op [lindex $line 0]
 if {$op eq "quit"} {puts $io BYE; close $io; quit -f}
 if {$op eq "stats"} {
  set vals {}
  foreach key {source_fault host_fault repair_rows leases queries injected owned dut/state dut/phase dut/repaired dut/spi/token} {lappend vals [getval $key]}
  puts $io $vals
  continue
 }
 if {$op eq "frame"} {
  putval frame_id [lindex $line 1]; putval corrupt [lindex $line 2]; putval command 1;set duration 2000
 } elseif {$op eq "reset"} {
  putval command 3;set duration 4000
 } elseif {$op eq "spi"} {
  set hex [lindex $line 1]
  set n [expr {[string length $hex]/2}]
  putval n $n;putval tx "16#$hex";putval command 2
  set duration [expr {$n*3048+9000}]
 } else {error "unknown command"}
 incr seq;putval go $seq
 run $duration ns
 if {[getval done]!=$seq} {error "incomplete transaction"}
 if {$op eq "spi"} {
  set raw [examine -radix hex /region595_tb/rx]
  puts $io [string range $raw end-[expr {2*$n-1}] end]
 } else {puts $io OK}
}
quit -code 1
