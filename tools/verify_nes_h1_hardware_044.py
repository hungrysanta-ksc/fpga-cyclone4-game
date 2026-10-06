# SPDX-License-Identifier: MIT
"""Verify the044 hardware observation without changing the frozen build checkpoint."""
from pathlib import Path
import ast,hashlib,json,subprocess
from decode_nes_h1_sampling import decode
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 r=ROOT;raw=r/'analysis/local-h1-hardware-044'
 def git(*args,data=None,success=(0,)):
  cp=subprocess.run(['git','-c','safe.directory='+r.as_posix(),*args],cwd=r,input=data,capture_output=True)
  assert cp.returncode in success,(cp.stdout+cp.stderr).decode(errors='replace');return cp.stdout
 prior=0
 for group in ('sources','status_files','evidence'):
  for e in read(r/'analysis/h1-sampling-artifacts.json')[group]:
   p=(raw/'baseline-status' if group=='status_files' else r)/e['path']
   assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];prior+=1
 assert prior==386
 obs=read(raw/'observation.json');d=decode((raw/'user-044.txt').read_text(encoding='utf-8-sig'))
 assert sha(raw/'user-044.txt')==obs['log_sha256']=='4ef6d67bf607714c6d9e6ec71cb6db5b91941fa57661579387fc278a269adf97'
 assert d==read(raw/'decoded.json')==obs['decoded']
 assert d['candidate']==obs['candidate']=='NES-H1-SAMPLING-044'
 assert d['confirmation']=={'identity':165,'protocol':68,'status':3}
 assert d['exit_reason']=='RESET_ASSERTED' and d['base_restored'] and not d['aggregate_fault']
 assert d['snapshot_trusted'] and not d['snapshot_valid'] and not d['frontend_capture_valid']
 assert d['elapsed_ms_including_configuration']==19540 and d['polls']==17463
 assert obs['start_result']==obs['stop_result']==0 and obs['epoch']==1
 assert obs['hardware_verified'] and not obs['FPGA_hash_verified'] and not obs['electrical_signoff'] and not obs['root_cause_proven']
 before=read(raw/'baseline-status/analysis/hardware-readiness.json');after=read(r/'analysis/hardware-readiness.json');h=after['H1'];old=before['H1']
 assert {k:v for k,v in before.items() if k!='H1'}=={k:v for k,v in after.items() if k!='H1'}
 assert h['last_hardware_observation']==obs and h['previous_hardware_observations']==[old['last_hardware_observation']]
 assert h['candidate']==obs['candidate'] and h['hardware_verified'] and not h['electrical_signoff']
 assert h['firmware']['sha256']==old['next_hardware_trial']['firmware']['sha256'] and h['fpga_image']['sha256']==old['next_hardware_trial']['fpga']['sha256']
 assert h['zip_sha256']==old['zip_sha256']==sha(r/h['package'])
 assert h['open_electrical_items']==old['open_electrical_items'] and h['previous_internal_build']==old['previous_internal_build']
 plan=read(r/'docs/nes-development-plan.json');assert plan['hardware_tracks']['H1']==h and plan['last_h1_candidate']==obs['candidate']
 oldplan=read(raw/'baseline-status/docs/nes-development-plan.json')
 for gate in oldplan['gates']:
  if gate['id']!='R2':assert gate==next(v for v in plan['gates'] if v['id']==gate['id'])
 before=read(raw/'baseline-status/cores/registry.json');after=read(r/'cores/registry.json')
 assert [v for v in before['cores'] if v['id']!='nes']==[v for v in after['cores'] if v['id']!='nes']
 gbc=read(r/'source-manifest.json')['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256'],e['path']
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 public=read(raw/'public-files.json')
 for name in public:
  if name.endswith('.py'):ast.parse((r/name).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(public)+'\0').encode(),success=(0,1))
 files=[p.relative_to(r).as_posix() for p in raw.rglob('*') if p.is_file()]
 assert set(git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0'))==set(files)
 count=0;manifest=r/'analysis/h1-hardware-044-artifacts.json'
 if manifest.exists():
  for group in ('sources','status_files','evidence'):
   for e in read(manifest)[group]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
 print(json.dumps({'candidate':obs['candidate'],'hardware_result':'basic H1 visual cycle and RESET/base recovery PASS','GBC':'gameplay normal per user report','log_protocol':68,'last_status':3,'exit_reason':'RESET_ASSERTED','elapsed_ms_including_configuration':19540,'warm_reentry_endurance':'unconfirmed','electrical_signoff':False,'physical_root_cause_proven':False,'SD_hashes_verified':False,'frozen044_entries':prior,'protected_GBC_hashes':len(gbc),'H0_other_cores':'unchanged','distributed044_zip':'unchanged','staged_files':0,'git_diff_check':'PASS','public_allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
