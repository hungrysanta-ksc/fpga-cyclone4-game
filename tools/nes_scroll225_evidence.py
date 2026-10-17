# SPDX-License-Identifier: MIT
"""Bind225 source, C/65816 pixels, ARM budget and unchanged FPGA evidence."""
from pathlib import Path
import argparse,json,re
from nes_scroll225 import ROOT,BASE,sha,planner

def read(p):return json.loads(p.read_bytes())
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();d=a.archive.resolve();assert not(d/'manifest01.json').exists()
 arm=d/'arm01';prep=read(arm/'preparation-scroll225.json')
 for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
 test=read(d/'test02/result.json');snes=read(d/'snes02/result.json');run=read(d/'runtime01/result.json');check=read(d/'check02/result.json')
 assert all(x['passed'] for x in [test,snes,run,check])
 selected=BASE/'probes/nes-ingress223/arm01/src'
 assert (arm/'src/nes_planner211.c').read_text()==planner((selected/'nes_planner211.c').read_text())
 for directory in [d/'test02/candidate',d/'snes02/candidate',d/'runtime01']:
  for n in ['nes_planner211.c','nes_resident211.c','nes_native165.c','nes_native_sink165.c']:
   assert sha(directory/n)==sha(arm/'src'/n),(directory,n)
 for n in ['nes_native_runtime165.c','nes_sink_window184.c','nes_plan_service200.c','nes_budget210.c']:
  assert sha(d/'runtime01'/n)==sha(arm/'src'/n)==sha(selected/n),n
 assert check['remaining_margin']==1912 and check['ram_static']==28020
 assert check['firmware_sha256']==sha(arm/'src/obj-nes-100/firmware.stm')
 assert check['elf_sha256']==sha(arm/'src/obj-nes-100/sd2snes.elf')
 pixels=0
 for i in range(1,31):
  x=d/f'snes02/reference-normal/frame-{i}.rgb';y=d/f'snes02/candidate-normal/frame-{i}.rgb'
  assert x.read_bytes()==y.read_bytes() and x.stat().st_size==183552
  pixels+=x.stat().st_size//3
 assert pixels==1835520
 assert sha(d/'snes02/client/sink-program.hex')==sha(BASE/'probes/nes-runtime213/asm01/sink-program.hex')
 costs={}
 for kind,text in test['results'].items():
  assert 'frames=353 ' in text and 'FAULTS boundaries=11 ' in text
  m=re.search(r'COST225 scroll_map_packet_bytes=(\d+) scroll_map_commands=(\d+) scroll_upload_bytes=(\d+)',text);assert m
  costs[kind]=dict(zip(['map_e1_clock_bytes','map_commands','map_upload_bytes'],map(int,m.groups())))
 assert costs['baseline']['map_e1_clock_bytes']==761684 and costs['candidate']['map_e1_clock_bytes']==385104
 wire={}
 for f in (d/'snes02/candidate-normal').glob('req-*.bin'):
  b=f.read_bytes();key='op%d_section%d'%(b[0],b[1]);entry=wire.setdefault(key,dict(packets=0,e1_clock_bytes=0))
  entry['packets']+=1;entry['e1_clock_bytes']+=len(b)+3
 cases=[dict(mode=x['mode'],type=x['type'],commits=x['commits']) for x in snes['cases']]
 assert set(x['mode'] for x in cases)=={'normal','bad_base','missing_map','wrong_display_ack'}
 public=['tools/nes_scroll225.py','tools/test_nes_scroll225.py','tools/test_nes_scroll225_snes.py','tools/test_nes_scroll225_runtime.py','tools/check_nes_scroll225_arm.py','tools/nes_scroll225_evidence.py']
 result=dict(passed=True,trial_gates_pass=True,physical=False,fps60=False,new_fit=False,new_snes_rom=False,new_state_bytes=0,
  synthetic_scroll=dict(frames=192,costs=costs,map_e1_reduction_percent=(1-385104/761684)*100,
   mixed353_note='Adversarial random placement: total E1 bytes1601186->1613679; not universal gain. checked counter mixes normalBG pixels and OBJ bytes, not purepixel count.'),
  c_frames=353,c_fault_boundaries=11,snes_frames=30,snes_reference_pixels=pixels,snes_cases=cases,
  actual_sink_packet_composition=wire,composition_scope='Thirty synthetic225 frames; E1 framing3 included, E0 polls/audio/aperture excluded. Not physical223 breakdown.',
  runtime=dict(frames=9,faults=6,wire_input='Archived scalar203 geometry withBEGIN version2231; packed exporter unchanged evidence reused',source_hashes=run['source_hashes']),
  arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin','firmware_sha256']},
  baseline=dict(merge='6c4bd8412a9e6bba0c5c54939029a95e20db22ea',fpga_sha256=read(BASE/'probes/nes-counter224/release01/result.json')['fpga_sha256']),
  gates={n:sha(d/n) for n in ['test02/result.json','snes02/result.json','runtime01/result.json','check02/result.json','arm01/preparation-scroll225.json']},
  public_sources={n:sha(ROOT/n) for n in public},limitations=['No complete live NES/SPI/65816 cosimulation; exact C+65816 fixture and separate unchanged FPGA proofs.',
   'Map64B dirty granularity and ingress/full planner remain; savings cannot be interpreted as60fps.',
   'Placement only: physical fetch tags, epoch, row-alt/mask, two-bank union and finalACK remain unchanged.'],
  next='Package unchanged223FPGA+225ARM then actual first-level scrolling,3TXT/menu/audio/input. No extraFIT/unchanged223/044repeat.')
 text=json.dumps(result,indent=2)+'\n';(d/'analysis.json').write_text(text,encoding='utf8');(ROOT/'analysis/scroll225-verification.json').write_text(text,encoding='utf8')
 print(json.dumps(dict(passed=True,costs=costs,pixels=pixels,arm=result['arm'],packet_composition=wire)))
if __name__=='__main__':main()
