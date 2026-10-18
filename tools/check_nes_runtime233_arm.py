# SPDX-License-Identifier: MIT
"""Linked233 output RUN/IRQ bound; reserved source state is NOT delta binding."""
import check_nes_repeat227_arm as prior
from nes_runtime233 import runtime,board,once

s=prior.s.replace('preparation-repeat227.json','preparation-runtime233.json')
s=once(s,"runtime((BASE/'probes/nes-scroll225/arm01/src/nes_native_runtime165.c').read_text())",
       "runtime((BASE/'probes/nes-repeat227/arm01/src/nes_native_runtime165.c').read_text())")
s=once(s,'[(31848,"static")]','[(32016,"static")]')
s=once(s,'"#31744" in body and "sp, #96" in body','"#32000" in body and "sp, #8" in body')
a=s.index(' from nes_startup222 import board,run');b=s.index(" r['startup_local_stack_bytes']",a)
s=s[:a]+''' oldsrc=BASE/'probes/nes-repeat227/arm01/src'
 assert (a.arm/'src/nes_runtime_board165.inc').read_text()==board((oldsrc/'nes_runtime_board165.inc').read_text())
 assert (a.arm/'src/nes_run136.inc').read_bytes()==(oldsrc/'nes_run136.inc').read_bytes()
'''+s[b:]
s=once(s," assert '<nes_resident211_reset>' in new['nes_runtime165_begin']", """ assert '<nes_resident211_reset>' in new['nes_runtime165_begin']
 assert '<nes_dirty231_reset>' in new['nes_runtime165_begin']
 assert '<nes_source231_reset>' in new['nes_runtime165_begin']
 assert '<nes_native_video231_plan>' in new['nes_runtime165_step']
 assert '<nes_sink231_seal>' in new['nes_runtime165_step']
 assert 'nes_source231_begin' not in new  # ingress233 not implemented/bound
 r['output231_bound']=True;r['source_state_reserved']=36;r['ingress_delta_bound']=False
 r['complete_delta_runtime_approved']=False
""")
for a,b in [('GAME 227','GAME 233'),('game227.nes','game233.nes'),('fpga_n227.bi3','fpga_n233.bi3'),('last-227.txt','last-233.txt'),('nes-progress-227.txt','nes-progress-233.txt'),('nes-budget-227.txt','nes-budget-233.txt'),('NES-GAME227-DEV','NES-GAME233-DEV'),('tools/check_nes_repeat227_arm.py','tools/check_nes_runtime233_arm.py')]:s=s.replace(a,b)
ns=dict(prior.ns);ns.update(__file__=__file__,runtime=runtime,board=board)
exec(compile(s,'runtime233-linked-check','exec'),ns)
if __name__=='__main__':ns['main']()
