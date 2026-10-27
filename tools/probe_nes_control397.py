# SPDX-License-Identifier: MIT
"""Passive warm/cold port and final-display-gate trace of selected396.
Exact actualM4/IRQ/SPI/2slot/ROM and actual65816 service remain unchanged.
"""
import argparse,json,shutil,subprocess,sys
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha,once
from probe_nes_refill267 import run

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);ref=BASE/'probes/nes-joint396/live07'
 for q in ref.iterdir():
  if q.is_file()and q.suffix in('.sv','.c','.h','.inc','.s','.a','.ld','.elf','.hex','.lens','.desc','.cfg','.bin','.expected','.palette','.dll'):shutil.copyfile(q,d/q.name)
 manifest=json.loads((ref/'manifest396.json').read_text());sources=list(manifest['RTL'])
 assert all(sha(d/n)==h for n,h in manifest['RTL'].items())and sha(d/'output.elf')==manifest['ELF']
 p=d/'joint266_tb.sv';s=p.read_text();at=s.rindex(' endmodule');s=s[:at]+(ROOT/'tests/nes-control397/ports.svh').read_text()+s[at:]
 s=once(s,'  check_final265();#(config394[1]*MASTER_NS378);', '''  check_final265();
  $fwrite(trace397,"view_done,%0d,%0d,%0d,%0d,%0t\\n",f,phase378(),config394[1],config394[2],$time);
  #(config394[1]*MASTER_NS378);
  $fwrite(trace397,"display_gate,%0d,%0d,%0d,%0d,%0d,%0t\\n",f,phase378(),config394[4],config394[2],blank378(),$time);''')
 s=once(s,'  origin=$realtime;window=(romcycle267+SNES_PHASE378)/357368;scroll=0;split=config394[5];', '''  $fwrite(trace397,"display_execute,%0d,%0d,%0t\\n",f,phase378(),$time);
  origin=$realtime;window=(romcycle267+SNES_PHASE378)/357368;scroll=0;split=config394[5];''')
 p.write_text(s,newline='\n');(d/'manifest397.json').write_text(json.dumps(dict(RTL=manifest['RTL'],ELF=manifest['ELF'],reference_test=sha(ref/'joint266_tb.sv'),test=sha(p),monitor=sha(ROOT/'tests/nes-control397/ports.svh')),indent=2)+'\n')
 q=Path('C:/altera_standard/25.1std/questa_fse/win64');run(q/'vlib.exe',['work'],d,'vlib');run(q/'vlog.exe',['-sv',*sources,'joint266_tb.sv'],d,'vlog')
 with(d/'arm-worker.log').open('wb')as log:
  worker=subprocess.Popen([sys.executable,str(ROOT/'tools/probe_nes_joint396.py'),'--worker','--out',str(d),'--last','916'],cwd=d,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
  try:
   try:run(q/'vsim.exe',['-c','-sv_lib','producer263','work.joint266_tb','-gCPI=1','-gROM_WINDOW=1','+LAST=916','-do','onerror {quit -code 1};run -all;quit -f'],d,'vsim',1800)
   except AssertionError:
    raw=(d/'vsim.log').read_text();assert 'Fatal: next capture deadline missed367 frame911'in raw and 'Errors: 1, Warnings: 0'in raw
   else:raise AssertionError('baseline unexpectedly passed')
  finally:
   if worker.poll()is None:worker.kill();worker.wait()
 assert sha(d/'joint-events.csv')==sha(ref/'joint-events.csv'),'observer changed actual event timeline'
 (d/'result.json').write_text(json.dumps(dict(audit_passed=True,implementation_changed=False,new_MAP=False,expected_capture_failure=911,timeline_exact396=True,manifest=sha(d/'manifest397.json'),trace=sha(d/'ports397.csv'),scope=__doc__),indent=2)+'\n');print('PASS PASSIVE397;396 actual timeline retained,first missed911')
if __name__=='__main__':main()
