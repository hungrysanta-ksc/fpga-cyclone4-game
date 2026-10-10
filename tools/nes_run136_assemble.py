# SPDX-License-Identifier: MIT
"""ASM/CPF from frozen135 fit03, without a new fit or hardware approval."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,put,run,sha
from nes_cf68_pair_preflight import encode,decode

def main():
 p=argparse.ArgumentParser()
 for n in ['evidence135','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();e=a.evidence135.resolve();o=a.out.resolve()
 meta=json.loads((ROOT/'analysis/command135-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 assert str(o).isascii() and not o.exists() and not o.is_relative_to(e)
 manifest=json.loads((e/'manifest.json').read_bytes())['files']
 inputs={n.removeprefix('fit03/'):h for n,h in manifest.items() if n.startswith('fit03/')}
 assert any(n.startswith('db/') for n in inputs) and any(n.startswith('incremental_db/') for n in inputs)
 for n,h in inputs.items():
  assert sha(e/'fit03'/n)==h,n
  dest=o/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/'fit03'/n,dest)
 put(o/'input-lineage.json',json.dumps(inputs,indent=2)+'\n')
 shutil.copy2(__file__,o/'executed-assemble136.py')
 for label,args in [('asm',['quartus_asm.exe','board']),('cpf',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
  log=run([a.quartus_bin/args[0],*args[1:]],o,label,300)
  assert 'successful. 0 errors, 0 warnings' in log and '25.1std.0 Build 1129' in log,log[-1500:]
 for n,h in inputs.items():
  assert sha(e/'fit03'/n)==h,n
  if n.endswith(('.sv','.sdc','.qsf','.qpf','.fit.rpt','.fit.summary','.sta.rpt','.sta.summary')):assert sha(o/n)==h,n
 raw=(o/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
 (o/'fpga_n136.bi3').write_bytes(packed)
 result=dict(candidate='NES-RUN-136',fit135_manifest=meta['manifest_sha256'],inputs=inputs,rbf_bytes=len(raw),rbf_sha256=sha(o/'output_files/board.rbf'),packed_bytes=len(packed),packed_sha256=sha(o/'fpga_n136.bi3'),encoder_sha256=sha(ROOT/'tools/nes_cf68_pair_preflight.py'),terminal_marker_added=False,new_map_fit_sta=False,installable=False,physical=False)
 put(o/'result.json',json.dumps(result,indent=2)+'\n');print('PASS136 ASM RBF=%d packed=%d'%(len(raw),len(packed)),flush=True)
if __name__=='__main__':main()
