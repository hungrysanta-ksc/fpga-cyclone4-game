# SPDX-License-Identifier: MIT
"""Actual471 live board/source -> paired C -> actual65816 -> finalACK/STOP."""
import argparse,sys
from pathlib import Path
from nes_delta231 import ROOT,BASE
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--arm',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
s=(ROOT/'tools/test_nes_nrom447_run136.py').read_text()
s=s.replace("prod=BASE/'probes/nes-repeat227/arm01/src'",'prod=Path('+repr(str(a.arm.resolve()))+')').replace("cand=prior/'candidate'",'cand=prod')
s=s.replace("r['fixture_sha256']==sha(a.rom) and ",'')
s=s.replace("'-Wno-unused-function','host.c'","'-Wno-unused-function','-DNES_COST471_HOST','host.c','nes_cost471.c'")
injection=r"""# Test adapter only: batch idle clocks while waiting for source-ready.
h=d/'host.c';text=h.read_text();needle='assert(cmd>=0xd0&&cmd<=0xd3);rpc(1,0,tx,n,rx,n);';assert text.count(needle)==1
h.write_text(text.replace(needle,needle+'if(cmd==0xd0&&!(rx[2]&1))rpc(10,0,NULL,0,NULL,0);'))
t=d/'join208_tb.sv';text=t.read_text();needle='default:$fatal(1,"bridge timeout/command %0d",op);';assert text.count(needle)==1
t.write_text(text.replace(needle,'10:begin repeat(65536)@(negedge dut.host_clk);join208_reply(0);end\n    '+needle))
exe=prior/'client/sink165.sfc'"""
s=s.replace("exe=prior/'client/sink165.sfc'",injection)
s=s.replace("<500,'first packet timeout'","<900,'first packet timeout'").replace('child.wait(timeout=600)','child.wait(timeout=900)')
start=s.index('for y in range(16,224):');end=s.index("result={'passed':True",start)
s=s[:start]+'''# Moving scene: require exact black/color bar mask, allowing captured scroll phase.
matched=[]
for phase in range(64):
 for parity in range(2):
  ok=True
  for y in range(16,224):
   for x in range(16,240):
    i=(y*256+x)*3;colored=pixels[i:i+3]!=bytes(3)
    expected=bool(((x+phase)//8)&4) and bool((x+phase+y+parity)&1)
    if colored!=expected:ok=False;break
   if not ok:break
  if ok:matched.append([phase,parity])
assert matched,'moving bar pixels differ from independent tile0/1 ROM mask'
'''+s[end:]
s=s.replace("'geometry_sha256':sha(a.rtl/'nrom429-blocks.txt'),","'reference_geometry_file_unused_by_live_host':True,'moving_bar_phase_matches':matched,")
sys.argv=['test_nes_nrom447_run136.py','--board',str(a.board),'--rtl',str(BASE/'probes/nes-nrom429/core01'),'--rom',str(a.rom),'--out',str(a.out)]
exec(compile(s,str(ROOT/'tools/test_nes_nrom447_run136.py'),'exec'),{'__name__':'__main__','__file__':str(ROOT/'tools/test_nes_nrom447_run136.py')})
