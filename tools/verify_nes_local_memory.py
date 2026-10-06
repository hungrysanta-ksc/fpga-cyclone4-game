# SPDX-License-Identifier: MIT
"""049 common local RAM, actual pixels, startup policy and frozen evidence integrity."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-local-memory-049'
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 frozen={}
 for key,name,status,expected in [
  ('048','oam-banked','local-local-memory-049',290),('047','ncr1-live','local-oam-banked-048',491),
  ('046','ncr1-encoder','local-ncr1-live-047',107),('045','packet-memory','local-ncr1-encoder-046',121),
  ('044_hardware','h1-hardware-044','local-packet-memory-045',23),('044_build','h1-sampling','local-h1-hardware-044',386)]:
  frozen[key]=manifest('analysis/'+name+'-artifacts.json',r/'analysis'/status/'baseline-status');assert frozen[key]==expected
 m=read(raw/'result.json');unit=read(raw/'unit/result.json');live=read(raw/'live/result.json');fit=read(raw/'resource/result.json')
 assert unit['passed'] and live['passed'] and fit['phases']=={'map':0,'fit':0}
 assert unit['checks']==153604 and unit['complete_scrubs']==3 and unit['interrupted_scrubs']==1 and unit['bytes']==12288
 for label,x in [('unit',unit),('live',live),('resource',fit)]:
  for n,h in x['sources'].items():assert sha(raw/label/n)==h,(label,n)
  assert sha(raw/label/'nes_local_memory.sv')==sha(r/'src/nes/nes_local_memory.sv')
 assert sha(raw/'unit/local_memory_tb.sv')==sha(r/'tests/nes-functional/local_memory_tb.sv')
 assert fit['driver_sha256']==live['driver_sha256']==sha(r/'tools/nes_local_memory.py')
 for n,h in live['sources'].items():assert fit['sources'][n]==h,n
 assert sha(raw/'live/rtl/ppu.sv')==sha(r/'analysis/local-oam-banked-048/live/rtl/ppu.sv')
 assert 'PASS LOCAL MEMORY checks=153604' in (raw/'unit/simulation.log').read_text()
 assert 'Errors: 0, Warnings: 0' in (raw/'unit/simulation.log').read_text()
 pixels=bus_bytes=fetches=0;offsets={}
 for case in ('banks32','fine_x'):
  c=raw/'live'/case;ref=r/'analysis/local-oam-banked-048/live'/case
  log=(c/'simulation.log').read_text();assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log
  assert not re.search(r'\*\* (?:Fatal|Error):',log)
  rows=[s.split() for s in (c/'live.tsv').read_text().splitlines()];before=[s.split() for s in (ref/'live.tsv').read_text().splitlines()]
  bus=bytes(int(v[2]) for v in rows if v[0]=='B');assert len(bus)==8032
  atlas=convert(bytes(int(v,16) for v in (c/'chr.hex').read_text().split())).ljust(32768,b'\0')
  offsets[case]=[]
  for i in range(1,5):
   a=(ref/f'packet-{i}.bin').read_bytes();b=(c/f'packet-{i}.bin').read_bytes()
   assert b==bus[(i-1)*2008:i*2008] and a[:12]+a[16:]==b[:12]+b[16:]
   offset=int.from_bytes(b[12:16],'little')-int.from_bytes(a[12:16],'little');assert offset==4;offsets[case].append(offset)
   assert (c/f'frame-{i}.hex').read_bytes()==(ref/f'frame-{i}.hex').read_bytes()
   pix=bytes(int(v,16) for v in (c/f'frame-{i}.hex').read_text().split());assert len(pix)==61440 and decode(b,atlas)==pix
   pixels+=len(pix);bus_bytes+=len(b)
  old_events=[v for v in before if v[0]!='B'];new_events=[v for v in rows if v[0]!='B'];assert len(old_events)==len(new_events)
  for a,b in zip(old_events,new_events):
   pos=4 if a[0]=='E' else 2;assert int(b[pos])-int(a[pos])==4
   assert a[:pos]+a[pos+1:]==b[:pos]+b[pos+1:]
  fetches+=sum(v[0]=='E' for v in rows)
  for n in ('prg.hex','chr.hex','manifest.json'):assert sha(c/n)==sha(ref/n)
 assert (pixels,bus_bytes,fetches)==(491520,16064,131104)
 report=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace');summary=(raw/'resource/output_files/live.fit.summary').read_text()
 assert 'Total logic elements : 13,477 /' in summary and 'Total registers : 4811' in summary and 'Total memory bits : 182,922 /' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',report)[1])==920 and re.search(r'; M9Ks\s*; 26 /',report)
 assert not re.search(r'Warning \((?:10036|10240)\)',(raw/'resource/map.log').read_text())
 for p in (raw/'memory-inference').glob('*.tdf'):
  text=p.read_text();assert 'read_during_write_mode_port_a="OLD_DATA"' in text and 'RAM_BLOCK_TYPE="M9K"' in text
 assert len(list((raw/'memory-inference').glob('*.tdf')))==2
 joint=(raw/'resource/nes_live_joint.sv').read_text();tb=(raw/'live/ncr1_live_tb.sv').read_text()
 from nes_local_memory import MEMORY
 assert MEMORY in joint and MEMORY in tb
 assert 'reset=reset_request || !memory_ready' in joint and 'reset=reset_request || !memory_ready' in tb
 assert 'nes_resource_ram #' not in joint and 'ram[0:2047]' not in tb
 assert not any(m[k] for k in ('new_hardware_image','hardware_executed','timing_signoff','physical_memory_controller'))
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
 count=manifest('analysis/local-memory-artifacts.json',r) if (r/'analysis/local-memory-artifacts.json').exists() else 0
 result=dict(candidate=m['candidate'],local_RAM_bytes=12288,reset_scrub_clocks=8192,unit_checks=153604,actual_core_frames=8,unchanged_pixels=pixels,packet_bus_bytes=bus_bytes,actual_BG_fetches=fetches,packet_release_tick_offset_vs048=offsets,joint_LE=13477,joint_LAB=920,LAB_remaining=43,joint_M9K=26,registers=4811,frozen_entries=frozen,protected_GBC_hashes=len(gbc),hardware_baseline='044 unchanged',new_hardware_image=False,physical_memory_controller=False,timing_signoff=False,git_diff_check='PASS',staged_files=0,allowlist='PASS',raw_ignored=len(files),manifest_entries=count)
 print(json.dumps(result,indent=2))
if __name__=='__main__':main()
