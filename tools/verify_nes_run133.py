# SPDX-License-Identifier: MIT
"""Verify exact133 joint sources, legal startup/teardown and synthetic CPU reads."""
from pathlib import Path
import argparse,json,re,collections
from nes_cdc125_sta import ROOT,sha
def review(e):
 t=e/'test03';m=json.loads((t/'run133.json').read_bytes())
 assert m['passed'] and m['pll_model'] and not m['production_changed']
 assert not any(m[k] for k in ['full_image_write_repeated','full_check_repeated','physical_trial'])
 old=e.parents[1]/'nes-counter131/evidence';p=json.loads((ROOT/'analysis/counter131-verification.json').read_bytes())
 assert sha(old/'manifest.json')==p['manifest_sha256']==m['base_manifest']
 pins=json.loads((old/'manifest.json').read_bytes())['files']
 for n,h in m['inputs'].items():assert h==pins[n]==sha(old/n),n
 for n,h in m['sources'].items():assert sha(t/n)==h,n
 for n in ['run133_tb.sv','run133_pll_model.sv']:assert sha(t/n)==sha(ROOT/'tests/nes-functional'/n)
 assert sha(t/'executed-run133.py')==sha(ROOT/'tools/nes_run133.py')
 norm=json.loads((t/'top-normalization.json').read_bytes());s=(old/'fit05/nes_live_joint.sv').read_text()
 assert norm['input_sha256']==sha(old/'fit05/nes_live_joint.sv')
 for d in norm['hoisted']:
  assert '=' not in d and s.count(d)==1;s=s.replace(d,'')
 pos=s.index(');')+2;s=s[:pos]+'\n'+'\n'.join(norm['hoisted'])+s[pos:]
 assert s==(t/'nes_live_joint.sv').read_text() and sha(t/'nes_live_joint.sv')==norm['output_sha256']
 for n,h in m['inputs'].items():
  if n!='fit05/nes_live_joint.sv':assert sha(t/n.split('/',1)[1])==h,n
 summary=[]
 for phase in [0,3500]:
  label='normal-'+str(phase);log=(t/(label+'.log')).read_text()
  assert '** Fatal:' not in log and '** Error:' not in log
  pat=r'PASS133 joint launches=(\d+) releases=(\d+) cancels=(\d+) requests=(\d+) responses=(\d+) chr_changes=(\d+) min_run_age=([\d.]+) min_chr_age=([\d.]+) phase_ps=(\d+) checks=(\d+)'
  a=re.search(pat,log);assert a and list(map(int,a.group(1,2,3,4,5,6)))==[10,10,11,210,206,7]
  lines=(t/(label+'.tsv')).read_text().splitlines();release=[x for x in lines if x.startswith('RELEASE ')];cancel=[x for x in lines if x.startswith('CANCEL ')];response=[x for x in lines if x.startswith('RESPONSE ')]
  assert len(release)==10 and len(cancel)==11 and len(response)==206
  assert all('scrub=8192 ' in x for x in release)
  causes=collections.Counter(x.split()[2] for x in cancel)
  assert causes==dict(STOP=2,STOP_BEFORE_RELOAD=2,SPI_CRC=2,RAW_RESET=2,SOURCE_CLOCK_STOP=1,MEMORY_CLOCK_STOP=1,UNVERIFIED_START=1)
  byrun=collections.defaultdict(list)
  for x in response:
   a0=re.fullmatch(r'RESPONSE ([\d.]+) run=(\d+) address=([0-9a-f]+) data=([0-9a-f]+)',x);assert a0,x
   byrun[int(a0[2])].append((int(a0[3],16),int(a0[4],16)))
  assert set(byrun)==set(range(1,11))
  for n,seq in byrun.items():
   assert seq[:5]==[(65532,0),(65533,128),(0,76),(1,0),(2,128)],(n,seq[:5])
   assert all(pair==[(0,76),(1,0),(2,128)][i%3] for i,pair in enumerate(seq[2:])),n
  ra=min(float(re.search(r'run_age=([\d.]+)',x)[1]) for x in release);ca=min(float(re.search(r'chr_age=([\d.]+)',x)[1]) for x in release)
  assert ra==float(a[7]) and ca==float(a[8]) and ca>45.454
  summary.append(dict(phase_ps=phase,launches=10,releases=10,cancels=11,requests=210,responses=206,chr_changes=7,min_run_to_release_ns=ra,min_chr_to_release_ns=ca,checks=int(a[10]),cancel_causes=dict(causes),reset_vector_and_loop_all_runs=True))
 for label,needle in [('early-core','core release skipped RAM scrub'),('missing-stop','consumer released before initialization')]:
  log=(t/(label+'.log')).read_text();assert '** Fatal: RUN133 '+needle in log and 'PASS133 joint' not in log
 assert (t/'early-core.sv').read_text()==s.replace('common_reset=raw_stop || !memory_ready;','common_reset=raw_stop;')
 assert (t/'missing-stop.sv').read_text()==s.replace('raw_stop=boot_reset || !run_enable;','raw_stop=boot_reset;')
 assert 'Undefined variable' in (e/'test01/compile.log').read_text()
 assert json.loads((e/'test02/run133.json').read_bytes())['passed']
 # Conditions, not a board-time/MTBF claim or a new fit.
 return dict(selected='test03',runs=summary,actual_top_inputs=len(m['inputs']),hoisted_declarations=norm['hoisted'],total_launches=20,total_cancels=22,total_responses=412,causal_rejections=['missing-memory-ready-reset-gate','missing-run-reset-gate'],same_fit='131fit05',new_fit=False,production_rtl_changed=False,seeded_image_and_check_completion=True,actual_spi_start_stop=True,actual_cpu_memory_service=True,ppu_and_pipeline_reset_connected=True,ppu_rendering_verified=False,snes_consumer_exercised=False,analog_pll_or_mtbf_verified=False,physical_trial=False,installable=False)
def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,required=True);e=p.parse_args().evidence
 m=json.loads((ROOT/'analysis/run133-verification.json').read_bytes());assert sha(e/'manifest.json')==m['manifest_sha256']
 files=json.loads((e/'manifest.json').read_bytes())['files'];assert len(files)==m['archived_files']
 for n,h in files.items():assert sha(e/n)==h,n
 for n,h in m['public_sources'].items():assert sha(ROOT/n)==h,n
 assert review(e)==m['checks'];print('PASS133 exact joint sources,20starts/22cancels/412CPU bytes; physical IO/consumer remains separate')
if __name__=='__main__':main()
