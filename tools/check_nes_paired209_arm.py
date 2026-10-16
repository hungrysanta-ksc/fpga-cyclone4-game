# SPDX-License-Identifier: MIT
"""Reuse203 whole linked RUN/IRQ bounds with209 identity; no stack waiver."""
import inspect,json
import check_nes_metadata203_arm as prior
from nes_board204 import ROOT,sha,replace
s=inspect.getsource(prior.main)
s=replace(s,'preparation-metadata203.json','preparation-paired209.json')
s=replace(s,'NES-META203-DEV','NES-GAME209-DEV')
s=replace(s,"for n,h in review['platform_sources'].items():assert sha(a.arm/'src'/n)==h,n",'''for n,h in review['platform_sources'].items():
  if n in ('nes_menu_diagnostic.c','nes_checkpoint112.c'):
   current=(a.arm/'src'/n).read_text()
   for x,y in [('NES-GAME-209','NES-GAME-186'),('GAME 209','GAME 186'),('game209.nes','game186.nes'),('fpga_n209.bi3','fpga_n186.bi3'),('last-209.txt','last-186.txt'),('NES209 seq=','NES186 seq='),('nes-progress-209.txt','nes-progress-186.txt')]:current=current.replace(x,y)
   if n=='nes_menu_diagnostic.c':
    start=current.index(' extra=snprintf(text+n,4096-(unsigned)n,"plan_error=')
    end=current.index(' printf("%s",text);',start)
    assert current[start:end].count('snprintf')==1 and 'native_runtime165.plan.finished?1u:0u' in current[start:end]
    current=current[:start]+current[end:]
   assert current==(BASE/'probes/nes-metadata203/arm01/src'/n).read_text(),n
   review['platform_sources'][n]=sha(a.arm/'src'/n)
  else:assert sha(a.arm/'src'/n)==h,n''')
s=replace(s,"(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\\n',encoding='utf8')",'''for m in [b'NES GAME 209.nh1',b'game209.nes',b'fpga_n209.bi3',b'nes-progress-209.txt',b'nes-game-last-209.txt',b'plan_error=%u']:
  assert m in (a.arm/'src/obj-nes-100/firmware.stm').read_bytes(),m
 r['paired209']=True
 r['public_sources'].update({n:sha(ROOT/n) for n in ['tools/nes_paired209.py','tools/check_nes_paired209_arm.py']})
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\\n',encoding='utf8')''')
ns=dict(prior.__dict__);exec(compile(s,'paired209-linked-check','exec'),ns)
if __name__=='__main__':ns['main']()
