#160 Placement guidance for the two measured nominal failures in fit01.
# These are stricter same-memory-clock budgets, not timing waivers.
set_max_delay 5.3 -from [get_registers {*|control|byte_count*}] -to [get_registers {*|control|miso_hold}]
set_max_delay 5.3 -from [get_registers {*|loader|state*}] -to [get_registers {*|loader|loaded_bytes*}]
