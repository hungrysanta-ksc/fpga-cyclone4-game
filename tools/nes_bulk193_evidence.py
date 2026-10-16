# SPDX-License-Identifier: MIT
"""193 direct tile transport evidence; scroll performance remains unmeasured."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False);folder=BASE/'probes/nes-bulk193'
 normal=json.loads((folder/'test04/result.json').read_bytes());faults=json.loads((folder/'faults02/result.json').read_bytes())
 assert normal['passed'] and faults['passed'] and faults['cases']==8
 pins={**normal['source_pins'],**faults['source_pins']}
 for n,h in pins.items():assert sha(BASE/n)==h,n
 for n in ('tools/test_nes_tile_bulk193.py','tools/test_nes_bulk193_faults.py','tools/nes_bulk193_evidence.py'):
  pins['repository-nes-milestone/'+n]=sha(ROOT/n);shutil.copyfile(ROOT/n,a.out/Path(n).name)
 prior=[]
 for name in ('nes-paired186','nes-game186-hardware01','nes-video-arch187','nes-bulk188','nes-source189','nes-chr190','nes-plan191','nes-source192'):
  archive=BASE/'probes'/name;manifest=archive/'manifest01.json';entries=json.loads(manifest.read_bytes())
  for n,h in entries.items():assert sha(archive/n)==h,(name,n)
  prior.append(dict(name=name,files=len(entries),manifest_sha256=sha(manifest)))
 r=dict(passed=True,selected=['test04','faults02','evidence01'],cases=normal['cases'],negative_cases=8,
  source_pins=pins,prior_archives=prior,
  normal_payload_bytes=1840,pressure_payload_bytes=8192,pressure_chunks=4,
  descriptor_bits=27,cdc_metadata_bits=34,dual_clock_tile_bytes=32,aperture_bytes_reused=4096,
  no_per_tile_payload_header=True,control_bus_bytes_not_measured=True,
  preliminary_m9k_accounting=dict(deployed=42,aperture_estimate=4,tile_store_estimate=1,total_estimate=47,device=56,not_synthesis=True),
  actual_scroll_measured=False,performance_change_percent=None,physical_fps=None,
  production_snes_client=False,control_decoder=False,whole_frame_commit=False,physical_cdc=False,
  new_fit=False,new_firmware=False,new_package=False,
  scope='Actual192 source/READ16 -> immutable32B dual-clock tile RAM+34bit metadata mailbox ->188 raw bus. Synthetic C-reference scenes and pin memory; no live game or actual65816 DMA.')
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
 plan=dict(status='required_not_yet_measured',workload='SMB3(J) first level continuous camera scrolling',
  rom_sha256='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49',
  user_recipe=['world map: move to tile1 and press A','verify first-level scene','hold RIGHT+B and repeatedly press/release A'],
  acceptance=['measure continuous camera-scroll interval, not intro or stationary scene',
   'match source/conversion/transfer/display evidence by generation within each run',
   'compare baseline and candidate over comparable game state, scrolling distance and input sequence',
   'separate initial cold load, warm scrolling, static scene, transition and raw-fallback rows',
   'use unique completed display generations and actual display intervals; do not divide all ACKs by total60s',
   'preserve sound/input/core priority; no improvement accepted by skipping gameplay work',
   'avoid per-frame SD writes; reuse bounded counters/captures and write after STOP/reset/error'],
  metrics=['source physical reads and cache hits/misses','new/reused tile/plan counts','BG/OBJ/raw/control bytes',
   'capture/prepare/transfer/VRAM-display latency','display interval median/p95/max and distinct display cadence'],
  collected_runs=[],notes='193 proves transport correctness only. Intro/repeated-tile percentages are not actual load reduction.')
 (a.out/'scroll-measurement-plan.json').write_text(json.dumps(plan,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,normal_bytes=1840,pressure_bytes=8192,pressure=normal['cases'][-1],prior_files=[x['files'] for x in prior],actual_scroll_measured=False)))
if __name__=='__main__':main()
