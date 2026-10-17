# SPDX-License-Identifier: MIT
"""Replace only4KiB client ROM in selected220 route; inspect resulting atoms."""
from pathlib import Path
import inspect,json
import assemble_nes_paired186 as prior
from nes_runtime213 import ROOT,BASE,sha,once

s=inspect.getsource(prior.main)
s=once(s,"(a.baseline/'preparation.json')", "(a.baseline/'preparation220.json')")
s=s.replace('mif186','mif220').replace('asm186','asm220').replace('cpf186','cpf220').replace('fpga_n186.bi3','fpga_n220.bi3').replace('result186.json','result220.json').replace('assemble_nes_paired186.py','assemble_nes_paired220.py').replace('PASS186','PASS220')
s=once(s," (a.work/'result220.json').write_text", """ log=run([a.quartus_bin/'quartus_eda.exe','board','--simulation','--tool=modelsim','--format=verilog','--output_directory=simulation/modelsim'],a.work,'eda220',600)
 assert 'successful' in log and '0 errors' in log,log[-2000:]
 for n,h in preserved.items():
  if n!='board.qsf' and not n.startswith('simulation/'):assert sha(a.work/n)==h,n
 result['new_fit']=False
 (a.work/'result220.json').write_text""")
ns=dict(prior.__dict__);ns['__file__']=__file__;exec(compile(s,'assemble213','exec'),ns)
if __name__=='__main__':ns['main']()
