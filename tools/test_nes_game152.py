# SPDX-License-Identifier: MIT
"""Changed context boundary plus exact functional-source preservation check."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_game147 import ROOT,sha
from build_nes_game152 import build

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert not a.out.exists() and str(a.out).isascii()
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 e=a.baseline/'nes-game151/evidence';pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/game151-verification.json').read_bytes())['manifest_sha256']
 old=(e/'asm/nes_rom_service.sv').read_text();new=(ROOT/'src/nes/diagnostic/nes_rom_service152.sv').read_text()
 assert sha(e/'asm/nes_rom_service.sv')==pins['asm/nes_rom_service.sv']
 # Preserve fault_trigger too; only context combinational wiring is changed.
 a0=old[:old.index(' assign fault_context=')]+old[old.index(' always @(posedge clk'):]
 a1=new[:new.index(' //152 The top bit')]+new[new.index(' always @(posedge clk'):]
 assert a0==a1,'Service behavior changed outside context'
 a.out.mkdir(parents=True)
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_rom_service152.sv',a.out/'nes_rom_service.sv')
 shutil.copy2(ROOT/'tests/nes-functional/game152_context_tb.sv',a.out/'game152_context_tb.sv')
 for n in ['nes_game_bus151.sv']:
  assert sha(e/'asm'/n)==pins['asm/'+n];shutil.copy2(e/'asm'/n,a.out/n)
 s=(ROOT/'tests/nes-functional/game150_rom_tb.sv').read_text().replace('game150_rom_tb','game152_rom_tb').replace('nes_game_bus150','nes_game_bus151')
 (a.out/'game152_rom_tb.sv').write_text(s)
 shutil.copy2(build(a.out/'client'),a.out/'game-program.hex')
 def run(exe,args,log):
  with (a.out/log).open('wb') as f:r=subprocess.run([str(a.questa_bin/(exe+'.exe')),*args],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=180)
  s=(a.out/log).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (?:Error|Fatal):',s),(log,s[-2500:]);return s
 run('vlib',['work'],'vlib.log')
 run('vlog',['-sv','nes_rom_service.sv','nes_game_bus151.sv','game152_context_tb.sv','game152_rom_tb.sv'],'vlog.log')
 results={}
 for tb in ['context','rom']:
  s=run('vsim',['-c',f'work.game152_{tb}_tb','-do','onerror {quit -code 1}; run -all; quit -f'],tb+'.log')
  results[tb]=re.search(r'PASS GAME15[02][^\r\n]+',s)[0]
 result=dict(passed=True,results=results,service_behavior_exact151=True,hardware_fault_reproduced=False,ppu_error_fixed=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
