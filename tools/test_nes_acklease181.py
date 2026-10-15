# SPDX-License-Identifier: MIT
"""Actual endpoint differential wire test, real170 C replay, hostlease regression."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','baseline','out','questa-bin','gcc']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';a.out.mkdir(exist_ok=False)
 m=json.loads((a.prepared/'preparation.json').read_bytes())
 files=['nes_domain_reset124.sv','nes_sink_bridge165.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','sink-program.hex']
 for n in files:assert sha(a.prepared/n)==m['sources'][n],n;shutil.copy2(a.prepared/n,a.out/n)
 assert sha(a.baseline/'nes_sink_spi165.sv')==m['baseline_acklease_sources']['nes_sink_spi165.sv']
 s=(a.baseline/'nes_sink_spi165.sv').read_text();assert s.count('module nes_sink_spi165(')==1
 (a.out/'reference.sv').write_text(s.replace('module nes_sink_spi165(','module nes_sink_spi165_reference('),encoding='utf8',newline='\n')
 for n in ['acklease181_tb.sv','hostlease181_tb.sv','acklease181_host.c']:shutil.copy2(ROOT/'tests/nes-functional'/n,a.out/n)
 def run(cmd,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(x) for x in cmd],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/(label+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:]
  return s
 run([a.questa_bin/'vlib.exe','work'],'vlib')
 run([a.questa_bin/'vlog.exe','-sv',*files[:-1],'reference.sv','acklease181_tb.sv','hostlease181_tb.sv'],'compile')
 matches={}
 for bench in ['acklease181','hostlease181']:
  s=run([a.questa_bin/'vsim.exe','-c','work.'+bench+'_tb','-do','onerror {quit -code 1}; run -all; quit -f'],bench)
  mat=re.search(r'PASS '+bench.upper()+r'[^\r\n]*',s);assert mat,s[-3000:];matches[bench]=mat[0]
 fw=ROOT/'src/nes/firmware';(a.out/'firmware').mkdir()
 # Compile only frozen local copies, including all public header dependencies.
 for src in fw.glob('*.h'):shutil.copy2(src,a.out/'firmware'/src.name)
 for n in ['nes_sink_spi170.c','nes_sink_io170.c']:shutil.copy2(fw/n,a.out/'firmware'/n)
 run([a.gcc,'-std=c11','-Wall','-Wextra','-Werror','-O2','-Ifirmware','acklease181_host.c','firmware/nes_sink_spi170.c','firmware/nes_sink_io170.c','-o','host.exe'],'host-build')
 s=run([a.out/'host.exe','wire.txt'],'host-test');assert 'PASS ACKLEASE181 MCU' in s;matches['mcu']=s.strip()
 result=dict(passed=True,results=matches,scope=__doc__,hardware=False,runner_sha256=sha(Path(__file__)),
  files={str(x.relative_to(a.out)).replace('\\','/'):sha(x) for x in a.out.rglob('*') if x.is_file() and 'work' not in x.relative_to(a.out).parts})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(matches),flush=True)
if __name__=='__main__':main()
