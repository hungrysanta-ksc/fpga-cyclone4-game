# SPDX-License-Identifier: MIT
"""Verify053 pin-loaded ROM execution, ownership and immutable checkpoints."""
from pathlib import Path
import ast,json,re,subprocess
from verify_nes_rom_early import read,sha
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert
ROOT=Path(__file__).resolve().parents[1]

def main():
 r=ROOT;raw=r/'analysis/local-rom-boot-053'
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 frozen={}
 for key,name,status,expected in [('052','rom-physical','local-rom-boot-053',261),('051','rom-early','local-rom-physical-052',551),('050','rom-service','local-rom-early-051',223),('049','local-memory','local-rom-service-050',212),('048','oam-banked','local-local-memory-049',290),('047','ncr1-live','local-oam-banked-048',491),('046','ncr1-encoder','local-ncr1-live-047',107),('045','packet-memory','local-ncr1-encoder-046',121),('044_hardware','h1-hardware-044','local-packet-memory-045',23),('044_build','h1-sampling','local-h1-hardware-044',386)]:
  frozen[key]=manifest('analysis/'+name+'-artifacts.json',r/'analysis'/status/'baseline-status');assert frozen[key]==expected
 meta=read(raw/'result.json');unit=read(raw/'unit/result.json');fit=read(raw/'resource/result.json');run=raw/'live';m=read(run/'result.json')
 assert unit['passed'] and (unit['checks'],unit['read_bytes'],unit['negative_cases'],unit['images'])==(360505,180226,8,2)
 for label in ('unit','resource','live'):
  d=raw/label;mm=read(d/'result.json')
  for n,h in mm['sources'].items():assert sha(d/n)==h,(label,n)
  for n in ('nes_rom_physical.sv','nes_rom_loader.sv','nes_rom_boot.sv'):assert sha(d/n)==sha(r/'src/nes'/n)
 for n in ('rom_boot_tb.sv','rom_boot_model.sv'):assert sha(raw/'unit'/n)==sha(r/'tests/nes-functional'/n)
 log=(raw/'unit/simulation.log').read_text();assert 'PASS BOOT checks=360505 read_bytes=180226 negative_cases=8 images=2' in log and 'Errors: 0, Warnings: 0' in log
 assert '** Fatal: BOOT check360492' in (raw/'unit-failed/simulation.log').read_text()
 assert "Undefined variable: 'run_enable'" in (raw/'compile-failed/vlog.log').read_text()
 assert m['passed'] and m['driver_sha256']==fit['driver_sha256']==sha(r/'tools/nes_rom_boot.py')
 ref=r/'analysis/local-rom-physical-052/live';rm=read(ref/'result.json')
 for n,h in rm['sources'].items():
  if n not in ('ncr1_live_tb.sv','rom_backend_model.sv','nes_rom_physical.sv'):assert m['sources'][n]==h,n
 assert sha(run/'rom_backend_model.sv')==sha(r/'tests/nes-functional/rom_boot_model.sv')
 assert '$readmemh' not in (run/'rom_backend_model.sv').read_text()
 assert not re.search(r'memory\.(?:prg|chr)\[[^\]]+\]\s*=(?!=)',(run/'ncr1_live_tb.sv').read_text())
 requests=responses=0;offsets={};loaded={}
 for case,length in [('banks32',98304),('fine_x',81920)]:
  c=run/case;before=ref/case;log=(c/'simulation.log').read_text()
  assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  assert f'BOOT bytes={length} pin_writes={length} run=1' in log;loaded[case]=length
  q=int(re.search(r'ROM SERVICE requests=(\d+)',log)[1]);v=re.search(r'PHYSICAL responses=(\d+) latency=(\d+)..(\d+)',log)
  assert (int(v[2]),int(v[3]))==(4,4) and q-int(v[1]) in (0,1);requests+=q;responses+=int(v[1])
  atlas=convert(bytes(int(v,16) for v in (c/'chr.hex').read_text().split())).ljust(32768,b'\0')
  offsets[case]=[]
  for i in range(1,5):
   packet=(c/f'packet-{i}.bin').read_bytes();old=(before/f'packet-{i}.bin').read_bytes();pix=bytes(int(v,16) for v in (c/f'frame-{i}.hex').read_text().split())
   assert packet[:12]+packet[16:]==old[:12]+old[16:]
   offsets[case].append(int.from_bytes(packet[12:16],'little')-int.from_bytes(old[12:16],'little'))
   assert (c/f'frame-{i}.hex').read_bytes()==(before/f'frame-{i}.hex').read_bytes() and len(pix)==61440 and decode(packet,atlas)==pix
  assert len(set(offsets[case]))==1
  old_events=[x.split() for x in (before/'live.tsv').read_text().splitlines() if not x.startswith('B ')];new_events=[x.split() for x in (c/'live.tsv').read_text().splitlines() if not x.startswith('B ')];assert len(old_events)==len(new_events)
  for old,new in zip(old_events,new_events):
   pos=4 if old[0]=='E' else 2;assert int(new[pos])-int(old[pos])==offsets[case][0] and old[:pos]+old[pos+1:]==new[:pos]+new[pos+1:]
  for n in ('prg.hex','chr.hex','manifest.json'):assert sha(c/n)==sha(before/n)
 assert offsets==meta['packet_tick_offsets_vs052']
 assert fit['phases']=={'map':0,'fit':0}
 for n,h in m['sources'].items():assert fit['sources'][n]==h,n
 log=(raw/'resource/map.log').read_text();assert not re.search(r'Warning \((?:10036|10240)\)',log)
 assert not any('Warning' in line and ('nes_rom_loader.sv' in line or 'nes_rom_boot.sv' in line) for line in log.splitlines())
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
 count=manifest('analysis/rom-boot-artifacts.json',r) if (r/'analysis/rom-boot-artifacts.json').exists() else 0
 print(json.dumps(dict(candidate=meta['candidate'],unit_checks=unit['checks'],unit_read_bytes=180226,protocol_negative_cases=8,loaded_pin_bytes=loaded,actual_frames=8,exact_pixels=491520,packet_bus_bytes=16064,unchanged_packet_content_except_release_ticks=True,packet_tick_offsets_vs052=offsets,actual_fetch_events=131104,ROM_requests=requests,ROM_responses=responses,read_latency_clocks=4,joint_LE=le,joint_LAB=lab,LAB_remaining=963-lab,joint_M9K=m9k,registers=regs,frozen_entries=frozen,protected_GBC_hashes=len(gbc),hardware_baseline='044 unchanged',stream_loader_RTL=True,MCU_SPI_loader=False,physical_clock_binding=False,new_hardware_image=False,timing_signoff=False,git_diff_check='PASS',staged_files=0,allowlist='PASS',raw_ignored=len(files),manifest_entries=count),indent=2))
if __name__=='__main__':main()
