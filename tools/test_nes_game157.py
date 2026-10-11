# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['prepared','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 assert not a.out.exists();a.out.mkdir(parents=True)
 names=['nes_run_observer134.sv','nes_pad_trace156.sv','nes_ppu_history157.sv','nes_rom_service.sv']
 for n in names:shutil.copy2(a.prepared/n,a.out/n)
 shutil.copy2(ROOT/'tests/nes-functional/game157_history_tb.sv',a.out/'history157_tb.sv')
 shutil.copy2(ROOT/'tests/nes-functional/game157_service_tb.sv',a.out/'service157_tb.sv')
 for label,cmd in [('vlib',['vlib','work']),('vlog',['vlog','-sv',*names,'history157_tb.sv','service157_tb.sv']),('vsim',['vsim','-c','work.history157_tb','-do','onerror {quit -code 1}; run -all; quit -f']),('service',['vsim','-c','work.service157_tb','-do','onerror {quit -code 1}; run -all; quit -f'])]:
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(cmd[0]+'.exe')),*cmd[1:]],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=120)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-2500:]
 assert 'PASS157' in s
 (a.out/'result.json').write_text(json.dumps(dict(passed=True,sources={n:sha(a.out/n) for n in names},testbenches={n:sha(a.out/n) for n in ['history157_tb.sv','service157_tb.sv']},physical=False,scope='Actual SPI observer/retained ring/service. Two synthetic request histories produce identical156 fault tuple but distinguishable history. Not physical root-cause reproduction.'),indent=2)+'\n');print('PASS157 history SPI and service ambiguity')
if __name__=='__main__':main()
