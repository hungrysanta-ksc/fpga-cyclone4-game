# SPDX-License-Identifier: MIT
"""Reuse ARM object comparison including the195 implementation include."""
import inspect
import check_nes_map185_objects as prior
from nes_clip178 import replace
def main():
 source=replace(inspect.getsource(prior.main),"f.suffix in ['.c','.h']","f.suffix in ['.c','.h','.inc']")
 namespace=dict(prior.__dict__);namespace['__file__']=__file__
 exec(compile(source,'bulk195-object-check','exec'),namespace)
 namespace['main']()
if __name__=='__main__':main()
