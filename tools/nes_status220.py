# SPDX-License-Identifier: MIT
"""Same-edge status/READY predicates; no added clock or protocol latency."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def transform(s):
 s=replace(s,' assign run_enable=!active_reset && !fault && phase[RUN];',''' // 220: asynchronous phase reset establishes IDLE, and local reset release
 // keeps IDLE. Thus phase[RUN] implies !active_reset in reachable operation.
 // Keep the sticky fault gate; external PSRAM reset gates are unchanged.
 assign run_enable=!fault && phase[RUN];''')
 s=replace(s,''' wire to_ready=(phase[READY] && !ir_bad && !stop && !accepted_load_begin && !accepted_start && !accepted_load_valid) ||
  (phase[RECEIVE] && !receive_bad && !stop && accepted_load_end && count_complete) ||
  (phase[RUN] && !run_bad && stop);''',''' // 220: flatten READY admission per origin. END implies !blocked, so its
 // simultaneous-command exclusions need no nested receive_bad decoder.
 wire to_ready=(phase[READY] && !fault && !stop &&
                   (commands_blocked || !(load_begin || load_valid || load_end || start))) ||
  (phase[RECEIVE] && !fault && !commands_blocked && !load_begin && !start &&
                   !stop && load_end && !load_valid && count_complete) ||
  (phase[RUN] && !fault && stop && (commands_blocked || !(load_begin || load_end || start)));''')
 return s

def prepare(out):
 old=BASE/'probes/nes-retire219/source02';p=json.loads((old/'preparation219.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 n='nes_rom_loader.sv';before=(old/n).read_text();after=transform(before)
 (out/n).write_text(after,encoding='utf8',newline='\n')
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['sources'],changed=['nes_rom_loader.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},adopted=False,no_package=True)
 assert [n for n,h in r['sources'].items() if h!=r['baseline'][n]]==r['changed']
 (out/'preparation220.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
