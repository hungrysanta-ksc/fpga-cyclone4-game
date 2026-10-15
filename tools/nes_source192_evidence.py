# SPDX-License-Identifier: MIT
"""Source192 audit and qualified-read budget; simulation is not physical FPS."""
from pathlib import Path
import argparse,hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 folder=BASE/'probes/nes-source192'
 old=json.loads((folder/'test01/result.json').read_bytes())
 new=json.loads((folder/'test03/result.json').read_bytes())
 assert old['passed'] and new['passed'] and new['negative_cases']==9
 for path,h in new['source_pins'].items():assert sha(BASE/path)==h,path
 # Historical candidate files are intentionally different; verify archived bytes.
 for path,h in old['source_pins'].items():
  assert sha(folder/'test01'/Path(path).name)==h,path
 selected_pins=dict(new['source_pins'])
 for n in ('tools/test_nes_source192.py','tools/nes_source192_evidence.py'):
  selected_pins['repository-nes-milestone/'+n]=sha(ROOT/n)
  shutil.copyfile(ROOT/n,a.out/Path(n).name)
 board=BASE/'probes/nes-window184-coupled/evidence/route02'
 core=(board/'rtl/nes.v').read_text();service=(board/'nes_rom_service.sv').read_text()
 assert 'div_cpu==3 && scanline_ppu>=242 && scanline_ppu<260' in core
 assert '!cpu_need&&!ppu_need&&!prefetch_need&&cpu_valid&&cpu_address_valid' in service
 for pth in (board/'rtl/nes.v',board/'nes_rom_service.sv',board/'nes_native_fetch165.sv'):
  selected_pins[pth.relative_to(BASE).as_posix()]=sha(pth)
 comparison=[]
 for before,after in zip(old['cases'],new['cases']):
  assert (before['scene'],before['mode'],before['tiles'],before['bytes'])==(after['scene'],after['mode'],after['tiles'],after['bytes'])
  comparison.append(dict(scene=after['scene'],mode=after['mode'],output_bytes=after['bytes'],
    old_reads=before['reads'],new_reads=after['reads'],old_windows=before['read_windows'],new_windows=after['read_windows'],
    old_synthetic_ms=before['synthetic_elapsed_ms'],new_synthetic_ms=after['synthetic_elapsed_ms']))
 prior=[]
 for name in ('nes-paired186','nes-game186-hardware01','nes-video-arch187','nes-bulk188','nes-source189','nes-chr190','nes-plan191'):
  archive=BASE/'probes'/name;manifest=archive/'manifest01.json';entries=json.loads(manifest.read_bytes())
  for path,h in entries.items():assert sha(archive/path)==h,(name,path)
  prior.append(dict(name=name,files=len(entries),manifest_sha256=sha(manifest)))
 report=dict(passed=True,selected=['test03','evidence01'],baseline='test01',intermediate='test02',
  comparison=comparison,negative_and_lifetime_cases=9,source_pins=selected_pins,
  normal_before_reads=sum(c['old_reads'] for c in comparison[:8]),normal_after_reads=sum(c['new_reads'] for c in comparison[:8]),
  optimistic_source_bytes_per_frame=(260-242)*341*4//12,
  model_assumptions=['21.477MHz NES clock/168MHz memory clock','READ16 with70ns pin memory fixture',
   'qualified interval242..259, one slot per12 clocks','core safe forced true,10percent slots have core traffic',
   'normal8 fixtures from actual186 converter; stress replays the SAME BG plan512times, not512unique tiles or a game'],
  cache_payload_bytes=16,tile_payload_bytes=32,cache_entries=1,
  excludes=['live CPU/PPU grant schedule','source epoch producer and frame-start latch','mutable CHR snapshot',
   'plan transport/CDC','aperture and SNES DMA/ACK','board fit/IO','actual scrolling scene/FPS'],
  decision='Keep core-priority qualification. Retain bounded physical-source reuse, but one-entry cache only saves42/1304 normal fixture reads. Next direct section/aperture path and stable content-key reuse budget, not blanket unqualified reads or long diagnostics.',
  new_fit=False,new_firmware=False,new_package=False,physical_fps=False,prior_archives=prior)
 (a.out/'result.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(passed=True,normal_before=report['normal_before_reads'],normal_after=report['normal_after_reads'],stress=comparison[-1],prior_files=[x['files'] for x in prior])))
if __name__=='__main__':main()
