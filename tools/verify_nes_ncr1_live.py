# SPDX-License-Identifier: MIT
"""047 live-core pixels/packets, area evidence and frozen044..046 integrity."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from nes_ncr1_live import ROOT,FILES
from nes_h1_sampling import frontend,transport
from build_nes_chr_residency import decode
from build_nes_trace_replay import convert

def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-ncr1-live-047';m=read(raw/'result.json');live=read(raw/'rtl/result.json');res=read(raw/'resource/result.json');unit=read(raw/'tap-checks/result.json')
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 assert manifest('analysis/ncr1-encoder-artifacts.json',raw/'baseline-status')==107
 assert manifest('analysis/packet-memory-artifacts.json',r/'analysis/local-ncr1-encoder-046/baseline-status')==121
 assert manifest('analysis/h1-hardware-044-artifacts.json',r/'analysis/local-packet-memory-045/baseline-status')==23
 assert manifest('analysis/h1-sampling-artifacts.json',r/'analysis/local-h1-hardware-044/baseline-status')==386
 assert live['passed'] and unit['passed'] and unit['tap_checks']==20 and res['phases']=={'map':0,'fit':0}
 for folder,x in [('rtl',live),('resource',res)]:
  for n,h in x['sources'].items():assert sha(raw/folder/n)==h,(folder,n)
 for n in live['sources']:
  assert live['sources'][n]==res['sources'][n],n
 for n in FILES:
  p=raw/'rtl'/(n+'.sv')
  if n not in ('nes_snes_frontend','nes_transport'):assert sha(p)==sha(r/'src/nes'/p.name)
 assert (raw/'rtl/nes_snes_frontend.sv').read_text()==frontend() and (raw/'rtl/nes_transport.sv').read_text()==transport()
 assert sha(raw/'rtl/ncr1_live_tb.sv')==sha(r/'tests/nes-functional/ncr1_live_tb.sv')
 assert sha(raw/'tap-checks/nes_ncr1_ppu_tap.sv')==sha(r/'src/nes/nes_ncr1_ppu_tap.sv')==unit['source_sha256']
 assert sha(raw/'tap-checks/ncr1_tap_tb.sv')==sha(r/'tests/nes-functional/ncr1_tap_tb.sv')==unit['testbench_sha256']
 for case in ('banks32','fine_x'):
  c=raw/'rtl'/case;info=next(v for v in live['cases'] if v['case']==case);assert info['passed'] and info['bus_bytes']==8032 and info['fetches']==65552 and info['raw_attributes']==[0,1,2,3]
  for n in ('prg.hex','chr.hex','manifest.json'):assert sha(c/n)==sha(r/f'analysis/local-video-workloads-021/{case}/build'/n)
  chrdata=bytes(int(v,16) for v in (c/'chr.hex').read_text().split());atlas=convert(chrdata).ljust(32768,b'\0')
  rows=[v.split() for v in (c/'live.tsv').read_text().splitlines()]
  bus=bytes(int(v[2]) for v in rows if v[0]=='B');assert len(bus)==8032
  for e in info['frames']:
   f=e['frame'];packet=(c/f'packet-{f}.bin').read_bytes();assert packet==bus[(f-1)*2008:f*2008] and sha(c/f'packet-{f}.bin')==e['packet_sha256']
   pixels=bytes(int(v,16) for v in (c/f'frame-{f}.hex').read_text().split());assert len(pixels)==61440 and decode(packet,atlas)==pixels and sha(c/f'frame-{f}.hex')==e['pixel_sha256']
   assert packet[5]==f and packet[6]==(case=='fine_x')
   events=[v for v in rows if v[0]=='E' and int(v[1])==f];assert len(events)==16388
   useful=[v for v in events if (0<=int(v[2])<240 and int(v[3])<=247) or (-1<=int(v[2])<239 and int(v[3])>=321)]
   assert len(useful)==15840 and int(useful[-1][4])==int.from_bytes(packet[12:16],'little')
   end=next(int(v[2]) for v in rows if v[:2]==['F',str(f)]);desc=next(int(v[2]) for v in rows if v[:2]==['D',str(f)]);assert end<=desc
  log=(c/'simulation.log').read_text();assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 log=(raw/'tap-checks/vsim.log').read_text();assert 'PASS TAP CHECKS=20' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 summary=(raw/'resource/output_files/live.fit.summary').read_text();fit=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace')
 assert 'Total logic elements : 14,153 /' in summary and 'Total registers : 4797' in summary and 'Total memory bits : 182,922 /' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',fit)[1])==953 and re.search(r'; M9Ks\s*; 26 /',fit)
 assert 'Total pins : 5 /' in summary and 'Total virtual pins : 237' in summary
 assert 'Warning (276027)' in (raw/'resource/map.log').read_text()
 assert not any(m[k] for k in ('new_hardware_image','hardware_executed','timing_signoff'))
 assert sha(r/'analysis/hardware-readiness.json')==sha(raw/'baseline-status/analysis/hardware-readiness.json')
 assert read(r/'docs/nes-development-plan.json')['hardware_tracks']==read(raw/'baseline-status/docs/nes-development-plan.json')['hardware_tracks']
 assert [v for v in read(r/'cores/registry.json')['cores'] if v['id']!='nes']==[v for v in read(raw/'baseline-status/cores/registry.json')['cores'] if v['id']!='nes']
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
 count=manifest('analysis/ncr1-live-artifacts.json',r) if (r/'analysis/ncr1-live-artifacts.json').exists() else 0
 print(json.dumps({'candidate':m['candidate'],'actual_core_frames':8,'actual_core_BG_fetches':131104,'exact_bus_bytes':16064,'decoded_pixels_matching_actual_PPU':491520,'tap_checks':20,'joint_LE':14153,'joint_LAB':953,'LAB_capacity':963,'joint_M9K':26,'frozen046_entries':107,'frozen045_entries':121,'frozen044_hardware_entries':23,'frozen044_build_entries':386,'protected_GBC_hashes':len(gbc),'hardware_baseline':'044 unchanged','new_hardware_image':False,'timing_signoff':False,'git_diff_check':'PASS','staged_files':0,'allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
