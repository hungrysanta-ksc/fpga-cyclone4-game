# SPDX-License-Identifier: MIT
"""Finish a latency exploration whose first case passed an expected-failure probe.
Keep the original probe and reuse its already complete first-case execution.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,sys
import nes_ncr1_live as live
def main():
 sys.argv.pop(1);p=argparse.ArgumentParser()
 for n in ('prepared','out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--delay',type=int,required=True);a=p.parse_args();src=a.prepared.resolve();out=a.out.resolve()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 m=json.loads((src/'result.json').read_text());assert not m['passed'] and m['delay_cycles']==a.delay and not m['cases']
 assert str(out).isascii() and not out.exists();out.mkdir()
 for n,h in m['sources'].items():
  assert live.sha(src/n)==h,n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src/n,dst)
 assert live.sha(out/'nes_rom_service.sv')==live.sha(live.ROOT/'src/nes/nes_rom_early.sv')
 shutil.copy2(src/'COPYING',out/'COPYING')
 shutil.copytree(src/'banks32',out/'banks32')
 # This refuses a failed/incomplete first case and checks its real pixels/bytes.
 first=live.verify_case(out,'banks32')
 m.update(candidate='NES-R1-ROM-EARLY-051',early_reads=True,passed=False,cases=[first],driver_sha256=live.sha(live.ROOT/'tools/nes_rom_early.py'),recovery_driver_sha256=live.sha(Path(__file__)),reused_case={'case':'banks32','original_result_sha256':live.sha(src/'result.json'),'simulation_log_sha256':live.sha(src/'banks32/simulation.log')})
 def save():live.put(out/'result.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,log,cwd=out):
  with log.open('wb') as f:p=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=900)
  assert p.returncode==0,str(log)
 save();run('vlib',['work'],out/'vlib.log')
 for i,n in enumerate(live.VHDL):run('vcom',['-2008',n],out/f'vcom-{i:02}.log')
 files=live.FILES+['nes_local_memory','nes_rom_service']
 run('vlog',['-sv','-mfcu',*live.SV,'cart_nrom.sv','nes_probe.sv',*[n+'.sv' for n in files],'rom_backend_model.sv','ncr1_live_tb.sv'],out/'vlog.log')
 c=out/'fine_x';c.mkdir();rom=live.ROOT/'analysis/local-video-workloads-021/fine_x/build'
 for n in ('prg.hex','chr.hex','manifest.json'):shutil.copy2(rom/n,c/n)
 live.put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
 run('vsim',['-c','-ini','modelsim.ini','work.ncr1_live_tb','+CHR32=0','+DELAY='+str(a.delay),'-do','onerror {quit -code 1}; run -all; quit -f'],c/'simulation.log',c)
 m['cases'].append(live.verify_case(out,'fine_x'));m['passed']=True;save();print('PASS latency exploration: verified original banks32, completed fine_x')
if __name__=='__main__':main()
