# SPDX-License-Identifier: MIT
"""Run actual Cortex-M4 N5-v3 source decoder, 71 exact history comparisons."""
import inspect
import probe_nes_decode280 as old
from nes_hybrid340 import decoder,encode340

source=inspect.getsource(old.build).replace("shutil.copyfile(ROOT/'tools/nes_decode280.c',d/'nes_decode280.c')", "(d/'nes_decode280.c').write_text(decoder(),newline='\\n')")
ns=dict(old.__dict__);ns['decoder']=decoder
exec(compile(source,'build340','exec'),ns)
old.build=ns['build'];old.encode280=encode340
if __name__=='__main__':old.main()
