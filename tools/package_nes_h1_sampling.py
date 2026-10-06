# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,shutil,zipfile
from manage_nes_h1_sampling_sd import CANDIDATE,EXPECTED,FIRMWARE,FPGA,BASELINE_FW,sha
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();out=a.out.resolve()
 assert not out.exists() and not out.with_suffix('.zip').exists()
 raw=ROOT/'analysis/local-h1-sampling-044'
 assert json.loads((raw/'rtl/result.json').read_text())['passed']
 # Preserve raw X/notifier failure; bounded binary models are a DIFFERENT experiment.
 assert not json.loads((raw/'gate-sdf/result.json').read_text())['payload_match']
 for mode in ('old','new','mixed'):
  model=json.loads((raw/('resolved-'+mode)/'result.json').read_text())
  assert model['payload_match'] and model['payload_bytes']==512 and model['resolution_events']>0
  assert model['timing_notifiers_enabled'] and not model['timing_pass']
 assert json.loads((raw/'gate-control/result.json').read_text())['payload_match']
 assert len(json.loads((raw/'host/result.json').read_text())['cases'])==15
 fw=raw/'arm/firmware.stm';assert sha(fw)==EXPECTED[FIRMWARE]
 dest=out/'sd-overlay'/FIRMWARE;dest.parent.mkdir(parents=True);shutil.copy2(fw,dest)
 shutil.copy2(raw/'resource/fpga_nh1.bi3',out/'sd-overlay'/FPGA)
 assert sha(out/'sd-overlay'/FPGA)==EXPECTED[FPGA]
 shutil.copy2(ROOT/'tools/manage_nes_h1_sampling_sd.py',out/'manage_nes_h1_sampling_sd.py')
 shutil.copy2(ROOT/'docs/nes-h1-sampling-test.ko.md',out/'READ-ME.ko.md')
 shutil.copy2(ROOT/'analysis/local-h1-board-034/board-reference-contact.png',out/'reference-034.png')
 shutil.copy2(ROOT/'analysis/H1-SAMPLING-RESULT.ko.md',out/'VERIFICATION.ko.md')
 m={'candidate':CANDIDATE,'diagnostic_not_root_cause_fix':True,'hardware_executed':False,'electrical_signoff':False,'experiment_scope':'Bounded diagnostic hardware trial; first-stage/ROM SDF violations remain. Not a physical root-cause claim.','raw_SDF':json.loads((raw/'gate-sdf/result.json').read_text()),'bounded_resolution_models':{mode:json.loads((raw/('resolved-'+mode)/'result.json').read_text()) for mode in ('old','new','mixed')},'baseline':{'firmware.stm':BASELINE_FW,'fpga_nh1.bi3':'b6c7d930a8fb618f1a1ae27724faf1b177c3407526601c8b465cb82472e1453f'},'existing_marker':'NES H1 037.nh1','visible_title':'NES H1 034','output_log':'sd2snes/nes-h1-last-044.txt','files':[{'path':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.rglob('*')) if f.is_file()]}
 (out/'manifest.json').write_text(json.dumps(m,indent=2)+'\n')
 with zipfile.ZipFile(out.with_suffix('.zip'),'w',zipfile.ZIP_DEFLATED) as z:
  for f in sorted(out.rglob('*')):
   if f.is_file():z.write(f,f.relative_to(out))
 print(json.dumps({'zip':str(out.with_suffix('.zip')),'sha256':sha(out.with_suffix('.zip'))}))
if __name__=='__main__':main()
