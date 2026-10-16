# SPDX-License-Identifier: MIT
"""Assemble selected207 routing unchanged, then export post-fit ROM evidence.
No MAP/FIT/STA or MIF update. All writes occur in a fresh ASCII clone.
"""
from pathlib import Path
import argparse,json,shutil
from nes_board204 import ROOT,BASE,sha
from nes_spi_boot import run
from nes_cf68_pair_preflight import encode,decode

def main():
 p=argparse.ArgumentParser()
 for n in ['work','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert a.work.as_posix().isascii() and not a.work.exists()
 fit=BASE/'probes/nes-board207/mapfit02'
 prep=json.loads((fit/'preparation207.json').read_bytes())
 for n,h in prep['sources'].items():assert sha(fit/n)==h,n
 pins={f.relative_to(fit).as_posix():sha(f) for f in fit.rglob('*') if f.is_file()}
 shutil.copytree(fit,a.work)
 (a.work/'input-inventory.json').write_text(json.dumps(pins,indent=2)+'\n',encoding='utf8')
 for label,args in [('asm209',['quartus_asm.exe','board']),('cpf209',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  s=run([a.quartus_bin/args[0],*args[1:]],a.work,label,300);assert 'successful' in s and '0 errors' in s,s[-2000:]
 unchanged={}
 for n,h in pins.items():
  assert sha(fit/n)==h,n
  if n in prep['sources'] or n.endswith(('.fit.rpt','.fit.summary','.rcf','.pin')):
   assert sha(a.work/n)==h,n;unchanged[n]=h
 raw=(a.work/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.work/'fpga_n209.bi3').write_bytes(packed)
 s=run([a.quartus_bin/'quartus_eda.exe','board','--simulation','--tool=modelsim','--format=verilog','--output_directory=simulation/modelsim'],a.work,'eda209',600)
 assert 'successful' in s and '0 errors' in s,s[-2000:]
 # EDA may append output settings to QSF; it is not used to assemble this RBF.
 for n,h in unchanged.items():
  if n!='board.qsf':assert sha(a.work/n)==h,n
 result=dict(passed=True,baseline_pins=pins,unchanged_assembly_sources_and_routing=unchanged,
  client_sha256=sha(a.work/'sink-program.hex'),rbf_sha256=sha(a.work/'output_files/board.rbf'),fpga_sha256=sha(a.work/'fpga_n209.bi3'),
  method='Unchanged selected207 FIT -> ASM/CPF -> EDA post-fit evidence; no new MAP/FIT/STA/MIF update',new_fit=False,physical=False,
  public_sources={'tools/assemble_nes_paired209.py':sha(ROOT/'tools/assemble_nes_paired209.py')})
 (a.work/'result209.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps({k:v for k,v in result.items() if k not in ['baseline_pins','unchanged_assembly_sources_and_routing']}))
if __name__=='__main__':main()
