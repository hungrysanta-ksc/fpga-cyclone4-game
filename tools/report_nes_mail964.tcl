package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
set mailbox {nes_live_joint:core|nes_direct206:direct_path|nes_native_mailbox206:page_mail963}
set pairs {{request {req_sync[0]}} {acknowledge {ack_sync[0]}} {{sr[1]} {up_dst[0]}} {{dr[1]} {up_src[0]}}}
for {set bit 0} {$bit<26} {incr bit} {
 lappend pairs [list [format {held[%d]} $bit] [format {received[%d]} $bit]]
}
set fh [open mail964.tsv w]
puts $fh "corner\tfrom\tto\tslack\tdelay"
foreach corner [get_available_operating_conditions] {
 set_operating_conditions $corner
 update_timing_netlist
 foreach pair $pairs {
  lassign $pair a b
  set src [cdc181_exact "$mailbox|$a"]
  set dst [cdc181_exact "$mailbox|$b"]
  set paths [get_timing_paths -setup -from $src -to $dst -npaths 1]
  if {[get_collection_size $paths]!=1} {error "Missing $corner $a -> $b"}
  foreach_in_collection path $paths {
   puts $fh [join [list $corner $a $b [get_path_info -slack $path] [get_path_info -data_delay $path]] "\t"]
  }
 }
}
close $fh
delete_timing_netlist
project_close
