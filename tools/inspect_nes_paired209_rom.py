# SPDX-License-Identifier: MIT
"""Verify ROM bytes in all three outputs produced by selected207 FIT EDA.
Default plus slow85/fast0 are ROM-constant checks, not a new timing analysis.
"""
import inspect
import inspect_nes_startup170_rom as prior
from nes_clip178 import replace
s=inspect.getsource(prior.main)
s=replace(s,"assert len(files)==4","assert {f.name for f in files}=={'board.vo','board_8_1200mv_85c_slow.vo','board_min_1200mv_0c_fast.vo'}")
s=replace(s,'Post-fit EDA atom constants at three corners and default','Post-fit EDA atom constants in default, slow85 and fast0 outputs; not new timing analysis')
s=replace(s,"'tools/inspect_nes_startup170_rom.py':sha(ROOT/'tools/inspect_nes_startup170_rom.py')","'tools/inspect_nes_paired209_rom.py':sha(ROOT/'tools/inspect_nes_paired209_rom.py'),'tools/inspect_nes_startup170_rom.py':sha(ROOT/'tools/inspect_nes_startup170_rom.py')")
s=replace(s,'PASS170 post-fit ROM atoms:4 netlists','PASS209 post-fit ROM atoms:3 netlists')
ns=dict(prior.__dict__);exec(compile(s,'paired209-ROM','exec'),ns)
if __name__=='__main__':ns['main']()
