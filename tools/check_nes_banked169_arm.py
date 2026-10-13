# SPDX-License-Identifier: MIT
"""Reuse the full linked168 checker for169 naming-only MCU, retaining trace168."""
import inspect
import check_nes_sink168_arm as prior
# Binutils renders an absolute Korean filename in the host code page. Keep the
# executable input path relative, as the outer168 checker already does.
inner=inspect.getsource(prior.checker.main)
anchor="*args,str(elf)])"
assert inner.count(anchor)==1
inner=inner.replace(anchor,"*args,'src/obj-nes-100/sd2snes.elf'],cwd=a.arm)")
inner_ns=dict(prior.checker.__dict__);exec(compile(inner,'linked_banked169','exec'),inner_ns)
prior.checker.main=inner_ns['main']
source=inspect.getsource(prior.main)
for a,b in [("b'NES-GAME168-DEV'","b'NES-GAME169-DEV'"),("b'NES GAME 168.nh1'","b'NES GAME 169.nh1'"),("b'nes-progress-168.txt'","b'nes-progress-169.txt'"),("b'nes-game-last-168.txt'","b'nes-game-last-169.txt'")]:
 assert a in source;source=source.replace(a,b)
source=source.replace('New168 ACK trace checked; FPGA and SNES unchanged.','169 names only; trace168 and MCU RUN unchanged. SNES169 assessed separately.')
source=source.replace("'tools/check_nes_sink168_arm.py','tools/nes_sink_trace168.py'","'tools/check_nes_banked169_arm.py','tools/check_nes_sink168_arm.py','tools/nes_banked169_mcu.py'")
namespace=dict(prior.__dict__);exec(compile(source,'check_banked169','exec'),namespace)
if __name__=='__main__':namespace['main']()
