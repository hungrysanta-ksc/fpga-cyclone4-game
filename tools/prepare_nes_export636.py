# SPDX-License-Identifier: MIT
"""Bind the accepted-END/drain exporter and packed SNES ROM to pinned board 613."""
import argparse,json,shutil
from pathlib import Path
from nes_status495 import sha,once

def prepare(base,client,board):
 pins=json.loads((Path(__file__).resolve().parents[1]/'analysis/trial613-package.json').read_text())['inputs']
 board.mkdir(exist_ok=False,parents=True)
 for n,h in pins.items():
  assert sha(base/n)==h,n
  (board/n).parent.mkdir(exist_ok=True,parents=True)
  shutil.copyfile(base/n,board/n)
 changed=set()
 def edit(name,fn):
  f=board/name
  f.write_text(fn(f.read_text()),encoding='utf8',newline='\n')
  changed.add(name)
 # closed is the existing NES-domain END-accepted state; no new completion latch.
 def batch(s):
  s=once(s,'module nes_plan_batch206(','module nes_plan_batch206(\n output wire plan_closed,')
  at=s.index('endmodule')
  return s[:at]+'assign plan_closed=closed&&!nc;\n'+s[at:]
 edit('nes_plan_batch206.sv',batch)
 edit('nes_direct206.sv',lambda s:once(once(s,'output wire reader_drained,retire_commit,','output wire reader_drained,retire_commit,plan_closed,'),'.host_idle(pi),.fault(batch_fault),','.host_idle(pi),.plan_closed(plan_closed),.fault(batch_fault),'))
 def joint(s):
  s=once(s,'reader_drained204;','reader_drained204,plan_closed204;')
  s=once(s,'nes_direct206 direct_path(','nes_direct206 direct_path(.plan_closed(plan_closed204),')
  s=once(s,'.enable(export_permitted204&&!direct_nes_fault204)', '.start_permitted(export_permitted204||reader_drained204),.enable((export_permitted204||(lease204&&plan_closed204))&&!direct_nes_fault204)')
  s=once(s,'.ack_accept(native_ack_data[16])','.ack_accept(native_ack_data[16]&&export_permitted204)')
  return s
 edit('nes_live_joint.sv',joint)
 edit('nes_native_export203.sv',lambda s:once(once(s,'input wire clk,reset,enable,','input wire clk,reset,enable,start_permitted,'),'IDLE:if(enable&&frame_owned)','IDLE:if(enable&&start_permitted&&frame_owned)'))
 rom=(client/'sink165.sfc').read_bytes()
 assert bytes.fromhex((client/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
 shutil.copyfile(client/'sink-program.hex',board/'sink-program.hex')
 changes={n:sha(board/n) for n in pins if sha(board/n)!=pins[n]}
 assert set(changes)==set(changed)|{'sink-program.hex'}
 (board/'inputs636.json').write_text(json.dumps(changes,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('base','client','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.base,a.client,a.out)
