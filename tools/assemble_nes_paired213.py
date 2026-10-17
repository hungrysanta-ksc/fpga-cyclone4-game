# SPDX-License-Identifier: MIT
"""Replace only4KiB client ROM in frozen207 route; inspect resulting atoms."""
from pathlib import Path
import inspect,json
import assemble_nes_paired186 as prior
from nes_runtime213 import ROOT,BASE,sha,once

s=inspect.getsource(prior.main)
s=once(s,"(a.baseline/'preparation.json')", "(a.baseline/'preparation207.json')")
s=s.replace('mif186','mif213').replace('asm186','asm213').replace('cpf186','cpf213').replace('fpga_n186.bi3','fpga_n213.bi3').replace('result186.json','result213.json').replace('assemble_nes_paired186.py','assemble_nes_paired213.py').replace('PASS186','PASS213')
s=once(s," (a.work/'result213.json').write_text", """ log=run([a.quartus_bin/'quartus_eda.exe','board','--simulation','--tool=modelsim','--format=verilog','--output_directory=simulation/modelsim'],a.work,'eda213',600)
 assert 'successful' in log and '0 errors' in log,log[-2000:]
 for n,h in preserved.items():
  if n!='board.qsf' and not n.startswith('simulation/'):assert sha(a.work/n)==h,n
 result['new_fit']=False
 (a.work/'result213.json').write_text""")
ns=dict(prior.__dict__);ns['__file__']=__file__;exec(compile(s,'assemble213','exec'),ns)
if __name__=='__main__':ns['main']()
