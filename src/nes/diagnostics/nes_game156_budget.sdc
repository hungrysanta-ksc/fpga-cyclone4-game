#156 Implementation budgets, not a complete board electrical signoff.
# Same-memory-clock CHECK comparators: tighten, never waive existing setup.
set_max_delay 5.5 -from [get_registers {*|control|check_next* *|reader|check_response_address*}] -to [get_registers {*|control|*}]
# CE/OE launch previously had only a post-route check. Guide that launch route.
# The independent70ns/16edge/PCB-allowance calculation must still pass afterward.
set_max_delay 12.0 -from [get_registers {*|reader|reading_active}] -to [get_ports {ROM_1CE ROM_2CE ROM_OE}]
