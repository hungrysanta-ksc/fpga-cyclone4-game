# SPDX-License-Identifier: MIT
"""048 structural equivalence, unchanged actual pixels and measured joint resource integrity."""
from pathlib import Path
import ast,hashlib,json,re,subprocess
from nes_oam_compact import compact
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 r=ROOT;raw=r/'analysis/local-oam-banked-048';m=read(raw/'result.json');eq=read(raw/'equivalence/result.json');live=read(raw/'live/result.json');fit=read(raw/'resource/result.json');budget=read(raw/'area-budget.json')
 def manifest(name,status):
  count=0
  for group in ('sources','status_files','evidence'):
   for e in read(r/name)[group]:
    p=(status if group=='status_files' else r)/e['path'];assert p.stat().st_size==e['bytes'] and sha(p)==e['sha256'],e['path'];count+=1
  return count
 assert manifest('analysis/ncr1-live-artifacts.json',raw/'baseline-status')==491
 assert manifest('analysis/ncr1-encoder-artifacts.json',r/'analysis/local-ncr1-live-047/baseline-status')==107
 assert manifest('analysis/packet-memory-artifacts.json',r/'analysis/local-ncr1-encoder-046/baseline-status')==121
 assert manifest('analysis/h1-hardware-044-artifacts.json',r/'analysis/local-packet-memory-045/baseline-status')==23
 assert manifest('analysis/h1-sampling-artifacts.json',r/'analysis/local-h1-hardware-044/baseline-status')==386
 assert eq['passed'] and live['passed'] and fit['phases']=={'map':0,'fit':0}
 assert [eq[k] for k in ('cycles','row_copies','cpu_writes','ss_writes','write_collisions')]==[216362,2426,3111,10473,2012]
 assert eq['optimization']==live['optimization']==fit['optimization']=='merged_mutually_exclusive_normal_write_port'
 for label,x in [('equivalence',eq),('live',live),('resource',fit)]:
  for n,h in x['sources'].items():assert sha(raw/label/n)==h,(label,n)
 for n,h in live['sources'].items():assert fit['sources'][n]==h,n
 original=(r/'analysis/local-ncr1-live-047/rtl/rtl/ppu.sv').read_text();changed=compact(original)
 assert (raw/'live/rtl/ppu.sv').read_text()==changed==(raw/'resource/rtl/ppu.sv').read_text()
 old_others=read(r/'analysis/local-ncr1-live-047/rtl/result.json')['sources']
 for n,h in old_others.items():
  if n!='rtl/ppu.sv':assert live['sources'][n]==h,n
 assert sha(raw/'equivalence/oam_banked_tb.sv')==sha(r/'tests/nes-functional/oam_banked_tb.sv')
 module=re.search(r'(?ms)^module OAMEval\(.*?^endmodule',changed)[0].replace('module OAMEval(','module oam_banked(',1)
 assert module in (raw/'equivalence/oam_banked.sv').read_text()
 log=(raw/'equivalence/simulation.log').read_text();assert 'PASS OAM BANKING cycles=216362' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 assert 'Errors: 0, Warnings: 0' in log
 total_pixels=total_bytes=0
 for case in ('banks32','fine_x'):
  c=raw/'live'/case;ref=r/'analysis/local-ncr1-live-047/rtl'/case
  case_result=next(x for x in live['cases'] if x['case']==case);assert case_result['passed'] and case_result['fetches']==65552 and case_result['bus_bytes']==8032
  for n in ('prg.hex','chr.hex','manifest.json','live.tsv'):
   assert (c/n).read_bytes()==(ref/n).read_bytes(),(case,n)
  for i in range(1,5):
   for n in (f'packet-{i}.bin',f'frame-{i}.hex'):assert (c/n).read_bytes()==(ref/n).read_bytes(),(case,n)
   total_pixels+=len((c/f'frame-{i}.hex').read_text().split());total_bytes+=(c/f'packet-{i}.bin').stat().st_size
  log=(c/'simulation.log').read_text();assert 'PASS LIVE NES frames=4 bytes=8032 pixels=245760 fetches=65552' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 assert (total_pixels,total_bytes)==(491520,16064)
 report=(raw/'resource/output_files/live.fit.rpt').read_text(errors='replace');summary=(raw/'resource/output_files/live.fit.summary').read_text()
 assert 'Total logic elements : 13,283 /' in summary and 'Total registers : 4797' in summary and 'Total memory bits : 182,922 /' in summary
 assert int(re.search(r'Total LABs:.*?;\s*(\d+)',report)[1])==926 and re.search(r'; M9Ks\s*; 26 /',report)
 assert sha(raw/'resource/output_files/live.fit.rpt')==budget['accepted_merged_write']['fit_report_sha256']
 rejected=(raw/'rejected-resource/output_files/live.fit.rpt').read_text(errors='replace');assert int(re.search(r'Total LABs:.*?;\s*(\d+)',rejected)[1])==961
 assert budget['reference047']['LE']-budget['accepted_merged_write']['LE']==870 and budget['reference047']['LAB']-budget['accepted_merged_write']['LAB']==27
 assert not re.search(r'Warning \((?:10036|10240)\)',(raw/'resource/map.log').read_text())
 assert not any(m[k] for k in ('new_hardware_image','hardware_executed','timing_signoff'))
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
 count=manifest('analysis/oam-banked-artifacts.json',r) if (r/'analysis/oam-banked-artifacts.json').exists() else 0
 print(json.dumps({'candidate':m['candidate'],'accepted_driver':'tools/nes_oam_compact.py','differential_clocks':216362,'same_edge_write_collisions':2012,'actual_core_frames':8,'unchanged_pixels':491520,'unchanged_bus_bytes':16064,'joint_LE':13283,'LE_saved_vs047':870,'joint_LAB':926,'LAB_remaining':37,'LAB_gained_vs047':27,'joint_M9K':26,'registers':4797,'frozen047_entries':491,'frozen046_entries':107,'frozen045_entries':121,'frozen044_hardware_entries':23,'frozen044_build_entries':386,'protected_GBC_hashes':len(gbc),'hardware_baseline':'044 unchanged','new_hardware_image':False,'timing_signoff':False,'git_diff_check':'PASS','staged_files':0,'allowlist':'PASS','raw_ignored':len(files),'manifest_entries':count},indent=2))
if __name__=='__main__':main()
