# SPDX-License-Identifier: MIT
"""Materialize402 alternatives with exact400 ARM; fixed host is rejected.
Use funded for the retained-host RAM candidate. Neither is production-ready.
"""
import argparse,json,shutil
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_host402 import apply as host
from nes_capture402 import apply as capture

def apply(d,variant='joint'):
 if variant in('host','joint'):host(d)
 if variant in('ram','joint','funded'):
  capture(d);shutil.copyfile(ROOT/'src/fpga/nes_joint402'/('cache_shared.sv'if variant=='funded'else'nes_chr_cache192.sv'),d/'nes_chr_cache192.sv')
 if variant=='funded':compact_program(d)

def compact_program(d):
 # This funds real data RAMs; it does not impose a permanent program cap.
 # A larger future program automatically selects the next capacity and pays
 # its full RAM cost. All reachable control targets remain unchanged.
 info=json.loads((d/'program398.json').read_text());used=info['words'];capacity=1<<used.bit_length();bits=capacity.bit_length()-1
 assert capacity<=4096 and used<capacity
 words=[int(x,16)for x in(d/'program398.hex').read_text().split()]
 assert len(words)==4096 and all(w==(15<<14|255)for w in words[used:])
 targets=[w&4095 for w in words[:used]if w>>14 in(12,13)];assert targets and max(targets)<used
 p=d/'nes_mux260.sv';s=p.read_text();assert ".irq(1'b0)"in s
 for old,new in(('wire[11:0] code_addr,debug_pc;',f'wire[{bits-1}:0] code_addr,debug_pc;'),('reg[11:0] code_tag;',f'reg[{bits-1}:0] code_tag;'),('program398[0:4095]',f'program398[0:{capacity-1}]'),('nes_byte398 #(.ENTRY(',f'nes_byte398 #(.PC_BITS({bits}),.ENTRY(')):
  assert s.count(old)==1,old;s=s.replace(old,new)
 p.write_text(s,newline='\n');(d/'program398.hex').write_text('\n'.join(f'{w:05x}'for w in words[:capacity])+'\n',newline='\n')
 (d/'program-layout402.json').write_text(json.dumps(dict(used=used,capacity=capacity,PC_bits=bits,maximum_control_target=max(targets),padding_traps=True,interrupt_disabled=True,reachable_words_unchanged=True,original_bytes=4096*18//8,new_bytes=capacity*18//8),indent=2)+'\n',newline='\n')

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--variant',choices=('host','ram','joint','funded','reference'),default='funded');a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False)
 ref=BASE/'probes/nes-joint400/build07'
 for q in ref.iterdir():
  if q.is_file()and q.suffix in('.sv','.c','.h','.inc','.s','.a','.ld','.elf','.hex','.json','.su','.log','.map'):shutil.copyfile(q,d/q.name)
 apply(d,a.variant)
 sources=list(json.loads((BASE/'probes/nes-joint400/live04/manifest400.json').read_text())['RTL'])
 if a.variant in('host','joint'):sources.remove('nes_byte398.sv')
 (d/'manifest402.json').write_text(json.dumps(dict(variant=a.variant,RTL={n:sha(d/n)for n in sources},ARM=sha(d/'output.elf'),ARM_changed=False,semantic_VM_removed=a.variant in('host','joint'),source_plan_SPI_bodies_replaced=False),indent=2)+'\n',newline='\n')
 print(json.dumps(dict(variant=a.variant,sources=len(sources),ELF=sha(d/'output.elf'))))
if __name__=='__main__':main()
