# SPDX-License-Identifier: MIT
"""Decode H1 exit telemetry. Captured bus address is observational, not causal proof."""
from pathlib import Path
import argparse,json,re
FRONT={0:'aborted_or_address_or_ROMSEL_changed',1:'payload_order_or_not_ready',2:'read_write_conflict',3:'missing_response'}
BUS={0:'none',1:'write_in_wrong_state',2:'invalid_length_or_acquire_response',5:'commit_before_all_bytes_consumed',6:'read_past_length',7:'data_or_commit_in_wrong_state',8:'unsupported_register_write',9:'epoch_sequence_mismatch',10:'invalid_or_missing_response'}
PRODUCER={0:'none',1:'slot_state',2:'length',3:'epoch',4:'sequence',5:'publish_length',6:'write_overflow',15:'timeout_or_invalid_state'}
def decode(text):
 fields=dict(line.strip().split('=',1) for line in text.splitlines() if '=' in line)
 candidate=fields.get('candidate');assert candidate in ('NES-H1-RUNTIME-038','NES-H1-FAULT-039'),'Unexpected candidate'
 status=int(fields['last_status_hex'],16);assert 0<=status<=255
 result={'candidate':candidate,'exit_reason':fields['exit_reason'],'last_status':status,'RUN':bool(status&1),'LOCKED':bool(status&2),'aggregate_fault':bool(status&4),'sequence_exhausted':bool(status&8),'polls':int(fields['polls']),'elapsed_ms_including_configuration':int(fields['elapsed_ticks_10ms'])*10,'base_restored':fields['base_restored']=='1','root_cause_proven':False}
 if candidate.endswith('038'):
  result['detail']='No sub-error telemetry in038';return result
 if fields.get('detail_ok')!='1':result['detail']='Snapshot transactions unavailable';return result
 encoded=fields.get('detail_hex','');assert re.fullmatch('[0-9a-fA-F]{28}',encoded),'Expected14 telemetry bytes'
 b=bytes.fromhex(encoded);result['confirmation']={'identity':b[0],'protocol':b[1],'status':b[2]}
 result['snapshot_trusted']=b[0]==0xa5 and b[1]==0x39
 if not result['snapshot_trusted']:return result
 result['snapshot_valid']=bool(b[3]&128)
 if not result['snapshot_valid']:return result
 result['snapshot']={'flags_hex':f'{b[3]:02x}','bus_error':b[4]&15,'bus_meaning':BUS.get(b[4]&15,'unknown'),'frontend_mask':b[4]>>4,'frontend_flags':[v for bit,v in FRONT.items() if b[4]&(1<<(4+bit))],'producer_error':b[5]&15,'producer_meaning':PRODUCER.get(b[5]&15,'unknown'),'captured_address_hex':f'{int.from_bytes(b[6:9],"little"):06x}','capture_cycles_84MHz':int.from_bytes(b[9:13],'little'),'published_low8':b[13],'read_n':bool(b[3]&2),'write_n':bool(b[3]&1),'romsel_n':bool(b[5]&16)}
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args();print(json.dumps(decode(a.log.read_text(encoding='utf-8-sig')),indent=2))
