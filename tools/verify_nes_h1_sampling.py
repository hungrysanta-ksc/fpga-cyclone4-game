# SPDX-License-Identifier: MIT
"""Verify044 provenance, retained failures, bounded model scope and hardware package."""
from pathlib import Path
import ast,csv,hashlib,json,re,subprocess,zipfile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
 r=ROOT;raw=r/'analysis/local-h1-sampling-044';x=read(raw/'result.json')
 def git(*args,cwd=r,data=None,success=(0,)):
  cp=subprocess.run(['git','-c','safe.directory='+cwd.as_posix(),*args],cwd=cwd,input=data,capture_output=True)
  assert cp.returncode in success,(cp.stdout+cp.stderr).decode(errors='replace');return cp.stdout
 previous=0
 for group in ('sources','status_files','evidence'):
  for e in read(r/'analysis/h1-qualified-artifacts.json')[group]:
   p=(raw/'baseline-status' if group=='status_files' else r)/e['path']
   assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];previous+=1
 assert previous==300
 gbc=read(r/'source-manifest.json')['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256'],e['path']
 from nes_h1_sampling import frontend,boundary,source,session
 from manage_nes_h1_sampling_sd import payload,EXPECTED
 rtl=x['rtl'];resource=x['resource'];rel=rtl['release']
 assert rtl['passed'] and (rel['normal_cases'],rel['real_abort_cases'],rel['stream_bytes'])==(936,504,4608)
 assert rel['shared_event_every_edge'] and rel['uncertain_write_release_cases']==6
 for name in ('aligned','rd_late','addr_late','sel_late','wr_late','crossed'):
  s=(raw/f'rtl/qualified-{name}.log').read_text();assert 'PASS RELEASE good=156 abort=84' in s and 'PASS STREAM bytes=768' in s and not re.search(r'\*\* (?:Fatal|Error):',s)
 for name,marker in [('board','PASS NES H1 BOARD checks=9 rombytes=65536 payloadbytes=8192'),('wave','PASS C SPI WAVE samples=704 verified=328 rows=2952'),('resolution-run','PASS RESOLUTION binary=576 X_negative_controls=288 independent_delay_cases=96')]:
  s=(raw/f'rtl/{name}.log').read_text();assert marker in s and not re.search(r'\*\* (?:Fatal|Error):',s)
 assert 'Fatal: write lost/duplicated after uncertainty count=0' in (raw/'rtl/edge-control.log').read_text()
 assert len(x['host']['cases'])==15 and sha(raw/'host/waveform.txt')==sha(raw/'rtl/waveform.txt')==rtl['waveform_sha256']
 assert (raw/'rtl/nes_snes_frontend.sv').read_text()==(raw/'resource/nes_snes_frontend.sv').read_text()==frontend()
 assert sha(raw/'rtl/nes_snes_frontend.sv')==rtl['frontend_sha256']==resource['compiled_frontend_sha256']
 assert (raw/'rtl/nes_h1_board_bus.sv').read_text()==(raw/'resource/nes_h1_board_bus.sv').read_text()==boundary()
 assert (raw/'arm/nes_h1_stm32.c').read_text()==source() and (raw/'arm/nes_h1_session.c').read_text()==session()
 assert sha(raw/'arm/firmware.stm')==x['firmware']['sha256'] and x['firmware']['warnings']==0 and x['firmware']['bytes']==169056
 assert resource['phases']==dict.fromkeys(('map','fit','sta','asm'),0)
 assert sha(raw/'resource/fpga_nh1.bi3')==resource['bi3_sha256']==x['decoder']['bi3_sha256']
 assert sha(raw/'resource/output_files/board.rbf')==resource['rbf_sha256'] and x['decoder']['passed'] and x['decoder']['bytes']==214731
 assert 'PASS MCU rle_file_getc exact bytes=214731 and EOF' in (raw/'decoder/decode.log').read_text()
 assert x['predicate_and_decoder']['boolean_identity_4bit_triples']==4096 and x['predicate_and_decoder']['decoder_cases']==4
 rows=list(csv.DictReader((raw/'resource/input-audit/direct-paths.tsv').read_text().splitlines(),delimiter='\t'))
 for row in rows:
  if row['group'] in ('sticky','capture','event','context'):assert int(row['registers'])>0 and int(row['paths'])==0
 assert min(x['internal_slack_min_ns'].values())>0
 assert (x['raw_sdf_result']['payload_bytes'],x['raw_sdf_result']['timing_errors'])==(126,884) and not x['raw_sdf_result']['payload_match']
 assert x['raw_control_result']['payload_match'] and x['raw_control_result']['payload_bytes']==512 and x['raw_control_result']['timing_errors']==0
 nodes={f'addr_meta[{i}]' for i in range(24)}|{f'data_meta[{i}]' for i in range(8)}|{'rd_sync[0]','wr_sync[0]','sel_sync[0]'}
 for mode in ('old','new','mixed'):
  d=raw/('resolved-'+mode);m=read(d/'result.json');assert m==x['resolved'][mode]
  assert m['payload_match'] and m['payload_bytes']==512 and m['resolution_events']==304 and m['timing_errors']==4365 and not m['timing_pass'] and m['timing_notifiers_enabled']
  tb=(d/'gate_tb.sv').read_text();forces=[v for v in tb.splitlines() if re.search(r'\bforce\s',v)]
  assert len(forces)==35 and {v.split('frontend|')[1].split(' ')[0] for v in forces}==nodes
  assert len((d/'resolutions.txt').read_text().splitlines())==304
 for name in ('gate-sdf','gate-control','resolved-old','resolved-new','resolved-mixed'):
  d=raw/name;log=(d/'gate.log').read_text();assert ('SDF Backannotation Successfully Completed' in log)==(name!='gate-control')
  assert not re.search(r'\*\* Fatal:',log)
  original=(d/'board.original.vo').read_text();derived=(d/'board.vo').read_text()
  assert original.count('initial $sdf_annotate("board_v.sdo");')==1
  assert original.replace('initial $sdf_annotate("board_v.sdo");','// SDF is selected explicitly by this driver.')==derived
  for file in ('board.vo','board_v.sdo'):assert sha(d/file)==sha(raw/'gate-sdf'/file)
 assert sha(raw/'gate-sdf/gate_tb.sv')==sha(raw/'gate-control/gate_tb.sv')
 for label,at in [('043','641401000'),('044','654496000')]:
  trace=read(raw/('trace-'+label)/'trace-result.json');assert trace['retained_q_taps_checked'] and trace['first_unknown']['event']['time_ps']==at
 assert read(raw/'sd-test/result.json')['passed']==read(raw/'final-package-test/result.json')['passed']==8
 pkg=raw/'NES-H1-SAMPLING-044';payload(pkg);pm=read(pkg/'manifest.json')
 assert not pm['hardware_executed'] and not pm['electrical_signoff'] and pm['diagnostic_not_root_cause_fix']
 assert pm['raw_SDF']==x['raw_sdf_result'] and pm['bounded_resolution_models']==x['resolved']
 assert sha(r/x['package'])==x['zip_sha256']
 with zipfile.ZipFile(r/x['package']) as z:
  assert z.testzip() is None
  assert set(z.namelist())=={p.relative_to(pkg).as_posix() for p in pkg.rglob('*') if p.is_file()}
  for name in z.namelist():assert z.read(name)==(pkg/name).read_bytes()
 for file,h in EXPECTED.items():assert sha(pkg/'sd-overlay'/file)==h
 assert (pkg/'manage_nes_h1_sampling_sd.py').read_bytes()==(r/'tools/manage_nes_h1_sampling_sd.py').read_bytes()
 assert (pkg/'VERIFICATION.ko.md').read_bytes()==(r/'analysis/H1-SAMPLING-RESULT.ko.md').read_bytes()
 before=read(raw/'baseline-status/analysis/hardware-readiness.json');after=read(r/'analysis/hardware-readiness.json')
 assert {k:v for k,v in before.items() if k!='H1'}=={k:v for k,v in after.items() if k!='H1'}
 for key in ('candidate','firmware','fpga_image','last_hardware_observation'):assert before['H1'][key]==after['H1'][key]
 assert after['H1']['next_hardware_trial']['candidate']==x['candidate'] and after['H1']['package_ready'] and not after['H1']['next_hardware_trial']['hardware_executed']
 assert after['H1']==read(r/'docs/nes-development-plan.json')['hardware_tracks']['H1']
 before=read(raw/'baseline-status/cores/registry.json');after=read(r/'cores/registry.json')
 assert [c for c in before['cores'] if c['id']!='nes']==[c for c in after['cores'] if c['id']!='nes']
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 public=read(raw/'public-files.json')
 for name in public:
  if name.endswith('.py'):ast.parse((r/name).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(public)+'\0').encode(),success=(0,1))
 files=[p.relative_to(r).as_posix() for p in raw.rglob('*') if p.is_file()]
 assert set(git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0'))==set(files)
 up=r.parent/'nes-upstream-mister';assert git('rev-parse','HEAD',cwd=up).decode().strip()=='49a0a662e244469ca77b2155746a066df704ffae' and not git('status','--porcelain',cwd=up).strip()
 count=0;manifest=r/'analysis/h1-sampling-artifacts.json'
 if manifest.exists():
  for group in ('sources','status_files','evidence'):
   for e in read(manifest)[group]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
 assert x['package_ready'] and not any(x[k] for k in ('hardware_executed','hardware_verified','hardware_root_cause_proven','electrical_signoff'))
 print(json.dumps({'candidate':x['candidate'],'previous043_entries':previous,'GBC_hashes':len(gbc),'RTL':'936 normal /504 real abort /576 binary /288 X controls /96 delays PASS','MCU_and_board':'15 host /704 SPI samples /9 board cases PASS','raw_SDF':'FAIL126bytes/884violations preserved','bounded_resolution_models':'old/new/mixed PASS512 each, not timing signoff','installer_cases':8,'final_package_cases':8,'package_ready':True,'hardware_verified':False,'electrical_signoff':False,'protected_GBC_nonNES_H0':'unchanged','upstream_pin_clean':True,'staged_files':0,'git_diff_check':'PASS','public_allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
