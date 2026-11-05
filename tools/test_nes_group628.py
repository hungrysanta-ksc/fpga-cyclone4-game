# SPDX-License-Identifier: MIT
"""Recognize a checked delta in the independent early-VRAM scoreboard."""
import runpy
from unittest.mock import patch
import trace_nes_map527
from test_nes_raw506_joint import Runtime
from nes_raw506 import once


if __name__=='__main__':
    original=trace_nes_map527.observer
    def observer(src,labels):
        return once(original(src,labels),'(pb(0)==2 or pb(0)==4) then',
                    '(pb(0)==2 or pb(0)==4 or pb(0)==9) then')
    with patch.object(trace_nes_map527,'observer',observer), patch.object(Runtime,'linked_runtime_storage',True,create=True):
        runpy.run_module('test_nes_board611',run_name='__main__')
