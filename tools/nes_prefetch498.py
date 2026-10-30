# SPDX-License-Identifier: MIT
"""498 candidate: next export after accepted END/drain; COMMIT after old retire.
Experimental paired ARM/FPGA source recipe. No hardware selection.
"""
import argparse,json,shutil
from pathlib import Path
from nes_status495 import once,sha
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__)
 for k in ['arm','board','out']:p.add_argument('--'+k,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);patch=a.out/'patch';patch.mkdir();board=a.out/'board';board.mkdir()
 prior=json.loads(Path('analysis/status495-verification.json').read_text());pins=prior['FPGA']
 assert sha(a.arm/'obj-nes-100/firmware.stm')==prior['ARM']['firmware_SHA256']
 # Copy source/project inputs only; preserve prior compiled products.
 for n,h in pins['whole_board_inputs'].items():
  f=a.board/n;assert sha(f)==h,n;dst=board/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,dst)
 changed={}
 def edit(name,fn):
  f=board/name;before=sha(f);f.write_text(fn(f.read_text()),encoding='utf8',newline='\n');changed[name]={'before':before,'after':sha(f)}
 # closed is the existing NES-domain END-accepted state; no new completion latch.
 edit('nes_plan_batch206.sv',lambda s:once(s,'module nes_plan_batch206(','module nes_plan_batch206(\n output wire plan_closed,'))
 f=board/'nes_plan_batch206.sv';s=f.read_text();i=s.index('endmodule');s=s[:i]+'assign plan_closed=closed&&!nc;\n'+s[i:];f.write_text(s,encoding='utf8',newline='\n');changed[f.name]['after']=sha(f)
 edit('nes_direct206.sv',lambda s:once(once(s,'output wire reader_drained,retire_commit,','output wire reader_drained,retire_commit,plan_closed,'),'.host_idle(pi),.fault(batch_fault),','.host_idle(pi),.plan_closed(plan_closed),.fault(batch_fault),'))
 def joint(s):
  s=once(s,'reader_drained204;','reader_drained204,plan_closed204;')
  s=once(s,'nes_direct206 direct_path(','nes_direct206 direct_path(.plan_closed(plan_closed204),')
  s=once(s,'.enable(export_permitted204&&!direct_nes_fault204)', '.start_permitted(export_permitted204||reader_drained204),.enable((export_permitted204||(lease204&&plan_closed204))&&!direct_nes_fault204)')
  s=once(s,'.ack_accept(native_ack_data[16])','.ack_accept(native_ack_data[16]&&export_permitted204)')
  return s
 edit('nes_live_joint.sv',joint)
 edit('nes_native_export203.sv',lambda s:once(once(s,'input wire clk,reset,enable,','input wire clk,reset,enable,start_permitted,'),'IDLE:if(enable&&frame_owned)','IDLE:if(enable&&start_permitted&&frame_owned)'))
 # Preserve every command/STOP/write-drain truth-table row; select the late
 # check_failed input after decoding the two command classes.
 edit('nes_rom_loader.sv',lambda s:once(s,
  '''wire to_write=(phase[SETUP] && !timed_bad && !stop && terminal) ||
  (phase[WRITE] && !drain_step);''',
  '''wire write_blocked=(phase[SETUP] && !fault && !stop && terminal) ||
  (phase[WRITE] && (!terminal || (!fault && stop)));
 wire write_unblocked=(phase[SETUP] && !fault && !stop && terminal && !(load_begin || load_end || start)) ||
  (phase[WRITE] && (!terminal || (!fault && (stop || load_begin || load_end || start))));
 wire to_write=commands_blocked ? write_blocked : write_unblocked;'''))
 s=(a.arm/'nes_native_runtime165.c').read_text()
 insert='''static bool wait498(void *ctx,bool (*check)(void *),unsigned reason,bool progress){
 struct nes_native_runtime165 *s=ctx;
 if(reason==2&&!progress){
  struct nes_native165 *r=s->receiver;
  nes_native165_consumed(r);
  /* Receive only: D3 prepare stays in the next step, after final ACK and EA. */
  if(r->state!=NES_NATIVE165_COMPLETE&&!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
 }
 return nes_cost474_pause(ctx,check,reason,progress);
}
'''
 s=once(s,'static bool resident_plan213(',insert+'static bool resident_plan213(')
 s=once(s,'s->transport.wait=nes_cost474_pause;','s->transport.wait=wait498;')
 s=once(s,'s->sink.last_generation!=r->generation','s->sink.last_generation!=s->video->generation')
 s=once(s,'s->frames++;s->generation=r->generation;','s->frames++;s->generation=s->video->generation;')
 (patch/'nes_native_runtime165.c').write_text(s,encoding='utf8',newline='\n')
 (a.out/'result.json').write_text(json.dumps({'experimental':True,'ARM_base':sha(a.arm/'nes_native_runtime165.c'),'ARM_patch':sha(patch/'nes_native_runtime165.c'),'changed_board':changed,'new_frame_RAM_B':0,'new_completion_FF':0,'common_clock_proven':False},indent=2)+'\n')
