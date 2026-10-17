# SPDX-License-Identifier: MIT
"""Replay actual213 joined C packets/65816 ACKs through unchanged184 queue.
Reuse207 top mux checks; schedules regroup four credits, not measured timing.
"""
import inspect
import test_nes_binding209 as prior
from nes_runtime213 import once
s=inspect.getsource(prior.main)
s=once(s,'a.out=a.out.resolve();a.out.mkdir',"a.out=a.out.resolve();assert str(a.out).isascii(),'ASCII Questa path required';a.out.mkdir")
s=once(s,"BASE/'probes/nes-join208/test08'", "BASE/'probes/nes-runtime213/join01'")
s=s.replace("'tools/test_nes_binding209.py'","'tools/test_nes_binding213.py'")
ns=dict(prior.__dict__);ns.update(__file__=__file__,__doc__=__doc__)
exec(compile(s,'binding213','exec'),ns)
if __name__=='__main__':ns['main']()
