# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,shutil,zipfile
from manage_nes_h1_sd import CANDIDATE,EXPECTED,FIRMWARE,FPGA,MARKER,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 out=a.out.resolve();assert not out.exists() and not out.with_suffix('.zip').exists()
 sweep=json.loads((ROOT/'analysis/local-h1-bringup-037/rtl/result.json').read_text())
 assert len(sweep['runs'])==24 and all(e['passed'] for e in sweep['runs'])
 assert sweep['compiled_boundary_sha256']=='4673a76c45f91c7ef5469ec3e985528251279fb92ad310bca81718ccbc7f1c8f'
 sources={FIRMWARE:ROOT/'analysis/local-h1-firmware-035/arm-final/firmware-h1-035.stm',FPGA:ROOT/'analysis/local-h1-spi-036/resource/fpga_nh1.bi3'}
 for n,f in sources.items():assert sha(f)==EXPECTED[n]
 out.mkdir(parents=True)
 for n,f in sources.items():
  dest=out/'sd-overlay'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
 (out/'sd-overlay'/MARKER).write_bytes(b'NES-H1-BRINGUP-037\n')
 for src,dest in [('tools/manage_nes_h1_sd.py','manage_nes_h1_sd.py'),('docs/nes-h1-bringup-test.ko.md','READ-ME.ko.md'),('analysis/local-h1-board-034/board-reference-contact.png','reference.png')]:shutil.copy2(ROOT/src,out/dest)
 (out/'results.tsv').write_text('date\tconsole_region\tcart\tcold_warm\tmenu\ttitle_034\tcycles_123\tdefects\treset_menu\treentry\tGBC\trestore\n')
 m={'candidate':CANDIDATE,'firmware_candidate':'035','fpga_candidate':'036','visible_id':'NES H1 034','hardware_executed':False,'electrical_signoff':False,'files':[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()]}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with zipfile.ZipFile(out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(out.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(out))
 print(json.dumps({'package':str(out.with_suffix('.zip')),'sha256':sha(out.with_suffix('.zip')),'files':len(m['files'])},indent=2))
if __name__=='__main__':main()
