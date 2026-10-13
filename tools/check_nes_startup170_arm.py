# SPDX-License-Identifier: MIT
"""Full linked RUN/IRQ graph; reuse relocated library-body audit, add20B trace."""
import inspect
import check_nes_banked169_arm as prior
source=prior.source
for a,b in [('GAME169-DEV','GAME170-DEV'),('GAME 169.nh1','GAME 170.nh1'),('progress-169.txt','progress-170.txt'),('last-169.txt','last-170.txt')]:
 assert a in source;source=source.replace(a,b)
source=source.replace("result.update(trace_bytes=32", "assert re.search(r'^\\S+ 00000014 B nes_sink_io170$',nm,re.M)\n assert b'sink_io170=' in fw\n result.update(io_trace_bytes=20,trace_bytes=32")
source=source.replace("'tools/check_nes_banked169_arm.py','tools/check_nes_sink168_arm.py','tools/nes_banked169_mcu.py'", "'tools/check_nes_startup170_arm.py','tools/nes_startup170.py','src/nes/firmware/nes_sink_spi170.c','src/nes/firmware/nes_sink_io170.c','src/nes/firmware/nes_sink_io170.h'")
source=source.replace('169 names only; trace168 and MCU RUN unchanged. SNES169 assessed separately.','170 adds20B first exchange failure trace; full RUN/IRQ graph recomputed. FPGA/SNES169 unchanged.')
namespace=dict(prior.namespace);exec(compile(source,'check_startup170','exec'),namespace)
if __name__=='__main__':namespace['main']()
