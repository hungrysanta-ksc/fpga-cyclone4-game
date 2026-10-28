# SPDX-License-Identifier: MIT
"""Audit the failed capture's source transfers and replay its causal hint."""
import argparse,csv,json
from pathlib import Path
from profile_nes_prepare353 import Profile
from nes_delta231 import sha
from nes_bg295 import unbatch

def main():
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--frame',type=int,default=914)
 p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.run.resolve();frame=a.frame
 paths=[d/'output.elf',d/f'arm{frame}.json',d/'joint-events.csv']
 events=list(csv.reader(paths[2].read_text().splitlines()));start=int(next(x[2] for x in events if x[:2]==['start319',str(frame)]))
 txs=json.loads(paths[1].read_text())['transfers'];parts=[];hint=None
 for t in txs:
  tx=bytes.fromhex(t['tx']);phase=t.get('source_phase367',0)
  if phase or tx[:1] in (b'\xea',b'\xd5'):
   parts.append(dict(phase=phase,command=tx[0] if not phase and tx else None,bytes=len(tx),end_ms=(t['RTL_ns']*1000-start)/1e9,pending_ARM_instructions=t['instructions']))
  if tx[:1]==b'\xea':hint=t
  if tx[:1]==b'\xd5':break
 assert hint is not None
 snapshot=sorted(d.glob(f'causal368-{frame-904}-*.bin'))[0];paths.append(snapshot)
 arm=Profile(d/'output.elf');arm.uc.mem_write(0x20000000,snapshot.read_bytes());assert arm.call('source_hint367',[])==28
 cost=arm.instructions;exclusive=dict(arm.counts);at=arm.call('source_buffer367',[])
 assert bytes(arm.uc.mem_read(at,28)).hex()==hint['tx']
 payload=next(t for t in txs if t.get('source_phase367')==2 and t['tx'])
 wire=int(next(x[2] for x in events if x[:2]==['hint_start367',str(frame)]))
 gap=(wire-payload['RTL_ns']*1000)/1e9
 plans=d/f'actual-plans293-{frame}.bin';paths.append(plans)
 bg=[int.from_bytes(p[5:7],'little') for p in unbatch(plans.read_bytes()) if p[0]==128]
 hint_bytes=bytes.fromhex(hint['tx']);hint_tags=[int.from_bytes(hint_bytes[i:i+2],'little') for i in range(12,26,2)]
 missing=[t for t in bg if t not in hint_tags]
 first_plan=next(t for t in txs if t['tx'].startswith('e9'))
 first_bg=next(x for x in events if x[:3]==['romtile305',str(frame),'0'])
 first_zero=next(x for x in events if x[:3]==['romtile305',str(frame),'2'])
 result=dict(passed=True,new_timing=False,frame=frame,parts=parts,hint_replay_instructions=cost,hint_exclusive=exclusive,
  first_payload_to_hint_wire_ms=gap,hint_pending_instructions=hint['instructions'],
  hint_allocated_CPU_ms=cost/84000,other_pending_instructions=hint['instructions']-cost,
  retrospective_BG=dict(tags=bg,initial_hint_unique=sorted(set(hint_tags)),missing_from_initial_hint=missing,
   first_plan_SPI_end_ms=(first_plan['RTL_ns']*1000-start)/1e9,first_BG_result_ms=(int(first_bg[-1])-start)/1e9,
   first_zero_result_ms=(int(first_zero[-1])-start)/1e9,
   attribution='This interval includes hint ownership and plan/producer acceptance. Source RTL blocks even zero plans while hint_active. Do not attribute the entire interval to a missing BG ROM read without owner-state timing.',
   scope='Post-run analysis only; these future plan tags are never supplied to the hint producer.'),
  ownership='Current source code sets D4 pop only after block286 CRC+semantic decode and optional hint. Physical packet storage release is coupled to foreground processing; separate raw-CRC checked DMA storage credit from semantic completion only with two-buffer ownership and STOP drain proof.',
  unimplemented_budget=dict(existing_wire_bytes=259,extra_RX_bank_bytes=250,descriptor_allowance_bytes=32,total_extra_allowance_bytes=282,implemented=False,credit=0),
  scope='The8917instruction hint replay is not a hardware WCET or an additional time gain. Remaining pending instructions include decoder/caller/IRQ work; they are not all attributed to the decoder.',
  pins={str(p):sha(p) for p in [*paths,Path(__file__).resolve()]})
 assert not a.out.exists();a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps({k:result[k] for k in ('frame','hint_replay_instructions','first_payload_to_hint_wire_ms','hint_pending_instructions','other_pending_instructions')}))
if __name__=='__main__':main()
