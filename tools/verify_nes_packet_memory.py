# SPDX-License-Identifier: MIT
"""Verify045 executed evidence, matched fit source and protected044 baseline."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from nes_h1_sampling import frontend,transport
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-packet-memory-045';x=read(raw/'result.json')
 def check_manifest(name,status_root):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status_root if group=='status_files' else r)/e['path']
    assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 assert check_manifest('analysis/h1-hardware-044-artifacts.json',raw/'baseline-status')==23
 assert check_manifest('analysis/h1-sampling-artifacts.json',r/'analysis/local-h1-hardware-044/baseline-status')==386
 rtl=read(raw/'rtl/result.json');res=read(raw/'resource/result.json')
 assert rtl==x['rtl'] and rtl['passed'] and len(rtl['runs'])==3 and res==x['resource_fit'] and res['phases']=={'map':0,'fit':0}
 src=r/'src/nes/nes_packet_memory_producer.sv'
 assert sha(src)==sha(raw/'rtl'/src.name)==sha(raw/'resource'/src.name)==res['source_sha256']==rtl['sources'][src.name]
 assert sha(r/'tests/nes-functional/packet_memory_tb.sv')==sha(raw/'rtl/packet_memory_tb.sv')==rtl['testbench_sha256']
 for name,h in rtl['sources'].items():
  assert sha(raw/'rtl'/name)==h
  if name not in ('nes_snes_frontend.sv','nes_transport.sv'):assert sha(r/'src/nes'/name)==h
 assert (raw/'rtl/nes_snes_frontend.sv').read_text()==frontend() and (raw/'rtl/nes_transport.sv').read_text()==transport()
 assert sha(raw/'rtl/nes_snes_frontend.sv')==sha(r/'analysis/local-h1-sampling-044/rtl/nes_snes_frontend.sv')
 data=b''
 for e in rtl['inputs']:
  p=r/e['path'];assert sha(p)==e['sha256'] and p.stat().st_size==2008 and e['memory_offset']==len(data);data+=p.read_bytes()
 assert len(data)==16064
 expected=data+data[2008:2016]+data[:8]+data[:3072]+b'\xff'
 total=0
 for label,v in rtl['runs'].items():
  s=(raw/'rtl'/(label+'.log')).read_text();assert 'PASS MEMORY PRODUCER checks=17 bytes=19153' in s and not re.search(r'\*\* (?:Fatal|Error):',s)
  assert v['checks']==17 and len(v['cases'])==17 and v['exact_bytes_verified'] and v['bytes']==19153
  rows=[s.split() for s in (raw/'rtl'/(label+'.tsv')).read_text().splitlines()]
  actual=bytes(int(s[3]) for s in rows if s[0]=='B');assert actual==expected;total+=len(actual)
  # First8 frames: all source reads are strictly sequential, exactly once.
  reads=[s for s in rows if s[0]=='R'];first_epoch=int(reads[0][2]);first=[int(s[4]) for s in reads if int(s[2])==first_epoch]
  assert first==list(range(16064))
  assert int(re.search(r'ACQUIRE retries=(\d+)',s)[1])>0
 assert total==57459
 logs=(raw/'resource/map.log').read_text()+(raw/'resource/fit.log').read_text()
 assert not any('('+n+')' in logs for n in ('10240','335093','332060'))
 assert 'Warning (10240)' in (raw/'resource-before-reset-fix/map.log').read_text()
 assert 'Fatal: read address00006008' in (raw/'rtl-initial-register-test/q46_h12.log').read_text()
 assert 'Fatal: acquire failed' in (raw/'rtl-initial-retry-test/q46_h12.log').read_text()
 summary=(raw/'resource/output_files/producer.fit.summary').read_text();fit=(raw/'resource/output_files/producer.fit.rpt').read_text(errors='replace')
 assert 'Total logic elements : 416 /' in summary and 'Total registers : 155' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',fit)[1])==61
 assert not any(x[k] for k in ('new_hardware_image','hardware_executed','electrical_signoff'))
 assert sha(r/'analysis/hardware-readiness.json')==sha(raw/'baseline-status/analysis/hardware-readiness.json')
 plan=read(r/'docs/nes-development-plan.json');old=read(raw/'baseline-status/docs/nes-development-plan.json')
 assert plan['hardware_tracks']==old['hardware_tracks'] and plan['gates']==old['gates']
 assert plan['technical_candidate']==x['candidate'] and plan['last_h1_candidate']=='NES-H1-SAMPLING-044'
 reg=read(r/'cores/registry.json');oldreg=read(raw/'baseline-status/cores/registry.json')
 assert [c for c in reg['cores'] if c['id']!='nes']==[c for c in oldreg['cores'] if c['id']!='nes']
 gbc=read(r/'source-manifest.json')['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256']
 def git(*args,data=None,success=(0,)):
  p=subprocess.run(['git','-c','safe.directory='+r.as_posix(),*args],cwd=r,input=data,capture_output=True)
  assert p.returncode in success,(p.stdout+p.stderr).decode(errors='replace');return p.stdout
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 public=read(raw/'public-files.json')
 for name in public:
  if name.endswith('.py'):ast.parse((r/name).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(public)+'\0').encode(),success=(0,1))
 files=[p.relative_to(r).as_posix() for p in raw.rglob('*') if p.is_file()]
 assert set(git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0'))==set(files)
 count=check_manifest('analysis/packet-memory-artifacts.json',r) if (r/'analysis/packet-memory-artifacts.json').exists() else 0
 print(json.dumps({'candidate':x['candidate'],'runs':3,'cases_per_run':17,'exact_bus_bytes':total,'historical_packet_bytes':16064,'source_match_RTL_fit':True,'standalone_resource':x['resource'],'044_hardware_manifest_entries':23,'044_build_manifest_entries':386,'protected_GBC_hashes':len(gbc),'hardware_readiness':'044 unchanged','new_hardware_image':False,'live_encoder_physical_memory':'not integrated','staged_files':0,'git_diff_check':'PASS','allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
