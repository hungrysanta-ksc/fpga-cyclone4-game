# SPDX-License-Identifier: MIT
"""Reuse 170 ROM-atom checker on the single Lite default EDA netlist."""
import inspect
import inspect_nes_startup170_rom as prior
s=inspect.getsource(prior.main)
assert s.count('assert len(files)==4')==1
s=s.replace('assert len(files)==4',"assert [f.name for f in files]==['board.vo']")
s=s.replace('Post-fit EDA atom constants at three corners and default','One Lite default post-fit EDA netlist only; no corner netlists, RBF extraction or physical readback')
s=s.replace('PASS170 post-fit ROM atoms:4 netlists','PASS423 post-fit ROM atoms:1 netlist')
ns=dict(prior.__dict__);exec(compile(s,'nrom423-ROM','exec'),ns)
if __name__=='__main__':ns['main']()
