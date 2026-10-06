# SPDX-License-Identifier: MIT
from pathlib import Path
import ast,hashlib,json,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-h1-timing-042';count=0
 for group in ('sources','status_files','evidence'):
  for e in json.loads((r/'analysis/h1-edge-artifacts.json').read_text())[group]:
   p=(raw/'baseline-status' if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
 assert count==271
 gbc=json.loads((r/'source-manifest.json').read_text())['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256'],e['path']
 x=json.loads((raw/'result.json').read_text())
 assert x['hardware']['causal_consistency']=='different_first_error_bits'
 assert x['hardware']['cause_implied_frontend_mask']==2 and x['hardware']['aggregate_first_frontend_mask']==1
 assert x['raw_sdf_result']['payload_bytes']==227 and not x['raw_sdf_result']['payload_match']
 assert x['gate_sdf']['timing_violations']==617 and x['gate_sdf']['SDF_applied']
 assert x['raw_control_result']['payload_bytes']==512 and x['raw_control_result']['payload_match']
 assert x['gate_control']['timing_violations']==0 and not x['gate_control']['SDF_applied']
 assert not x['new_hardware_image'] and not x['hardware_root_cause_proven']
 assert sha(raw/'gate-03/gate_tb.sv')==sha(raw/'gate-05/gate_tb.sv')
 a=(raw/'gate-03/board.vo').read_text();b=(raw/'gate-05/board.vo').read_text()
 assert a.count('initial $sdf_annotate("board_v.sdo");')==1
 assert a.replace('initial $sdf_annotate("board_v.sdo");','// SDF is selected explicitly by this driver.')==b
 assert sha(raw/'gate-03/board_v.sdo')==sha(raw/'gate-05/board_v.sdo')==sha(raw/'gate-export/board_v.sdo')
 assert json.loads((raw/'sdf-triplet-audit.json').read_text())=={'triplets':34652,'different_min_typ_max':0}
 assert json.loads((raw/'consistency-tests.json').read_text())['passed']==3
 for group in ('gate_sdf','gate_control'):
  p=raw/('gate-03' if group=='gate_sdf' else 'gate-05')/'gate.log';assert sha(p)==x[group]['gate_log_sha256']
  assert not re.search(r'\*\* Fatal:',p.read_text())
 for e in json.loads((raw/'input-fit-files.json').read_text()):assert sha(r/'analysis/local-h1-edge-041/resource'/e['path'])==e['sha256']
 q=json.loads((raw/'EDA-qsf-changes.json').read_text());assert sha(raw/'gate-export/input-board.qsf')==q['export_sha256']
 assert (raw/'gate-export/input-board.qsf').read_text().splitlines()==(r/'analysis/local-h1-edge-041/resource/board.qsf').read_text().splitlines()+q['added_only']
 before=json.loads((raw/'baseline-status/analysis/hardware-readiness.json').read_text());after=json.loads((r/'analysis/hardware-readiness.json').read_text())
 assert {k:v for k,v in before.items() if k!='H1'}=={k:v for k,v in after.items() if k!='H1'}
 assert after['H1']['last_hardware_observation']['candidate']=='NES-H1-EDGE-041'
 assert not after['H1']['package_ready'] and not after['H1']['hardware_verified']
 assert json.loads((r/'docs/nes-development-plan.json').read_text())['hardware_tracks']['H1']==after['H1']
 before=json.loads((raw/'baseline-status/cores/registry.json').read_text());after=json.loads((r/'cores/registry.json').read_text())
 assert [x for x in before['cores'] if x['id']!='nes']==[x for x in after['cores'] if x['id']!='nes']
 def git(*args,cwd=r,data=None,success=(0,)):
  cp=subprocess.run(['git','-c','safe.directory='+cwd.as_posix(),*args],cwd=cwd,input=data,capture_output=True);assert cp.returncode in success,cp.stderr.decode(errors='replace');return cp.stdout
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 names=json.loads((raw/'public-files.json').read_text())
 for n in names:
  if n.endswith('.py'):ast.parse((r/n).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(names)+'\0').encode(),success=(0,1))
 files=[f.relative_to(r).as_posix() for f in raw.rglob('*') if f.is_file()]
 ignored=git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0');assert set(files)==set(ignored)
 up=r.parent/'nes-upstream-mister';assert git('rev-parse','HEAD',cwd=up).decode().strip()=='49a0a662e244469ca77b2155746a066df704ffae';assert not git('status','--porcelain',cwd=up).strip()
 total=0;manifest=r/'analysis/h1-timing-artifacts.json'
 if manifest.exists():
  m=json.loads(manifest.read_text())
  for group in ('sources','status_files','evidence'):
   for e in m[group]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];total+=1
 print(json.dumps({'previous041_entries':count,'GBC_hashes':len(gbc),'hardware_telemetry_consistency':'FAIL preserved','SDF_payload':'FAIL at byte227 preserved','SDF_timing_errors':617,'unannotated_control':'PASS512bytes','control_errors':0,'same_netlist_connectivity_and_TB':True,'new_hardware_image':False,'protected_GBC_nonNES_H0':'unchanged','upstream_pin_clean':True,'staged_files':0,'git_diff_check':'PASS','public_allowlist':'PASS','raw_ignored':len(files),'manifest_entries':total},indent=2))
if __name__=='__main__':main()
