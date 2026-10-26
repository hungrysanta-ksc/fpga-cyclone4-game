# SPDX-License-Identifier: MIT
"""Actual M4 next-source writes and a publish-history lifetime counterexample.

Uses real precommit3 RAM and real postdisplay3 resident/dirty objects. Combining
those snapshots is a deliberate lifetime experiment,not a new live schedule.
No SPI/IRQ overlap or time gain is inferred from decoder instruction counts.
"""
import argparse,binascii,json,struct
from pathlib import Path
from check_nes_compact354 import objects
from probe_nes_arm264 import ARM
from unicorn import UC_HOOK_MEM_WRITE
from probe_nes_decode280 import records,chunks,golden
from nes_delta231 import ROOT,BASE,sha


def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 d=BASE/'probes/nes-frontier377/joint01';elf=d/'output.elf';syms=objects(elf)
 before=(d/'precommit352-3.bin').read_bytes();after=(d/'causal368-4-2.bin').read_bytes()
 arm=ARM(elf,None);arm.uc.mem_write(0x20000000,before)
 def obj(name):return bytes(arm.uc.mem_read(*syms[name]))
 def word(name):return int.from_bytes(obj(name),'little')
 keep={n:obj(n) for n in ('input285','video285','resident285','dirty285','certificate286','output285','seal289')}
 written=set()
 def watch(uc,access,address,size,value,user):
  for n,(at,nbytes) in syms.items():
   if at<address+size and address<at+nbytes:written.add(n)
 h=arm.uc.hook_add(UC_HOOK_MEM_WRITE,watch)
 start=arm.instructions;blocks=chunks(records(d/'frame908.records'))
 for b in blocks:
  arm.uc.mem_write(0x20028000,b);assert arm.call('block286',[0x20028000,len(b),binascii.crc_hqx(b,65535)])==1
 instructions=arm.instructions-start;arm.uc.hook_del(h)
 assert arm.call('complete280',[])==1
 assert obj('history286')==b''.join(golden(908))
 for n,data in keep.items():assert obj(n)==data,(n,'prefetch overwrote current output')
 receiver_serial=struct.unpack_from('<I',obj('receiver280'),4)[0];assert receiver_serial==4
 # Model the already-verified current display3 retirement by importing only
 # its actual closed resident/dirty objects. The next receiver remains4.
 for n in ('resident285','dirty285'):
  at,size=syms[n];arm.uc.mem_write(at,after[at-0x20000000:at-0x20000000+size])
 resident_serial=struct.unpack_from('<I',obj('resident285'),3164)[0];assert resident_serial==3
 arm.call('publish352',[]);published=word('display_serial352');assert published==4 and published!=resident_serial
 plan_path=ROOT/'src/fpga/nes_dual373/nes_plan_path267.sv';plan=plan_path.read_text()
 assert 'wire host_owner=pre_sync[1]&&!display_sync[1]&&immutable;' in plan
 source=d/'nes_decode280.c';decoder=source.read_text()
 assert '!r->displayed||r->open||r->prepared||r->fault' in decoder
 # This is the existing function's unsafe binding under an early receiver.
 # A frozen current-frame epoch/serial/raw_count(12B+valid/alignment=16B)
 # must replace that dependency before an incremental scheduler is enabled.
 result=dict(audit_completed=True,source_blocks=len(blocks),decoder_instructions=instructions,full_source_exact=True,
  current_output_objects_unchanged=list(keep),written_objects=sorted(written),
  counterexample=dict(current_display_serial=resident_serial,next_receiver_serial=receiver_serial,incorrect_published_display_serial=published,old_publish_safe_for_early_ingest=False,synthetic_lifetime_overlap=True),
  proposed_ARM_bytes=dict(frozen_commit=16,incremental_RX=24,total=40,implemented=False),
  hint_ownership=dict(ARM_suppressed_while_resident_open=True,FPGA_host_hint_excludes_display_lease=True,separate_next_input_generation_implemented=False,new_FPGA_area=None),
  caveats=['Actualblockdecoder+mixed real snapshot objects;not a live simultaneous ARM/SPI/IRQ run.','No planner expansion or input_commit for next frame before current display commit.','Existing source_hint suppresses hints while resident.open;early-source schedule needs causal projected-bank hint ownership.','STOP/CRC failure must invalidate both pending display and prefetched input.','AdditionalRAM/time/IRQ cost remains unmeasured.'],
  time_gain_ms=None,FPGA_area_gain=0,pins={str(x):sha(x) for x in (elf,d/'precommit352-3.bin',d/'causal368-4-2.bin',d/'frame908.records',source,plan_path,ROOT/'tools/audit_nes_ingest385.py')})
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
