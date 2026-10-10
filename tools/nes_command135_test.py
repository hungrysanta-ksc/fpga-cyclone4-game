# SPDX-License-Identifier: MIT
"""Changed validator: prior exact SPI retirement suite, differential and board RUN."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_command135 import prepare
from nes_cdc125_sta import ROOT,sha,put
from nes_functional import VHDL

def main():
 p=argparse.ArgumentParser()
 for n in ['out','baseline','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 names=prepare(a.baseline,o)
 e=a.baseline/'nes-command128/evidence';meta=json.loads((ROOT/'analysis/command128-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];n='test06/spi_readback_control_tb.sv';assert sha(e/n)==pins[n]
 shutil.copy2(e/n,o/'spi_readback_control_tb.sv')
 source=a.baseline/'nes-board134/evidence/fit02/nes_rom_spi.sv'
 put(o/'baseline135.sv',source.read_text().replace('module nes_rom_spi_check(','module baseline135('))
 source=a.baseline/'nes-board134/evidence/fit02/nes_rom_boot.sv'
 put(o/'baseline_boot135.sv',source.read_text().replace('module nes_rom_boot(','module baseline_boot135('))
 shutil.copy2(ROOT/'tests/nes-functional/command135_diff_tb.sv',o/'command135_diff_tb.sv')
 shutil.copy2(ROOT/'tests/nes-functional/boot135_diff_tb.sv',o/'boot135_diff_tb.sv')
 for n in ['nes_command135.py','nes_command135_test.py']:shutil.copy2(ROOT/'tools'/n,o/('executed-'+n))
 m=dict(passed=False,runs={},full_load_check=False,physical_trial=False)
 def save():put(o/'test135.json',json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 def sim(top,label,expected,extra=[]):
  log=run('vsim',['-c',top,*extra,'-do','onerror {quit -code 1}; run -all; quit -f'],label)
  assert expected in log,label
  if expected.startswith('PASS'):assert '** Fatal:' not in log,label
  m['runs'][label]=[x for x in log.splitlines() if 'PASS' in x or '** Fatal:' in x];save()
 save();run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*[n for n in names if n not in VHDL],'rom_boot_model.sv','run133_pll_model.sv','nes_run_observer134.sv','fxpak_nes_run134_top.sv','board134_tb.sv','spi_readback_control_tb.sv','baseline135.sv','command135_diff_tb.sv','baseline_boot135.sv','boot135_diff_tb.sv'],'compile')
 sim('command135_diff_tb','equivalence','PASS135 cause equivalence cases=4194304')
 sim('boot135_diff_tb','boot-equivalence','PASS135 boot sticky equivalence cases=4096')
 for half in [60,18]:sim('spi_readback_control_tb','decoder-'+str(half),'PASS SPI CHECK CONTROL',['-gHALF127='+str(half)])
 for phase in [0,3500]:sim('board134_tb','board-'+str(phase),'PASS134',['+PHASE_PS='+str(phase)])
 original=(o/'nes_rom_spi.sv').read_text()
 needle="pending_causes[1]?4'd5";assert original.count(needle)==1
 put(o/'wrong-priority.sv',original.replace(needle,"pending_causes[1]?4'd0"))
 run('vlog',['-sv','wrong-priority.sv'],'negative-cause-compile');sim('command135_diff_tb','negative-cause','** Fatal: CAUSE135 mismatch')
 needle='if(check_fault || (check_enable && boot_fault))fail(9);';assert needle in original
 put(o/'late-fault.sv',original.replace(needle,'if(!pending && (check_fault || (check_enable && boot_fault)))fail(9);'))
 run('vlog',['-sv','late-fault.sv'],'negative-fault-compile');sim('spi_readback_control_tb','negative-fault','RETIRE128 hard fault wins START')
 original_boot=(o/'nes_rom_boot.sv').read_text();needle='!check_enable || !raw_check_ready || !address_valid';assert needle in original_boot
 put(o/'missing-owner.sv',original_boot.replace(needle,'!raw_check_ready || !address_valid'))
 run('vlog',['-sv','missing-owner.sv'],'negative-owner-compile');sim('boot135_diff_tb','negative-owner','** Fatal: BOOT135 mismatch')
 m['passed']=True;save();print('PASS135 cause equivalence, actual retirement and physical-shell RUN; three negatives rejected')
if __name__=='__main__':main()
