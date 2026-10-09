# SPDX-License-Identifier: MIT
"""Pinned128 core with reset-scoped, registered reader ownership."""
import json,shutil
from nes_loader127 import ROOT,sha,put,replace

def materialize(o,baseline,full=False):
 e=baseline/'nes-command128/evidence';m=json.loads((ROOT/'analysis/command128-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prefix='fit07/'
 names=[n[len(prefix):] for n in pins if n.startswith(prefix) and n.endswith(('.sv','.v','.vhd','.qsf','.sdc','.qpf'))]
 if not full:names=[n for n in names if '/' not in n and n.endswith('.sv')]
 inputs={}
 for n in names:
  src=e/prefix/n;assert sha(src)==pins[prefix+n];dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 p=o/'nes_rom_physical.sv';s=p.read_text()
 s=replace(s,'wire sr=source_reset[1],mr=memory_reset[1];','''wire sr=source_reset[1],mr=memory_reset[1];
 //129 The owner changes only across common reader reset. Capture it after
 // local release and delay readiness until capture completes. Raw cancellation
 // still asynchronously clears both the controller and this ownership latch.
 reg owner_valid,owner_check;
 always @(posedge mem_clk or posedge mr)
  if(mr)begin owner_valid<=0;owner_check<=0;end
  else if(!owner_valid)begin owner_valid<=1;owner_check<=check_mode;end''')
 s=replace(s,'assign check_ready=!mr && check_mode && state==IDLE;','assign check_ready=!mr && owner_valid && owner_check && state==IDLE;')
 s=replace(s,'wire pending=check_mode ? check_request : request_sync[1]!=ack_toggle;','wire pending=owner_valid && (owner_check ? check_request : request_sync[1]!=ack_toggle);')
 s=replace(s,'wire [21:0] selected_address=check_mode ? check_address : address_hold;','wire [21:0] selected_address=owner_check ? check_address : address_hold;')
 s=replace(s,'if(check_mode)check_response<=1;else ack_toggle<=request_sync[1];','if(owner_check)check_response<=1;else ack_toggle<=request_sync[1];')
 put(p,s)
 p=o/'nes_rom_boot.sv';s=p.read_text()
 # raw_check_ready already requires the reader's captured CHECK owner. The
 # outer check_ready retains immediate visible legality; check_failed and
 # reader_reset still cancel a bad command before the active memory phase.
 s=replace(s,'.check_request(check_request && check_ready && address_valid)',
  '.check_request(check_request && raw_check_ready && address_valid && !check_failed)')
 put(p,s)
 put(o/'materialization129.json',json.dumps(dict(inputs=inputs,outputs={p.relative_to(o).as_posix():sha(p) for p in o.rglob('*') if p.is_file()}),indent=2)+'\n')
