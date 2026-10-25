# SPDX-License-Identifier: MIT
"""Replay the same354 warm snapshot to separate representation and dispatch costs."""
import argparse,json
from pathlib import Path
from nes_delta231 import BASE,sha
from check_nes_compact354 import objects
from profile_nes_prepare353 import Profile

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,required=True);ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 baseline=BASE/'probes/nes-compact354/fixed01';snapshot=baseline/'precommit352-3.bin';pins={str(snapshot):sha(snapshot)};rows=[]
 for label,d in [('354',baseline),('dual-per-access',a.root/'build02'),('dual-inline',a.root/'build03'),('entry-selected',a.root/'build05')]:
  elf=d/'output.elf';assert objects(elf)==objects(baseline/'output.elf');pins[str(elf)]=sha(elf)
  arm=Profile(elf);arm.uc.mem_write(0x20000000,snapshot.read_bytes());arm.uc.mem_write(arm.symbols['ctx286']+119,b'\0');calls=[]
  for name in ('expand286','geometry_plan286','h2early286','input_commit286','begin_step286'):
   arm.counts.clear();before=arm.instructions;assert arm.call(name,[])==1
   calls.append(dict(name=name,instructions=arm.instructions-before,exclusive=dict(arm.counts)))
  rows.append(dict(candidate=label,calls=calls,five_call_total=sum(x['instructions'] for x in calls)))
 result=dict(passed=True,rows=rows,pins=pins,scope='Same actual354 warm snapshot; five preparation calls only, not frame timing. Failed source generators build01/04 are excluded.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(rows,indent=2))
if __name__=='__main__':main()
