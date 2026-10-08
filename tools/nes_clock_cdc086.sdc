# SPDX-License-Identifier: MIT
# CF86 ONLY: exact two heartbeat first stages and two async reset-release flops.
# No clock-group exception; downstream/data paths MUST remain timed.
proc cf86_regs {pattern count} {
 set result [get_registers $pattern]
 if {[get_collection_size $result] != $count} {error "CF86 CDC endpoint mismatch: $pattern"}
 return $result
}
set cf86_mem_src [cf86_regs {*clock_guard|mem_heartbeat} 1]
set cf86_mem_dst [cf86_regs {*clock_guard|mem_sync[0]} 1]
set cf86_ref_src [cf86_regs {*clock_guard|ref_divider[3]} 1]
set cf86_ref_dst [cf86_regs {*clock_guard|ref_sync[0]} 1]
set_false_path -from $cf86_mem_src -to $cf86_mem_dst
set_false_path -from $cf86_ref_src -to $cf86_ref_dst
# Only asynchronous clear inputs are reachable from these two source regs.
# Verify this using the unwaived routed audit, not an assumption from this SDC.
set cf86_reset_src [cf86_regs {*clock_guard|ref_fault *clock_guard|ref_qualified} 2]
set cf86_reset_dst [cf86_regs {*boundary|memory_release[*]} 2]
set_false_path -from $cf86_reset_src -to $cf86_reset_dst
