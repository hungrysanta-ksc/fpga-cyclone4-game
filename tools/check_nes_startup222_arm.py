# SPDX-License-Identifier: MIT
"""Full linked RUN/IRQ bound plus low-stack startup lifetime and source pins."""
import check_nes_index221_arm as prior
from nes_runtime213 import once
s=prior.s.replace('preparation-index221.json','preparation-startup222.json')
for x,y in [('GAME 221','GAME 222'),('game221.nes','game222.nes'),('fpga_n221.bi3','fpga_n222.bi3'),('last-221.txt','last-222.txt'),('nes-progress-221.txt','nes-progress-222.txt'),('nes-budget-221.txt','nes-budget-222.txt'),('NES-GAME221-DEV','NES-GAME222-DEV'),('tools/check_nes_index221_arm.py','tools/check_nes_startup222_arm.py')]:s=s.replace(x,y)
s=once(s," ns=dict(base.__dict__);ns['CALLBACKS']=cb;", """ s=once(s,'weights=su.get(name,[]);edges=set();indirect=[];selfcall=False',
  'weights=su.get(name,[]);edges=set();indirect=[];selfcall=False\\n  if name==\"native_frames222.isra.0\":\\n   assert sum(n==name for n,b in blocks.values())==1\\n   weights=su[\"native_frames222.isra\"];assert weights==[(31848,\"static\")]\\n   assert \"push\\\\t{r4, lr}\" in body and \"#31744\" in body and \"sp, #96\" in body')
 ns=dict(base.__dict__);ns['CALLBACKS']=cb;""")
s=once(s,"assert '<nes_budget210_attach>' not in new['native_session165']", """assert '<nes_budget210_attach>' not in new['native_session165']
 assert 'native_frames222' in new['native_session165']
 frames=[n for n in new if n.startswith('native_frames222')];assert len(frames)==1
 assert '<nes_runtime165_begin>' in new[frames[0]]
 usage=(a.arm/'src/obj-nes-100/nes_h1_stm32.su').read_text()
 w=re.search(r'native_session165\\s+(\\d+)\\s+static',usage);assert w and int(w[1])<=256
 from nes_startup222 import board,run
 oldsrc=BASE/'probes/nes-index221/arm01/src'
 assert (a.arm/'src/nes_runtime_board165.inc').read_text()==board((oldsrc/'nes_runtime_board165.inc').read_text())
 assert (a.arm/'src/nes_run136.inc').read_text()==run((oldsrc/'nes_run136.inc').read_text())
 r['startup_local_stack_bytes']=int(w[1])
 r['startup_work_after_ready']=True
 r['root_cause_proven']=False""")
ns=dict(prior.ns);ns['__file__']=__file__;exec(compile(s,'check222','exec'),ns)
if __name__=='__main__':ns['main']()
