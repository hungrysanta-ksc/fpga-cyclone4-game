# SPDX-License-Identifier: MIT
"""Passive clock/port ownership trace of394. No implementation/time gain.
Retains exact M4/RTL/native service/fixed907 deadline and its expected failure."""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);reference=BASE/'probes/nes-jobs394/joint09'
 for f in reference.iterdir():
  if f.is_file()and f.suffix in('.sv','.c','.h','.inc','.s','.a','.ld','.elf','.hex','.lens','.desc','.cfg','.bin','.expected','.palette','.dll'):shutil.copyfile(f,d/f.name)
 m=json.loads((reference/'manifest394.json').read_text());sources=list(m['materialized_RTL']);assert all(sha(d/n)==h for n,h in m['materialized_RTL'].items());assert sha(d/'output.elf')==m['ELF']
 p=d/'joint266_tb.sv';s=p.read_text();at=s.rindex(' endmodule');s=s[:at]+(ROOT/'tests/nes-owners395/ports.svh').read_text()+s[at:];p.write_text(s,newline='\n')
 (d/'manifest395.json').write_text(json.dumps(dict(scope=__doc__,reference_test=sha(reference/'joint266_tb.sv'),test=sha(p),RTL=m['materialized_RTL'],ELF=sha(d/'output.elf'),monitor=sha(ROOT/'tests/nes-owners395/ports.svh')),indent=2)+'\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*sources,'joint266_tb.sv'],d,'vlog')
 with(d/'arm-worker.log').open('wb')as log:
  worker=subprocess.Popen([sys.executable,str(ROOT/'tools/probe_nes_jobs394_joint.py'),'--worker','--out',str(d),'--last','916'],cwd=d,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   try:run(q/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb','-gCPI=1','-gROM_WINDOW=1','+LAST=916','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',1800)
   except AssertionError:
    raw=(d/'vsim.log').read_text();assert 'Fatal: startup missed fixed capture368'in raw and 'Errors: 1, Warnings: 0'in raw
   else:raise AssertionError('baseline unexpectedly passed')
  finally:
   if worker.poll()is None:worker.kill();worker.wait()
 (d/'result.json').write_text(json.dumps(dict(audit_passed=True,expected_startup_failure=907,implementation_changed=False,manifest=sha(d/'manifest395.json'),trace=sha(d/'ports395.csv'),scope=__doc__),indent=2)+'\n');print('PASS PASSIVE395;strict394 startup failure retained')
if __name__=='__main__':main()
