# SPDX-License-Identifier: MIT
"""Verify043 implementation, preserved failures, image provenance and protected assets."""
from pathlib import Path
import ast,hashlib,json,re,subprocess,csv
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-h1-qualified-043'
 def read(p):return json.loads(p.read_text())
 previous=0
 for group in ('sources','status_files','evidence'):
  for e in read(r/'analysis/h1-timing-artifacts.json')[group]:
   p=(raw/'baseline-status' if group=='status_files' else r)/e['path']
   assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];previous+=1
 assert previous==95
 gbc=read(r/'source-manifest.json')['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256'],e['path']
 x=read(raw/'result.json');rtl=x['rtl'];resource=x['resource'];rel=rtl['release']
 assert rtl['passed'] and (rel['normal_cases'],rel['real_abort_cases'],rel['stream_bytes'])==(936,504,4608)
 assert rel['shared_event_every_edge'] and rel['uncertain_write_release_cases']==6 and rel['edge_completion_negative_control']=='lost write reproduced'
 assert 'Fatal: write lost/duplicated after uncertainty count=0' in (raw/'rtl/edge-control.log').read_text()
 for name in ('aligned','rd_late','addr_late','sel_late','wr_late','crossed'):
  text=(raw/f'rtl/qualified-{name}.log').read_text()
  assert 'PASS RELEASE good=156 abort=84' in text and 'PASS STREAM bytes=768' in text
  assert not re.search(r'\*\* (?:Fatal|Error):',text)
 for name,marker in [('board','PASS NES H1 BOARD checks=9 rombytes=65536 payloadbytes=8192'),('wave','PASS C SPI WAVE samples=704 verified=328 rows=2952')]:
  text=(raw/f'rtl/{name}.log').read_text();assert marker in text and not re.search(r'\*\* (?:Fatal|Error):',text)
 assert len(x['host']['cases'])==15 and x['host']['samples']==704
 assert sha(raw/'host/waveform.txt')==sha(raw/'rtl/waveform.txt')==rtl['waveform_sha256']
 from nes_h1_qualified import frontend,boundary,source,session
 assert (raw/'rtl/nes_snes_frontend.sv').read_text()==(raw/'resource/nes_snes_frontend.sv').read_text()==frontend()
 assert sha(raw/'rtl/nes_snes_frontend.sv')==rtl['frontend_sha256']==resource['compiled_frontend_sha256']
 assert (raw/'rtl/nes_h1_board_bus.sv').read_text()==(raw/'resource/nes_h1_board_bus.sv').read_text()==boundary()
 assert (raw/'arm/nes_h1_stm32.c').read_text()==source() and (raw/'arm/nes_h1_session.c').read_text()==session()
 assert sha(raw/'arm/firmware.stm')==x['firmware']['sha256'] and (raw/'arm/firmware.stm').stat().st_size==169056
 assert x['firmware']['warnings']==0
 assert resource['phases']==dict.fromkeys(('map','fit','sta','asm'),0)
 assert sha(raw/'resource/fpga_nh1.bi3')==resource['bi3_sha256']==x['decoder']['bi3_sha256']
 assert sha(raw/'resource/output_files/board.rbf')==resource['rbf_sha256']
 assert x['decoder']['passed'] and x['decoder']['bytes']==223160
 assert 'PASS MCU rle_file_getc exact bytes=223160 and EOF' in (raw/'decoder/decode.log').read_text()
 assert read(raw/'decoder-tests.json')['passed']==6
 rows=list(csv.DictReader((raw/'resource/input-audit/direct-paths.tsv').read_text().splitlines(),delimiter='\t'))
 for item in rows:
  if item['group'] in ('sticky','capture','event','context'):assert int(item['registers'])>0 and int(item['paths'])==0,item
 assert min(x['internal_slack_min_ns'].values())>0
 assert x['raw_sdf_result']['payload_bytes']==91 and not x['raw_sdf_result']['payload_match'] and x['raw_sdf_result']['timing_errors']==612
 assert x['raw_control_result']['payload_bytes']==512 and x['raw_control_result']['payload_match'] and x['raw_control_result']['timing_errors']==0
 assert x['gate_sdf']['timing_process_groups']=={'ROM_address_sampling':575,'bundle_first_stage':33,'control_first_stage':4}
 for name,mode in [('gate-sdf',True),('gate-control',False)]:
  text=(raw/name/'gate.log').read_text();assert ('SDF Backannotation Successfully Completed' in text)==mode and not re.search(r'\*\* Fatal:',text)
  original=(raw/name/'board.original.vo').read_text();derived=(raw/name/'board.vo').read_text()
  assert original.count('initial $sdf_annotate("board_v.sdo");')==1
  assert original.replace('initial $sdf_annotate("board_v.sdo");','// SDF is selected explicitly by this driver.')==derived
 for name in ('gate_tb.sv','board.vo','board_v.sdo'):
  assert sha(raw/'gate-sdf'/name)==sha(raw/'gate-control'/name),name
 assert not x['package_ready'] and not x['hardware_executed'] and not x['hardware_root_cause_proven']
 before=read(raw/'baseline-status/analysis/hardware-readiness.json');after=read(r/'analysis/hardware-readiness.json')
 assert {k:v for k,v in before.items() if k!='H1'}=={k:v for k,v in after.items() if k!='H1'}
 for key in ('candidate','firmware','fpga_image','last_hardware_observation'):assert after['H1'][key]==before['H1'][key],key
 assert after['H1']['investigation']==x['candidate'] and not after['H1']['package_ready']
 assert after['H1']==read(r/'docs/nes-development-plan.json')['hardware_tracks']['H1']
 before=read(raw/'baseline-status/cores/registry.json');after=read(r/'cores/registry.json')
 assert [c for c in before['cores'] if c['id']!='nes']==[c for c in after['cores'] if c['id']!='nes']
 def git(*args,cwd=r,data=None,success=(0,)):
  cp=subprocess.run(['git','-c','safe.directory='+cwd.as_posix(),*args],cwd=cwd,input=data,capture_output=True)
  assert cp.returncode in success,cp.stderr.decode(errors='replace');return cp.stdout
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 public=read(raw/'public-files.json')
 for name in public:
  if name.endswith('.py'):ast.parse((r/name).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(public)+'\0').encode(),success=(0,1))
 files=[p.relative_to(r).as_posix() for p in raw.rglob('*') if p.is_file()]
 assert set(git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0'))==set(files)
 up=r.parent/'nes-upstream-mister';assert git('rev-parse','HEAD',cwd=up).decode().strip()=='49a0a662e244469ca77b2155746a066df704ffae' and not git('status','--porcelain',cwd=up).strip()
 count=0;m=r/'analysis/h1-qualified-artifacts.json'
 if m.exists():
  for group in ('sources','status_files','evidence'):
   for e in read(m)[group]:
    p=r/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
 print(json.dumps({'candidate':x['candidate'],'previous042_entries':previous,'GBC_hashes':len(gbc),'normal_cases':936,'real_abort_cases':504,'board_cases':9,'ROM_bytes':65536,'payload_bytes':8192,'host_cases':15,'production_SPI_samples':704,'physical_fit_internal_STA':'PASS only; external IO unconstrained','shared_event_raw_direct_paths':0,'SDF':'FAIL after91bytes/612first-stage-or-ROM violations preserved','unannotated_control':'PASS512bytes','package_ready':False,'hardware_verified':False,'protected_GBC_nonNES_H0':'unchanged','upstream_pin_clean':True,'staged_files':0,'git_diff_check':'PASS','public_allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
