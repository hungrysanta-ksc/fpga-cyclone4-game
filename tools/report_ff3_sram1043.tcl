# Characterize the routed asynchronous SRAM interface. Delay columns are
# FPGA propagation delays. SRAM access time and PCB skew are external.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc
create_clock -name ff3_io -period 381
set outputs [get_ports {RAM_ADDR[*] RAM_DATA[*] RAM_WE RAM_OE}]
set inputs [get_ports {RAM_DATA[*]}]
if {[get_collection_size $inputs]!=8 || [get_collection_size $outputs]!=29} {error "cartridge SRAM pin inventory"}
set_output_delay -clock ff3_io -max 0 $outputs
set_output_delay -clock ff3_io -min 0 $outputs
set_input_delay -clock ff3_io -max 0 $inputs
set_input_delay -clock ff3_io -min 0 $inputs
set f [open [lindex $quartus(args) 0] w]
puts $f "corner	group	check	from	to	data_delay_ns"
foreach c [get_available_operating_conditions] {
 set_operating_conditions $c
 update_timing_netlist
 foreach {group pins direction} [list output $outputs -to input $inputs -from] {
  foreach_in_collection pin $pins {
   foreach check {setup hold} {
    # Upper address bits are tied to the FF3 snapshot region.
    foreach_in_collection path [get_timing_paths -$check $direction $pin -npaths 1] {
     set a [get_node_info -name [get_path_info -from $path]]
     set b [get_node_info -name [get_path_info -to $path]]
     puts $f [join [list $c $group $check $a $b [get_path_info -data_delay $path]] "	"]
    }
   }
  }
 }
}
close $f
delete_timing_netlist
project_close
