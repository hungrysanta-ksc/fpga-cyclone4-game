# SPDX-License-Identifier: MIT
"""Full linked226 RUN/IRQ bound, including96B phase counters; no relaxed gate."""
import check_nes_scroll225_arm as prior
from nes_fast226 import runtime,once
s=prior.s.replace('preparation-scroll225.json','preparation-fast226.json')
s=once(s,"for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n", "assert sha(ROOT/'tools/nes_fast226.py')==prep['source_sha256']")
s=once(s,"instrumentation((BASE/'probes/nes-status220/arm01/src/nes_native_runtime165.c').read_text())", "runtime((BASE/'probes/nes-scroll225/arm01/src/nes_native_runtime165.c').read_text())")
s=s.replace("public_sources=prep['public_sources']|", "public_sources={'tools/nes_fast226.py':prep['source_sha256']}|")
for x,y in [('GAME 225','GAME 226'),('game225.nes','game226.nes'),('fpga_n225.bi3','fpga_n226.bi3'),('last-225.txt','last-226.txt'),('nes-progress-225.txt','nes-progress-226.txt'),('nes-budget-225.txt','nes-budget-226.txt'),('NES-GAME225-DEV','NES-GAME226-DEV'),('tools/check_nes_scroll225_arm.py','tools/check_nes_fast226_arm.py')]:s=s.replace(x,y)
ns=dict(prior.ns);ns.update(__file__=__file__,runtime=runtime);exec(compile(s,'check226','exec'),ns)
if __name__=='__main__':ns['main']()
