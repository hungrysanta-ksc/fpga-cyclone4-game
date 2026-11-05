# SPDX-License-Identifier: MIT
"""Counterfactual schedule: re-enable only the second BG flush in first-fill 906."""
import runpy
from unittest.mock import patch

from check_nes_game478 import UC_HOOK_CODE, UC_ARM_REG_R0
from test_nes_raw506_joint import Runtime


if __name__ == '__main__':
    init = Runtime.__init__
    changes = []

    def watch(machine, args, link):
        init(machine, args, link)
        def first_emit(u, at, size, unused):
            if machine.generation != 906 or changes:
                return
            plan = u.reg_read(UC_ARM_REG_R0)
            assert plan == machine.rt + machine.layout['nes_native_runtime165']['plan']
            assert machine.get(plan, 'nes_plan200', 'bank_history') == 1
            machine.put(plan, 'nes_plan200', 'bank_history', 2, 1)
            changes.append(machine.generation)
        pc = machine.syms['nes_plan200_emit']
        machine.u.hook_add(UC_HOOK_CODE, first_emit, begin=pc, end=pc)

    with patch.object(Runtime, '__init__', watch):
        runpy.run_module('test_nes_board611', run_name='__main__')
    assert changes == [906]
