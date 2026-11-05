# SPDX-License-Identifier: MIT
"""Publish591 ARM gate failure and actual-call input sensitivities, not FPS."""
import argparse,json,statistics,zipfile
from pathlib import Path
from analyze_nes_transport584 import elf_cost,sha
from analyze_nes_ownership585 import inventory
from check_nes_game478 import ELFFile

ROOT=Path(__file__).resolve().parents[1]

def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('base','arm','patch','test','out','private'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();r=json.loads((a.test/'result.json').read_text())
 assert r['passed'] and len(r['frames'])==53 and len(r['guards'])==18
 assert r['pins']['checker_sha256']==sha(ROOT/'tools/check_nes_roles591.py')
 patch=json.loads((a.patch/'manifest.json').read_text())
 manifest=json.loads((ROOT/'analysis/whole580-manifest.json').read_text())
 for n,h in patch['baseline'].items():assert sha(a.base/n)==h==manifest['ARM_project_files']['src/'+n]['sha256']
 for n,h in patch['patched'].items():assert sha(a.arm/n)==h
 d=json.loads((ROOT/'analysis/whole580-verification.json').read_text())['phases'][0]['parameters']['driver_extra_us']
 groups={}
 for name,lo,hi in [('cold905',905,905),('warm907_957',907,957),('dense951_955',951,955)]:
  groups[name]={}
  for label,key in [('577','baseline_frames'),('591','frames')]:
   rows=[]
   for f in r[key]:
    if not lo<=f['generation']<=hi:continue
    n=f['packets'];k=f.get('D4',0);d0=f['calls']-2*n-k-1
    wire=f.get('wire_B',f['payload_B']+3*n+8*(f['calls']-n))
    driver=(d0*d['0xd0']+n*(d['0xd1']+d['0xd2'])+(1+k)*d['0xd3'])/1000
    io=wire*8/2625000*1000+driver
    rows.append(dict(IO_ms=io,wire_B=wire,calls=f['calls'],packets=n,D4=k,D0=d0,instructions=f['instructions'],
                     CPI1_input_ms=io+f['instructions']/84000,CPI2_input_ms=io+2*f['instructions']/84000))
   groups[name][label]={k:statistics.mean(x[k] for x in rows) for k in rows[0]}
  groups[name]['CPI2_input_delta_ms']=groups[name]['591']['CPI2_input_ms']-groups[name]['577']['CPI2_input_ms']
 changes={}
 for old in (a.base/'obj-nes-100').glob('*.o'):
  new=a.arm/'obj-nes-100'/old.name
  if new.exists():
   x=elf_cost(old)['code_B'];y=elf_cost(new)['code_B']
   if x!=y:changes[old.stem]=dict(old_B=x,new_B=y,delta_B=y-x)
 layouts={k:inventory(src) for k,src in [('577',a.base),('591',a.arm)]}
 with (a.arm/'obj-nes-100/sd2snes.elf').open('rb') as f:
  e=ELFFile(f);helper=e.get_section_by_name('.symtab').get_symbol_by_name('__popcountsi2')[0]['st_size']
 assert r['linked_cost']['591']['code_B']-r['linked_cost']['577']['code_B']==sum(v['delta_B'] for v in changes.values())+helper
 r.update(groups=groups,object_code_changes=changes,
  additional_linked_library=dict(__popcountsi2_B=helper),
  functions={k:v['modules']['nes_native165'] for k,v in layouts.items()},
  memory={k:dict(receiver_B=v['structs']['nes_native165']['size_B'],frame_stack_B=v['stack_frames_B']['native_frames222.isra'],
                gap_before_callees_IRQ_B=v['gap_before_callees_IRQ_B'],static_B=v['static_B'])for k,v in layouts.items()},
  decision='reject591_ARM_Flash_before_FPGA_implementation_MAP_and_two_phase_expansion',
  request_correction='Explicit MAP_ACCEPT D4/D0 required after full rows; otherwise repair races already-sealed nonmap. Additional actual D0 after phase waits is also charged.',
  patch=patch,firmware_delta_B=r['linked_cost']['591']['firmware_B']-r['linked_cost']['577']['firmware_B'],
  new_FIT=False,new_package=False,product_baseline='MMC577',
  limitations=['SPI endpoint is a single sealed packet Python model; not actual FPGA or ROM grants.',
   'CPI1/2 are sensitivities at84MHz, not measured cycles or IRQ service; D4 driver uses oldD3 mean.',
   'Source COMMIT/D2 confirmation exercised in ARM. Final displayACK/EA is an unchanged runtime path with consumed fixture, not new65816 verification.',
   'Cold computation regresses; warm/dense input savings alone do not establish60Hz or firstBG/finalACK improvement.',
   'No new FPGA implementation or Quartus Lite MAP because first wholeARM budget gate failed. No new circuit saving exists.'])
 a.private.mkdir(parents=True,exist_ok=False);files={}
 for q in a.patch.iterdir():
  if q.is_file():files['patch/'+q.name]=q
 for name in ('result.json',):files['test/'+name]=a.test/name
 for name in ('build.log','size.log','bootstrap.log'):files['build/'+name]=a.arm.parent/name
 for name in ('sd2snes.elf','firmware.stm','nes_native165.o','nes_native165.su','nes_native_runtime165.o','nes_native_runtime165.su'):
  q=a.arm/'obj-nes-100'/name
  if q.exists():files['linked/'+name]=q
 for name in ('prepare_nes_roles591.py','nes_rows591.inc','check_nes_roles591.py','analyze_nes_roles591.py','build_nes_trial577.ps1'):
  files['tools/'+name]=ROOT/'tools'/name
 archive=a.private/'evidence.private.zip'
 with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED)as z:
  for name,q in files.items():z.write(q,name)
 r['private_archive']=dict(sha256=sha(archive),size_B=archive.stat().st_size,files={n:sha(q) for n,q in files.items()})
 a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(groups=groups,object_code_changes=changes,excess_B=r['excess_B'],archive=r['private_archive']['sha256']),indent=2))

if __name__=='__main__':main()
