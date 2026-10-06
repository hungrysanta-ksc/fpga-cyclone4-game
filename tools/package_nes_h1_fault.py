# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,zipfile
from manage_nes_h1_fault_sd import CANDIDATE,EXPECTED,FIRMWARE,FPGA,BASELINE_FW,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 assert not out.exists() and not out.with_suffix('.zip').exists()
 raw=ROOT/'analysis/local-h1-fault-039'
 assert json.loads((raw/'rtl/result.json').read_text())['passed']
 assert len(json.loads((raw/'host-01/result.json').read_text())['cases'])==15
 fw=raw/'arm/firmware.stm';assert sha(fw)==EXPECTED[FIRMWARE]
 dest=out/'sd-overlay'/FIRMWARE;dest.parent.mkdir(parents=True);shutil.copy2(fw,dest)
 shutil.copy2(raw/'resource/fpga_nh1.bi3',out/'sd-overlay'/FPGA)
 assert sha(out/'sd-overlay'/FPGA)==EXPECTED[FPGA]
 shutil.copy2(ROOT/'tools/manage_nes_h1_fault_sd.py',out/'manage_nes_h1_fault_sd.py')
 shutil.copy2(ROOT/'docs/nes-h1-fault-test.ko.md',out/'READ-ME.ko.md')
 m={'candidate':CANDIDATE,'diagnostic_not_root_cause_fix':True,'hardware_executed':False,'baseline':{'firmware.stm':BASELINE_FW,'fpga_nh1.bi3':'6de44eeea2c8692f303bc8aa66a572cec076710bb7ab6b034310f5abd63ad913'},'existing_marker':'NES H1 037.nh1','visible_title':'NES H1 034','output_log':'sd2snes/nes-h1-last-039.txt','files':[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()]}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with zipfile.ZipFile(out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(out.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(out))
 print(json.dumps({'zip':str(out.with_suffix('.zip')),'sha256':sha(out.with_suffix('.zip'))}))
if __name__=='__main__':main()
