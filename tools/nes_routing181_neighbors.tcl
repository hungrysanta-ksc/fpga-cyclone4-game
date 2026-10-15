# SPDX-License-Identifier: MIT
# Read-only report on a COPY of the completed CDC181 routed database.
# Implements Standard Design Optimization 3.4.3.4 four-neighborhood review.
package require ::quartus::sta
project_open board
create_timing_netlist
read_sdc nominal181.sdc
set_operating_conditions 8_slow_1200mv_85c
update_timing_netlist
set rows [open neighbors181.tsv w]
puts $rows "case	kind	from	to	slack	delay"
foreach {label pattern} {
 shift {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|shift[0]}
 offset {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_spi_check:control|offset[9]}
 failed {nes_live_joint:core|nes_spi_boot:loader_boot|nes_rom_boot:boot|check_failed}
 ack {nes_sink_bridge165:sink|nes_sink_spi165:endpoint|ack_work[31]}
} {
 set n [get_registers $pattern]
 if {[get_collection_size $n] != 1} {error "ambiguous endpoint: $label"}
 foreach direction {from to} {
  foreach kind {setup hold} {
   report_timing -$kind -$direction $n -npaths 50 -detail full_path -show_routing -file neighbors181-$label-$direction-$kind.rpt
   foreach_in_collection p [get_timing_paths -$kind -$direction $n -npaths 50] {
    puts $rows "$label-$direction	$kind	[get_node_info -name [get_path_info -from $p]]	[get_node_info -name [get_path_info -to $p]]	[get_path_info -slack $p]	[get_path_info -data_delay $p]"
   }
  }
 }
}
close $rows
delete_timing_netlist
project_close
