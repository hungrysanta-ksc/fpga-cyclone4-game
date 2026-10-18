# SPDX-License-Identifier: MIT
"""Actual bitmap overlap rejection, including a completed16-bit prefix.

Real protocol after one displayed frame; no WRAM/ACK injection. The marker
must be reached and reject, retaining the previously displayed frame.
"""
import inspect,json
import test_nes_maskfault247 as base
from nes_delta231 import once

CASES=('bg_overlap','bg_partial','obj_overlap','obj_partial','cgram_overlap','raw_overlap')


def main():
 s=inspect.getsource(base.main)
 s=once(s,'  for n,b in packets.items():', '''  kind={'bg':0,'obj':1,'cgram':3,'raw':5}[case.split('_')[0]]
  names=[name for name in second if originals[name][1]==kind and originals[name][0] in (2,4,5,7)]
  if kind==5:names=[name for name in names if int.from_bytes(originals[name][10:12],'little')>=1121]
  assert len(names)>=2
  if case.endswith('partial'):
   unit=16 if kind==0 else32
   packets[names[0]][10:12]=(16*unit).to_bytes(2,'little')
   packets[names[1]][10:12]=(15*unit).to_bytes(2,'little')
  else:
   first=originals[names[0]];unit=16 if kind in (0,3,5) else32
   n=int.from_bytes(first[14:16] if first[0] in (4,5,7) else first[12:14],'little')
   at=int.from_bytes(first[10:12],'little')+n-unit
   packets[names[1]][10:12]=at.to_bytes(2,'little')
  for n,b in packets.items():'''.replace('else32','else 32'))
 s=once(s,"  (d/'capture.lua').write_text", '''  labels=json.loads((a.client/'labels.json').read_text());target=int(names[1].split('-')[1].split('.')[0])
  at=lua.index('emu.addMemoryCallback(')
  hook="local overlapSeen247=false\\nlocal partialSeen247=false\\nlocal overlapReject247=false\\nlocal target247="+str(target)+"\\n"
  hook+="emu.addMemoryCallback(function() if ordinal==target247 then overlapSeen247=true;if word(0x6a)%16==0 then partialSeen247=true end end end,emu.callbackType.exec,"+str(labels['bits212'])+")\\n"
  check="assert(partialSeen247,'missing completed prefix');" if case.endswith('partial') else ''
  hook+="emu.addMemoryCallback(function() if ordinal==target247 then assert(overlapSeen247,'marker not reached');"+check+"overlapReject247=true end end,emu.callbackType.exec,"+str(labels['mark_bad212'])+")\\n"
  lua=lua[:at]+hook+lua[at:]
  lua=once(lua,"assert(commits==1 and word(0x1228)==2", "assert(overlapReject247,'missing range rejection');assert(commits==1 and word(0x1228)==2")
  (d/'capture.lua').write_text''')
 ns=dict(base.__dict__);ns.update(CASES=CASES,__file__=__file__,__doc__=__doc__)
 exec(compile(s,'validationfault247','exec'),ns);ns['main']()


if __name__=='__main__':main()
