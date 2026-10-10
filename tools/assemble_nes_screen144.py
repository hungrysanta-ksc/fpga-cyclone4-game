# SPDX-License-Identifier: MIT
"""Assemble the selected144 fitted design; preserve its source/routing inputs."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,put,run,sha
from nes_cf68_pair_preflight import encode,decode
def main():
 p=argparse.ArgumentParser()
 for n in ['fit','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 inputs={f.relative_to(a.fit).as_posix():sha(f) for f in a.fit.rglob('*') if f.is_file()}
 shutil.copytree(a.fit,a.out)
 for label,args in [('asm',['quartus_asm.exe','board']),('cpf',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],a.out,label,300)
  assert 'successful. 0 errors, 0 warnings' in log and '25.1std.0 Build 1129' in log,log[-1500:]
 for n,h in inputs.items():
  assert sha(a.fit/n)==h,n
  if n.endswith(('.sv','.v','.vhd','.hex','.sdc','.qsf','.qpf','.fit.rpt','.fit.summary','.sta.rpt','.sta.summary')):assert sha(a.out/n)==h,n
 raw=(a.out/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (a.out/'fpga_n144.bi3').write_bytes(packed)
 result=dict(candidate='NES-SCREEN-144',inputs=inputs,rbf_bytes=len(raw),rbf_sha256=sha(a.out/'output_files/board.rbf'),packed_bytes=len(packed),packed_sha256=sha(a.out/'fpga_n144.bi3'),new_map_fit=False,physical=False)
 put(a.out/'result.json',json.dumps(result,indent=2)+'\n');shutil.copy2(__file__,a.out/'executed-assemble144.py');print('PASS144 ASM',len(raw),len(packed))
if __name__=='__main__':main()
