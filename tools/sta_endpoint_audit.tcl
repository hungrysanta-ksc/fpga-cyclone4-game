# Run only after a fitted pin project has been rebuilt in a private directory.
# This reports post-map register names; it does not alter timing constraints.
project_open pin
create_timing_netlist
read_sdc
foreach pattern {
 {*uploader|brst*}
 {*uploader|srst*}
 {*writer|bus_reset*}
 {*writer|source_reset*}
 {*host_frontend|bridge|wr_sync[0]}
 {*host_frontend|bridge|addr_meta[*]}
 {*host_frontend|slots|wr_sync[0]}
 {*host_frontend|slots|addr_meta[*]}
 {*host_frontend|reset_pipe*}
} {
 set nodes [get_registers $pattern]
 puts "PATTERN $pattern COUNT [get_collection_size $nodes]"
 foreach_in_collection node $nodes {
  puts "NODE [get_node_info -name $node]"
 }
}
project_close
