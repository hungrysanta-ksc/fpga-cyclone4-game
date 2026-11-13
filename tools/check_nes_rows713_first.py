"""Actual first-BG admission gate; map executor replaced by a counted stub here."""
import argparse,json
from pathlib import Path
from check_nes_longrun693 import Probe
from check_nes_game478 import ELFFile,UC_HOOK_CODE,sha
from test_nes_raw506_joint import member_offset

def run(a):
 rows=[]
 for early,ready in ((0,3),(0,6),(0,31),(0,32),(1,3),(1,6),(1,31)):
  m=Probe(a.arm);L=m.layout['nes_native_runtime165'];plan=m.rt+L['plan'];sink=m.rt+L['sink'];fields={}
  with (a.arm/'obj-nes-100/sd2snes.elf').open('rb') as f:
   for cu in ELFFile(f).get_dwarf_info().iter_CUs():
    for d in cu.iter_DIEs():
     if d.tag=='DW_TAG_structure_type' and d.attributes.get('DW_AT_name') and d.attributes['DW_AT_name'].value==b'nes_plan200':
      fields.update({x.attributes['DW_AT_name'].value.decode():member_offset(x) for x in d.iter_children() if x.tag=='DW_TAG_member'})
  m.u.mem_write(plan+fields['early'],bytes([early]));called=[]
  def execute(u,pc,size,user):called.append(pc);m.ret(u,1)
  pc=m.syms['map527'];m.u.hook_add(UC_HOOK_CODE,execute,begin=pc,end=pc)
  assert m.call('offer527',[m.rt,ready])
  allowed=bool(early or ready==32);assert len(called)==int(allowed)
  quiet=int.from_bytes(m.u.mem_read(plan+fields['quiet_map'],4),'little');assert bool(quiet)==allowed
  rows.append(dict(early=early,completed_rows=ready,map_called=allowed,passed=True))
 a.out.write_text(json.dumps(dict(passed=True,firmware=sha(a.arm/'obj-nes-100/firmware.stm'),cases=rows,scope=__doc__),indent=2)+'\n');print('PASS713 first-BG gate',len(rows))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('arm','out'):p.add_argument('--'+n,type=Path,required=True)
 run(p.parse_args())
