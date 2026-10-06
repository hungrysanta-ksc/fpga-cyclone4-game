# SPDX-License-Identifier: MIT
"""Protocol43 uses sampled decision addresses and one registered error event."""
from pathlib import Path
import argparse,json,re
from decode_nes_h1_edge import decode as earlier_decode,CAUSES

def decode(text):
 f=dict(line.strip().split('=',1) for line in text.splitlines() if '=' in line)
 if f.get('candidate')!='NES-H1-QUALIFIED-043':return earlier_decode(text)
 encoded=f.get('detail_hex','');assert re.fullmatch('[0-9a-fA-F]{60}',encoded),'Expected30 telemetry bytes'
 b=bytes.fromhex(encoded);e=b[14:30]
 adapted=bytearray(b);adapted[1]=0x41;adapted[29]=0x41 if e[15]==0x43 else 0
 d=earlier_decode('\n'.join(k+'='+v for k,v in dict(f,candidate='NES-H1-EDGE-041',detail_hex=adapted.hex()).items()))
 d['candidate']=f['candidate'];d['confirmation']={'identity':b[0],'protocol':b[1],'status':b[2]}
 d['snapshot_trusted']=f.get('detail_ok')=='1' and b[:2]==b'\xa5\x43'
 d.pop('frontend_capture',None)
 if not d['snapshot_trusted']:
  for key in ('snapshot','snapshot_valid'):d.pop(key,None)
 d['frontend_capture_valid']=d['snapshot_trusted'] and e[0]!=0 and e[15]==0x43
 if not d['frontend_capture_valid']:return d
 state=e[1];control=e[2];mask=(bool(e[0]&15)*1)|(bool(e[0]&32)*2)|(bool(e[0]&16)*4)|(bool(e[0]&64)*8)
 d['frontend_capture']={'cause_mask_hex':f'{e[0]:02x}','causes':[n for i,n in enumerate(CAUSES) if e[0]&(1<<i)],'unknown_cause_bits':e[0]&128,
 'pending':state&3,'rd_previous':bool(state&4),'read_seen':bool(state&8),'read_issued':bool(state&16),'local_pending':bool(state&32),'payload_pending':bool(state&64),'output_valid':bool(state&128),
 'sampled_read_n':bool(control&2),'sampled_write_n':bool(control&1),'sampled_romsel_n':bool(control&4),'data_valid':bool(control&8),'reg_rvalid':bool(control&16),'fault':bool(control&32),'busy':bool(control&64),'ready':bool(control&128),
 'decision_address_hex':f'{int.from_bytes(e[3:6],"little"):06x}','latched_read_address_hex':f'{int.from_bytes(e[6:9],"little"):06x}',
 'previous_address_sample_hex':f'{int.from_bytes(e[12:15],"little"):06x}','position':int.from_bytes(e[9:11],'little'),
 'event_frontend_mask':e[11]&15,'response_valid_at_RD_sample':bool(e[11]&16),'cause_implied_frontend_mask':mask,'event_mask_consistent':(e[11]&15)==mask,
 'semantics':'Pre-update sampled context of the single registered event shared by sticky error and first capture; not raw pad levels or physical pulse measurements.'}
 aggregate=d.get('snapshot',{}).get('frontend_mask',0)
 d['aggregate_relation']='includes_first_frontend_event' if aggregate&mask==mask else 'prior_nonfrontend_fault' if aggregate==0 else 'different_error_bits'
 return d
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args();print(json.dumps(decode(a.log.read_text(encoding='utf-8-sig')),indent=2))
