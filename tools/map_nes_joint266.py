# SPDX-License-Identifier: MIT
"""Hash-bound Quartus Lite MAP of the shared H2/display boundary."""
import inspect
import map_nes_joint265 as old
from nes_joint266 import sources


if __name__=='__main__':
 s=inspect.getsource(old.main).replace("top='nes_joint265'","top='nes_joint266'")
 ns=dict(old.__dict__);ns['sources']=sources
 exec(compile(s,'map266-derived','exec'),ns);ns['main']()
