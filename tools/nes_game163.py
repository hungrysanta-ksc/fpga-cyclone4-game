# SPDX-License-Identifier: MIT
"""Prepare MCU163 and a copy of routed162 for a program-ROM content update."""
from pathlib import Path
import argparse,json,shutil
from nes_game147 import ROOT,sha

def prepare(baseline,out,client=None,arm=False):
 e=baseline/'nes-game162/evidence';m=json.loads((ROOT/'analysis/game162-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256'];pins=json.loads((e/'manifest.json').read_bytes())['files']
 assert not out.exists() and str(out).isascii()
 section='arm' if arm else 'asm'
 names=list(json.loads((e/'arm/preparation162.json').read_bytes())['copied']) if arm else [n[4:] for n in pins if n.startswith('asm/')]
 out.mkdir(parents=True);inputs={}
 for n in names:
  src=e/section/n;assert sha(src)==pins[section+'/'+n],n
  dst=out/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 def edit(n,a,b,count=None):
  p=out/n;s=p.read_text();assert a in s,n
  if count is not None:assert s.count(a)==count,(n,s.count(a))
  p.write_text(s.replace(a,b),encoding='utf8',newline='\n')
 if arm:
  for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:edit('src/'+n,'162','163')
  edit('src/nes_menu_diagnostic.c','"apu_channel_writes_blocked=0\\npad_trace_valid=',
       '"spc_init_status_hex=%02x\\nspc_init_status_valid=%u\\nspc_unmute_confirmed=%u\\nspc_result_source=SNES_CLIENT_FLG20_READBACK\\nscreen_error_field_role=SPC_INIT_RESULT_163\\napu_channel_writes_blocked=0\\npad_trace_valid=',1)
  edit('src/nes_menu_diagnostic.c','  nes_run136.pad_valid,nes_run136.pad_total,',
       '  nes_run136.screen_error,nes_run136.screen_valid&&(nes_run136.screen_error==0xa9||(nes_run136.screen_error>=0xe1&&nes_run136.screen_error<=0xe5)),nes_run136.screen_valid&&nes_run136.screen_error==0xa9,\n  nes_run136.pad_valid,nes_run136.pad_total,',1)
 else:
  assert client is not None
  r=json.loads((client/'result.json').read_bytes());assert r['passed']
  shutil.copy2(client/'client/game-program.hex',out/'game-program.hex')
 changed={n:sha(out/n) for n,h in inputs.items() if sha(out/n)!=h}
 if not arm:assert set(changed)=={'game-program.hex'}
 # Deliberately retain the exact162 RTL identity6B/E5, not a new/widened ID set.
 # Client163 is separately identified by its one-shot A9/E1..E5 status.
 (out/'preparation163.json').write_text(json.dumps(dict(copied=inputs,changed=changed,added={},ids=['6B','E5'],client='163',rtl_reused='162',physical=False),indent=2)+'\n')
 return out
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--client',type=Path);p.add_argument('--arm',action='store_true');a=p.parse_args();prepare(a.baseline,a.out,a.client,a.arm)
