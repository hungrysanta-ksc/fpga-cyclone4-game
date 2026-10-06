# SPDX-License-Identifier: MIT
"""Decode039 legacy evidence or041 pre-update frontend snapshots."""
from pathlib import Path
import argparse,json,re
from decode_nes_h1_fault import decode as legacy_decode
CAUSES=['active_read_address_changed','RD_released_while_response_pending','WR_asserted_while_response_pending','ROMSEL_released_during_active_payload_read','RD_WR_conflict','payload_order_or_not_ready','missing_response']
def decode(text):
 f=dict(line.strip().split('=',1) for line in text.splitlines() if '=' in line)
 if f.get('candidate')!='NES-H1-EDGE-041':return legacy_decode(text)
 encoded=f.get('detail_hex','');assert re.fullmatch('[0-9a-fA-F]{60}',encoded),'Expected30 telemetry bytes'
 b=bytes.fromhex(encoded)
 # Reuse only the unchanged039 aggregate schema; restore actual identity below.
 adapted=dict(f,candidate='NES-H1-FAULT-039',detail_hex=(b[:1]+b'\x39'+b[2:14]).hex())
 result=legacy_decode('\n'.join(k+'='+v for k,v in adapted.items()))
 result['candidate']=f['candidate'];result['snapshot_trusted']=f.get('detail_ok')=='1' and b[:2]==b'\xa5\x41'
 result['confirmation']={'identity':b[0],'protocol':b[1],'status':b[2]}
 if not result['snapshot_trusted']:
  for k in ('snapshot','snapshot_valid'):result.pop(k,None)
  result['frontend_capture_valid']=False;return result
 e=b[14:30];result['frontend_capture_valid']=e[0]!=0 and e[15]==0x41
 if not result['frontend_capture_valid']:return result
 state=e[1];control=e[2]
 result['frontend_capture']={'cause_mask_hex':f'{e[0]:02x}','causes':[name for i,name in enumerate(CAUSES) if e[0]&(1<<i)],'unknown_cause_bits':e[0]&128,'pending':state&3,'rd_sync':(state>>2)&3,'rd_previous':bool(state&16),'local_pending':bool(state&32),'payload_pending':bool(state&64),'output_valid':bool(state&128),'read_n':bool(control&2),'write_n':bool(control&1),'romsel_n':bool(control&4),'data_valid':bool(control&8),'reg_rvalid':bool(control&16),'fault':bool(control&32),'busy':bool(control&64),'ready':bool(control&128),'raw_address_hex':f'{int.from_bytes(e[3:6],"little"):06x}','latched_read_address_hex':f'{int.from_bytes(e[6:9],"little"):06x}','position':int.from_bytes(e[9:11],'little'),'sampled_low_cycles_before_edge':e[11],'previous_sampled_low_cycles':e[12],'sampled_high_cycles_before_edge':e[13],'previous_sampled_high_cycles':e[14],'counter_limit':255,'clock_nominal_MHz':84,'semantics':'First frontend error predicate at the scheduling edge; pre-edge sampled counters, not analog timing. Independent of later aggregate snapshot.'}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args();print(json.dumps(decode(a.log.read_text(encoding='utf-8-sig')),indent=2))
