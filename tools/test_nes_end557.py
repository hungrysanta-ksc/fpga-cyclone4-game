# SPDX-License-Identifier: MIT
"""Observe when the final E9 can actually be taken in the coupled producer model."""
import runpy
from unittest.mock import patch

from trace_nes_obj518 import ObjLink


def credit_edge(link, clock, cause):
    if link.generation==954:
        link.phases.setdefault(954,{}).setdefault('credit_edges557',[]).append(
            dict(clock=clock, cause=cause, accepted=link.accepted, next_plan=link.plan_at))


if __name__=='__main__':
    with patch.object(ObjLink,'credit_edge557',credit_edge,create=True):
        runpy.run_module('test_nes_prelude554',run_name='__main__')
