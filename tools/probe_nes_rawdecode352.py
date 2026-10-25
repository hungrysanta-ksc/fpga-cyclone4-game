# SPDX-License-Identifier: MIT
"""Charge changed-group tracking in the actual M4 source decoder."""
import inspect
import probe_nes_decode280 as old
from nes_raw352 import decoder
ns=dict(old.__dict__);ns['decoder']=decoder
s=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')", "(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
exec(compile(s,__file__,'exec'),ns);old.build=ns['build']
if __name__=='__main__':old.main()
