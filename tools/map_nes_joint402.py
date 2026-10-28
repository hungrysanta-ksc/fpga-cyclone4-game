# SPDX-License-Identifier: MIT
"""Whole Lite of exact402 functional materialization; no local-cell subtraction."""
import argparse,json,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,sha

def main():
 p=argparse.ArgumentParser();p.add_argument('--rtl',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 ref=BASE/'probes/nes-joint400/map01'
 for q in ref.rglob('*'):
  rel=q.relative_to(ref)
  if any(x in('db','incremental_db','work','output_files')for x in rel.parts):continue
  if q.is_file()and q.suffix.lower()in('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
   out=d/rel;out.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,out)
 manifest=json.loads((a.rtl/'manifest402.json').read_text());sources=manifest['RTL']
 for n,h in sources.items():assert sha(a.rtl/n)==h;shutil.copyfile(a.rtl/n,d/n)
 if 'nes_byte398.sv'in sources:shutil.copyfile(a.rtl/'program398.hex',d/'program398.hex')
 p=d/'board.qsf';s=p.read_text()
 if 'nes_byte398.sv'not in sources:s='\n'.join(x for x in s.splitlines()if 'nes_byte398.sv'not in x)
 p.write_text(s+'\n',newline='\n')
 inputs={q.relative_to(d).as_posix():sha(q)for q in d.rglob('*')if q.is_file()}
 with(d/'map.log').open('wb')as log:r=subprocess.run(['C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe','board'],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=900,creationflags=subprocess.CREATE_NO_WINDOW)
 raw=(d/'map.log').read_text(errors='replace');bad=re.findall(r'Warning \(10034\):[^\r\n]+',raw)
 rpt=(d/'output_files/board.map.rpt').read_text()if(d/'output_files/board.map.rpt').exists()else''
 fallback=re.findall(r'RAM logic "[^\n]*(?:previous|rank402|metadata402|storage402)" is uninferred[^\n]*',raw)
 expected=[]
 if 'previous_q402'in(d/'nes_native_compact181.sv').read_text():expected+=['previous_rtl_0','rank402_rtl_0','maps_rtl_0']
 cache=(d/'nes_chr_cache192.sv').read_text();expected+=['storage402_rtl_0']if'storage402'in cache else['metadata402_rtl_0']if'metadata402'in cache else[]
 missing=[n for n in expected if n not in rpt]
 result=dict(passed=r.returncode==0 and not bad and not fallback and not missing,actual_inputs=inputs,functional_RTL=sources,undriven=bad,new_RAM_fallback=fallback,missing_expected_RAM=missing,FIT=False,STA=False)
 if(d/'output_files/board.map.summary').exists():result['summary']=(d/'output_files/board.map.summary').read_text()
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps({k:v for k,v in result.items()if k not in('actual_inputs','functional_RTL')},indent=2));assert result['passed']
if __name__=='__main__':main()
