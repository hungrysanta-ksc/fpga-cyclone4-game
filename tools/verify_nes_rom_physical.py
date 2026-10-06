# SPDX-License-Identifier: MIT
"""Verify052 pin/CDC evidence, actual core pixels and immutable earlier checkpoints."""
from pathlib import Path
import ast,json,re,subprocess
from verify_nes_rom_early import read,sha
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
ROOT=Path(__file__).resolve().parents[1]

def main():
 r=ROOT;raw=r/'analysis/local-rom-physical-052'
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 frozen={}
 for key,name,status,expected in [('051','rom-early','local-rom-physical-052',551),('050','rom-service','local-rom-early-051',223),('049','local-memory','local-rom-service-050',212),('048','oam-banked','local-local-memory-049',290),('047','ncr1-live','local-oam-banked-048',491),('046','ncr1-encoder','local-ncr1-live-047',107),('045','packet-memory','local-ncr1-encoder-046',121),('044_hardware','h1-hardware-044','local-packet-memory-045',23),('044_build','h1-sampling','local-h1-hardware-044',386)]:
  frozen[key]=manifest('analysis/'+name+'-artifacts.json',r/'analysis'/status/'baseline-status');assert frozen[key]==expected
 original=(raw/'executed-sources/nes_rom_physical-before-attributes.sv').read_text()
 production=(r/'src/nes/nes_rom_physical.sv').read_text()
 normalized=original.replace('(* async_reg="true" *)','(* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *)').replace('remaining<=READ_CYCLES;',"remaining<=CW'(READ_CYCLES);")
 assert normalized==production
 meta=read(raw/'result.json');unit=read(raw/'unit/result.json');fit=read(raw/'resource/result.json');run=raw/'live';m=read(run/'result.json')
 for label in ('unit-before-attributes','unit','resource-before-attributes','resource','live'):
  d=raw/label;mm=read(d/'result.json')
  for n,h in mm['sources'].items():assert sha(d/n)==h,(label,n)
 assert unit['passed'] and unit['late_memory_expected_failure'] and len(unit['cases'])==16
 assert sha(raw/'unit/nes_rom_physical.sv')==sha(r/'src/nes/nes_rom_physical.sv')
 assert sha(raw/'unit/rom_physical_tb.sv')==sha(r/'tests/nes-functional/rom_physical_tb.sv')
 assert sha(raw/'unit/rom_physical_model.sv')==sha(r/'tests/nes-functional/rom_physical_model.sv')
 for c in unit['cases']:
  assert c['phase_ps'] in range(0,12000,750) and (c['accepted'],c['completed'],c['canceled'],c['min_clocks'],c['max_clocks'])==(538,525,13,4,4)
  log=(raw/'unit'/('phase-'+str(c['phase_ps'])+'.log')).read_text();assert 'PASS PHYSICAL ' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  assert 'Errors: 0, Warnings: 0' in log
 assert len({c['phase_ps'] for c in unit['cases']})==16
 assert '** Fatal: PHYSICAL check' in (raw/'unit/late-memory.log').read_text() and 'gotzz' in (raw/'unit/late-memory.log').read_text()
 assert m['passed'] and m['memory_read_clocks']==3 and m['phase_ps']==3500 and m['driver_sha256']==sha(r/'tools/nes_rom_physical.py')
 assert (run/'nes_rom_physical.sv').read_text()==original
 ref=r/'analysis/local-rom-early-051/live3';rm=read(ref/'result.json')
 for n,h in rm['sources'].items():
  if n not in ('ncr1_live_tb.sv','rom_backend_model.sv'):assert m['sources'][n]==h,n
 assert sha(run/'rom_backend_model.sv')==sha(r/'tests/nes-functional/rom_physical_model.sv')
 requests=responses=0
 for case in ('banks32','fine_x'):
  c=run/case;before=ref/case;log=(c/'simulation.log').read_text()
  assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  q=int(re.search(r'ROM SERVICE requests=(\d+)',log)[1]);v=re.search(r'PHYSICAL responses=(\d+) latency=(\d+)..(\d+)',log)
  assert (int(v[2]),int(v[3]))==(4,4) and q-int(v[1]) in (0,1)
  requests+=q;responses+=int(v[1]);assert (c/'live.tsv').read_bytes()==(before/'live.tsv').read_bytes()
  atlas=convert(bytes(int(v,16) for v in (c/'chr.hex').read_text().split())).ljust(32768,b'\0')
  for i in range(1,5):
   packet=(c/f'packet-{i}.bin').read_bytes();pix=bytes(int(v,16) for v in (c/f'frame-{i}.hex').read_text().split())
   assert packet==(before/f'packet-{i}.bin').read_bytes() and (c/f'frame-{i}.hex').read_bytes()==(before/f'frame-{i}.hex').read_bytes()
   assert len(pix)==61440 and decode(packet,atlas)==pix
  for n in ('prg.hex','chr.hex','manifest.json'):assert sha(c/n)==sha(before/n)
 assert requests==624788
 assert fit['phases']=={'map':0,'fit':0} and fit['driver_sha256']==m['driver_sha256']
 assert sha(raw/'resource/nes_rom_physical.sv')==sha(r/'src/nes/nes_rom_physical.sv')
 for n,h in m['sources'].items():
  if n!='nes_rom_physical.sv':assert fit['sources'][n]==h,n
 log=(raw/'resource/map.log').read_text();assert not re.search(r'Warning \((?:10036|10240)\)',log)
 assert not any('Warning' in line and 'nes_rom_physical.sv' in line for line in log.splitlines())
 report=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace');summary=(raw/'resource/output_files/live.fit.summary').read_text()
 le=int(re.search(r'Total logic elements : ([0-9,]+)',summary)[1].replace(',',''));lab=int(re.search(r'Total LABs:.*?;\s*(\d+)',report)[1]);regs=int(re.search(r'Total registers : (\d+)',summary)[1]);m9k=int(re.search(r'; M9Ks\s*; (\d+) /',report)[1]);assert lab<=963 and m9k==26
 assert (le,lab,regs,m9k)==tuple(meta['resource'][k] for k in ('LE','LAB','registers','M9K'))
 assert sha(r/'analysis/hardware-readiness.json')==sha(raw/'baseline-status/analysis/hardware-readiness.json')
 assert read(r/'docs/nes-development-plan.json')['hardware_tracks']==read(raw/'baseline-status/docs/nes-development-plan.json')['hardware_tracks']
 assert [x for x in read(r/'cores/registry.json')['cores'] if x['id']!='nes']==[x for x in read(raw/'baseline-status/cores/registry.json')['cores'] if x['id']!='nes']
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
 count=manifest('analysis/rom-physical-artifacts.json',r) if (r/'analysis/rom-physical-artifacts.json').exists() else 0
 print(json.dumps(dict(candidate=meta['candidate'],unit_phases=16,unit_checks=sum(c['checks'] for c in unit['cases']),unit_completed_reads=8400,unit_canceled_reads=208,late_memory_expected_failure=True,actual_frames=8,exact_pixels=491520,exact_bus_bytes=16064,exact_live_trace=True,ROM_requests=requests,ROM_responses=responses,request_sample_latency_clocks=4,actual_core_source_note='Pre-annotation cleanup source; exact attribute and explicit constant-width-only transformation verified against production; final production passed full unit matrix and joint fit',joint_LE=le,joint_LAB=lab,LAB_remaining=963-lab,joint_M9K=m9k,registers=regs,frozen_entries=frozen,protected_GBC_hashes=len(gbc),hardware_baseline='044 unchanged',physical_read_controller_RTL=True,CDC_implemented=True,CDC_physical_signoff=False,new_hardware_image=False,timing_signoff=False,git_diff_check='PASS',staged_files=0,allowlist='PASS',raw_ignored=len(files),manifest_entries=count),indent=2))
if __name__=='__main__':main()
