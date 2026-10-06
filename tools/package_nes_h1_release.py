# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,zipfile
from manage_nes_h1_release_sd import CANDIDATE,EXPECTED,FIRMWARE,FPGA,BASELINE_FW,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 assert not out.exists() and not out.with_suffix('.zip').exists()
 raw=ROOT/'analysis/local-h1-release-040'
 rtl=json.loads((raw/'rtl/result.json').read_text());assert rtl['passed'] and rtl['release']['normal_cases']==156 and rtl['release']['real_abort_cases']==72
 assert rtl['release']['board_signature']['legacy_F2']==7 and rtl['release']['board_signature']['fixed_F2']==3
 assert sha(ROOT/'analysis/local-h1-fault-039/arm/firmware.stm')==BASELINE_FW
 assert json.loads((raw/'decoder/result.json').read_text())['passed']
 dest=out/'sd-overlay'/FPGA;dest.parent.mkdir(parents=True);shutil.copy2(raw/'resource/fpga_nh1.bi3',dest)
 assert sha(dest)==EXPECTED[FPGA]
 shutil.copy2(ROOT/'tools/manage_nes_h1_release_sd.py',out/'manage_nes_h1_release_sd.py')
 shutil.copy2(ROOT/'docs/nes-h1-release-test.ko.md',out/'READ-ME.ko.md')
 shutil.copy2(ROOT/'analysis/local-h1-board-034/board-reference-contact.png',out/'reference-034.png')
 m={'candidate':CANDIDATE,'change':'Qualify ROMSEL abort by active raw RD; preserve039 MCU and first-fault snapshot','hardware_executed':False,'baseline':{'firmware.stm':BASELINE_FW,'fpga_nh1.bi3':'7d12e8126cbe137b12a81345e537c74a707bd0cfa200149ae7a27379e310c056'},'existing_marker':'NES H1 037.nh1','visible_title':'NES H1 034','output_log':'sd2snes/nes-h1-last-039.txt','reference':'Actual034 emulator capture; same ROM, no new emulator execution','files':[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()]}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with zipfile.ZipFile(out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(out.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(out))
 print(json.dumps({'zip':str(out.with_suffix('.zip')),'sha256':sha(out.with_suffix('.zip'))}))
if __name__=='__main__':main()
