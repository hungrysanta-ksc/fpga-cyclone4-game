# SPDX-License-Identifier: MIT
"""050 shared ROM timing, actual-core regression, protocol checks and frozen history."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
from nes_rom_service import ROM
from nes_ncr1_live import expose
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-rom-service-050'
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 frozen={}
 for key,name,status,expected in [
  ('049','local-memory','local-rom-service-050',212),('048','oam-banked','local-local-memory-049',290),
  ('047','ncr1-live','local-oam-banked-048',491),('046','ncr1-encoder','local-ncr1-live-047',107),
  ('045','packet-memory','local-ncr1-encoder-046',121),('044_hardware','h1-hardware-044','local-packet-memory-045',23),('044_build','h1-sampling','local-h1-hardware-044',386)]:
  frozen[key]=manifest('analysis/'+name+'-artifacts.json',r/'analysis'/status/'baseline-status');assert frozen[key]==expected
 m=read(raw/'result.json');unit=read(raw/'unit/result.json');live=read(raw/'live/result.json');slow=read(raw/'slow/result.json');fit=read(raw/'resource/result.json')
 assert unit['passed'] and live['passed'] and slow['passed'] and fit['phases']=={'map':0,'fit':0}
 assert (unit['checks'],unit['requests'],unit['cache_pairs'],unit['negative_cases'])==(4148,518,256,6)
 assert live['delay_cycles']==1 and slow['delay_cycles']==2
 for label,x in [('unit',unit),('live',live),('slow',slow),('resource',fit)]:
  for n,h in x['sources'].items():assert sha(raw/label/n)==h,(label,n)
  assert sha(raw/label/'nes_rom_service.sv')==sha(r/'src/nes/nes_rom_service.sv')
 assert sha(raw/'unit/rom_service_tb.sv')==sha(r/'tests/nes-functional/rom_service_tb.sv')
 assert fit['driver_sha256']==live['driver_sha256']==slow['driver_sha256']==sha(r/'tools/nes_rom_service.py')
 for n,h in live['sources'].items():assert fit['sources'][n]==slow['sources'][n]==h,n
 assert sha(raw/'live/rom_backend_model.sv')==sha(r/'tests/nes-functional/rom_backend_model.sv')
 previous=r/'analysis/local-local-memory-049/live'
 old=read(previous/'result.json')['sources']
 for n,h in old.items():
  if n not in ('rtl/nes.v','nes_probe.sv','ncr1_live_tb.sv'):assert live['sources'][n]==h,n
 expected=expose((previous/'rtl/nes.v').read_text(),'NES','output wire rom_cpu_sample','assign rom_cpu_sample=(cart_ce || cpu_ce) && mr_int && prg_addr[15] && prg_allow;')
 assert expected==(raw/'live/rtl/nes.v').read_text()
 expected=expose((previous/'nes_probe.sv').read_text(),'nes_probe','output wire rom_cpu_sample').replace('NES core(','NES core(\n.rom_cpu_sample(rom_cpu_sample),')
 assert expected==(raw/'live/nes_probe.sv').read_text()
 assert 'PASS ROM SERVICE checks=4148 requests=518 cache_pairs=256 negative_cases=6' in (raw/'unit/simulation.log').read_text()
 assert 'Errors: 0, Warnings: 0' in (raw/'unit/simulation.log').read_text()
 pixels=bus_bytes=fetches=requests=0
 for case,want in [('banks32',312303),('fine_x',312315)]:
  c=raw/'live'/case;ref=previous/case
  log=(c/'simulation.log').read_text();assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  assert int(re.search(r'ROM SERVICE requests=(\d+)',log)[1])==want;requests+=want
  assert (c/'live.tsv').read_bytes()==(ref/'live.tsv').read_bytes()
  rows=[v.split() for v in (c/'live.tsv').read_text().splitlines()];bus=bytes(int(v[2]) for v in rows if v[0]=='B');assert len(bus)==8032
  atlas=convert(bytes(int(v,16) for v in (c/'chr.hex').read_text().split())).ljust(32768,b'\0')
  for i in range(1,5):
   packet=(c/f'packet-{i}.bin').read_bytes();assert packet==bus[(i-1)*2008:i*2008]==(ref/f'packet-{i}.bin').read_bytes()
   assert (c/f'frame-{i}.hex').read_bytes()==(ref/f'frame-{i}.hex').read_bytes()
   pix=bytes(int(v,16) for v in (c/f'frame-{i}.hex').read_text().split());assert len(pix)==61440 and decode(packet,atlas)==pix
   pixels+=len(pix);bus_bytes+=len(packet)
  fetches+=sum(v[0]=='E' for v in rows)
  for n in ('prg.hex','chr.hex','manifest.json'):assert sha(c/n)==sha(ref/n)
  log=(raw/'slow'/case/'simulation.log').read_text();assert 'ROM DEADLINE/PROTOCOL error=2 tick=852270' in log and '** Fatal:' in log and 'PASS LIVE NES' not in log
  x=next(x for x in slow['cases'] if x['case']==case);assert x['expected_deadline_failure'] and (x['error'],x['tick'])==(2,852270)
 assert (pixels,bus_bytes,fetches,requests)==(491520,16064,131104,624618)
 report=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace');summary=(raw/'resource/output_files/live.fit.summary').read_text()
 assert 'Total logic elements : 13,538 /' in summary and 'Total registers : 4895' in summary and 'Total memory bits : 182,922 /' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',report)[1])==928 and re.search(r'; M9Ks\s*; 26 /',report)
 assert 'Total virtual pins : 282' in summary and not re.search(r'Warning \((?:10036|10240)\)',(raw/'resource/map.log').read_text())
 joint=(raw/'resource/nes_live_joint.sv').read_text();tb=(raw/'live/ncr1_live_tb.sv').read_text()
 assert ROM in joint and ROM in tb and 'out_rom_fault=rom_fault' in joint
 assert 'rom_backend_model backend' in tb and 'rom_backend_model backend' not in joint
 assert not any(m[k] for k in ('new_hardware_image','hardware_executed','timing_signoff','physical_memory_controller','CDC_implemented'))
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
 count=manifest('analysis/rom-service-artifacts.json',r) if (r/'analysis/rom-service-artifacts.json').exists() else 0
 print(json.dumps(dict(candidate=m['candidate'],unit_checks=4148,protocol_negative_cases=6,actual_core_frames=8,shared_ROM_requests=requests,unchanged_pixels=pixels,exact_bus_bytes=bus_bytes,exact_live_trace=True,actual_BG_fetches=fetches,backend_accept_to_response_clocks=1,late_backend_clocks=2,late_backend_expected_failures=2,late_error_code=2,joint_LE=13538,joint_LAB=928,LAB_remaining=35,joint_M9K=26,registers=4895,frozen_entries=frozen,protected_GBC_hashes=len(gbc),hardware_baseline='044 unchanged',new_hardware_image=False,physical_memory_controller=False,CDC_implemented=False,timing_signoff=False,git_diff_check='PASS',staged_files=0,allowlist='PASS',raw_ignored=len(files),manifest_entries=count),indent=2))
if __name__=='__main__':main()
