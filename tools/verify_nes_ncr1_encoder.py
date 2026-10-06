# SPDX-License-Identifier: MIT
"""Verify046 streaming evidence and frozen045/044 baselines."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from nes_h1_sampling import frontend,transport
from build_nes_trace_replay import palette
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-ncr1-encoder-046';x=read(raw/'result.json')
 def manifest(name,status_root):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status_root if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 assert manifest('analysis/packet-memory-artifacts.json',raw/'baseline-status')==121
 assert manifest('analysis/h1-hardware-044-artifacts.json',r/'analysis/local-packet-memory-045/baseline-status')==23
 assert manifest('analysis/h1-sampling-artifacts.json',r/'analysis/local-h1-hardware-044/baseline-status')==386
 rtl=read(raw/'rtl/result.json');gate=read(raw/'gate/result.json');res=read(raw/'resource/result.json')
 assert (rtl,gate,res)==(x['rtl'],x['gate'],x['resource_fit']) and rtl['passed'] and gate['passed']
 assert (rtl['checks'],rtl['event_count'],rtl['exact_bus_bytes'])==(16,131104,18072)
 assert (gate['cases'],gate['exact_bus_bytes'])==(3,6024) and res['phases']=={'map':0,'fit':0}
 for n,h in rtl['sources'].items():
  assert sha(raw/'rtl'/n)==h
  if n not in ('nes_snes_frontend.sv','nes_transport.sv'):assert sha(r/'src/nes'/n)==h
 assert (raw/'rtl/nes_snes_frontend.sv').read_text()==frontend() and (raw/'rtl/nes_transport.sv').read_text()==transport()
 src=r/'src/nes/nes_ncr1_encoder.sv'
 assert sha(src)==sha(raw/'resource'/src.name)==res['source_sha256']
 template=(r/'tests/nes-functional/ncr1_encoder_tb.sv').read_text().replace('@PALETTE@',f'{int.from_bytes(palette(),"little"):016x}')
 assert (raw/'rtl/ncr1_encoder_tb.sv').read_text()==template
 assert sha(raw/'rtl/ncr1_encoder_tb.sv')==rtl['testbench_sha256']
 assert sha(raw/'resource/gate/producer.vo')==sha(raw/'gate/encoder.vo')==gate['netlist_sha256']
 assert '$sdf_annotate' not in (raw/'gate/encoder.vo').read_text()
 for n in ('nes_packet_memory_producer.sv','nes_packet_queue_ram.sv','nes_packet_cdc_ram.sv','nes_host_stage.sv','nes_transport.sv','nes_snes_frontend.sv'):
  assert sha(raw/'rtl'/n)==sha(raw/'gate'/n)
 data=b'';seen=set()
 for e in rtl['inputs']:
  p=r/e['packet'];assert sha(p)==e['packet_sha256'];data+=p.read_bytes();assert e['events']==16388 and e['first_tick']<e['release_tick']<e['last_tick']
  if e['trace'] not in seen:assert sha(r/e['trace'])==e['trace_sha256'];seen.add(e['trace'])
 assert len(data)==16064 and len((raw/'rtl/events.hex').read_text().splitlines())==131104
 for label,marker,expected in [('rtl','PASS NCR1 ENCODER checks=16 bytes=18072',data+data[:2008]),('gate','PASS MAPPED NCR1 checks=3 bytes=6024',data[:4016]+data[8032:10040])]:
  log=(raw/label/('run.log' if label=='rtl' else 'gate.log')).read_text();assert marker in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  rows=[v.split() for v in (raw/label/'encoder-trace.tsv').read_text().splitlines()]
  actual=bytes(int(v[3]) for v in rows if v[0]=='B');assert actual==expected
  ends={}
  for v in rows:
   if v[0]=='F':ends[int(v[2]),int(v[3])]=int(v[1])
   if v[0]=='D':assert (int(v[2]),int(v[3])) in ends and int(v[1])>=ends[int(v[2]),int(v[3])] and int(v[4])>=int(v[3])
 logs=(raw/'resource/map.log').read_text()+(raw/'resource/fit.log').read_text()
 assert not any('('+v+')' in logs for v in ('10036','10240','335093','332060'))
 assert 'Warning (276027)' in logs
 assert 'vopt-13162' in (raw/'gate/gate.log').read_text()
 summary=(raw/'resource/output_files/producer.fit.summary').read_text();fit=(raw/'resource/output_files/producer.fit.rpt').read_text(errors='replace')
 assert 'Total logic elements : 672 /' in summary and 'Total registers : 292' in summary and 'Total memory bits : 10,890 /' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',fit)[1])==118 and re.search(r'; M9Ks\s*; 2 /',fit)
 assert re.search(r'; M9Ks\s*; 4 /',(raw/'resource-before-sharing/output_files/producer.fit.rpt').read_text(errors='replace'))
 assert not any(x[k] for k in ('new_hardware_image','hardware_executed','electrical_signoff'))
 assert sha(r/'analysis/hardware-readiness.json')==sha(raw/'baseline-status/analysis/hardware-readiness.json')
 old=read(raw/'baseline-status/docs/nes-development-plan.json');plan=read(r/'docs/nes-development-plan.json')
 assert plan['hardware_tracks']==old['hardware_tracks'] and plan['gates']==old['gates'] and plan['technical_candidate']==x['candidate']
 before=read(raw/'baseline-status/cores/registry.json');after=read(r/'cores/registry.json')
 assert [v for v in before['cores'] if v['id']!='nes']==[v for v in after['cores'] if v['id']!='nes']
 gbc=read(r/'source-manifest.json')['files']
 for e in gbc:assert sha(r/e['path'])==e['sha256']
 def git(*args,data=None,success=(0,)):
  p=subprocess.run(['git','-c','safe.directory='+r.as_posix(),*args],cwd=r,input=data,capture_output=True);assert p.returncode in success,(p.stdout+p.stderr).decode(errors='replace');return p.stdout
 assert not git('diff','--cached','--name-only').strip()
 assert not git('diff','HEAD','--','src/fpga','src/firmware-overlay','src/renderer','cores/gbc','release','source-manifest.json').strip();git('diff','--check')
 public=read(raw/'public-files.json')
 for n in public:
  if n.endswith('.py'):ast.parse((r/n).read_text())
 assert not git('check-ignore','-z','--stdin',data=('\0'.join(public)+'\0').encode(),success=(0,1))
 files=[p.relative_to(r).as_posix() for p in raw.rglob('*') if p.is_file()]
 assert set(git('check-ignore','-z','--stdin',data=('\0'.join(files)+'\0').encode()).decode().strip('\0').split('\0'))==set(files)
 count=manifest('analysis/ncr1-encoder-artifacts.json',r) if (r/'analysis/ncr1-encoder-artifacts.json').exists() else 0
 print(json.dumps({'candidate':x['candidate'],'historical_timed_fetches':131104,'RTL_cases':16,'RTL_exact_bus_bytes':18072,'fitted_functional_cases':3,'fitted_functional_exact_bus_bytes':6024,'resource':x['resource'],'frozen045_entries':121,'frozen044_hardware_entries':23,'frozen044_build_entries':386,'protected_GBC_hashes':len(gbc),'hardware_baseline':'044 unchanged','new_hardware_image':False,'live_PPU_tap':'not connected','timing_signoff':False,'git_diff_check':'PASS','staged_files':0,'allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
