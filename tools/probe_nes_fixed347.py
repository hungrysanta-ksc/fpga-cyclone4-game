# SPDX-License-Identifier: MIT
"""Execute proposed fixed-block receiver on M4, not integrated pipeline."""
import inspect
import probe_nes_decode280 as old
from nes_fixed347 import decoder,encode347
s=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')", "(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
ns=dict(old.__dict__);ns['decoder']=decoder
exec(compile(s,'build347','exec'),ns)
old.build=ns['build'];old.encode280=encode347
if __name__=='__main__':old.main()
