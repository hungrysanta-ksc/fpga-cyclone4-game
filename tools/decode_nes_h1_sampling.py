# SPDX-License-Identifier: MIT
# 044 keeps043 fields; require the paired44 protocol/tag before trusting them.
from pathlib import Path
import argparse,json,re
from decode_nes_h1_qualified import decode as prior_decode

def decode(text):
 fields=dict(line.strip().split('=',1) for line in text.splitlines() if '=' in line)
 if fields.get('candidate')!='NES-H1-SAMPLING-044':return prior_decode(text)
 encoded=fields.get('detail_hex','');assert re.fullmatch('[0-9a-fA-F]{60}',encoded),'Expected30 telemetry bytes'
 raw=bytes.fromhex(encoded);adapted=bytearray(raw);adapted[1]=0x43;adapted[29]=0x43 if raw[29]==0x44 else 0
 converted=dict(fields,candidate='NES-H1-QUALIFIED-043',detail_hex=adapted.hex())
 result=prior_decode(chr(10).join(k+'='+v for k,v in converted.items()))
 result['candidate']=fields['candidate'];result['confirmation']={'identity':raw[0],'protocol':raw[1],'status':raw[2]}
 trusted=fields.get('detail_ok')=='1' and raw[:2]==bytes([0xa5,0x44]);result['snapshot_trusted']=trusted
 if not trusted:
  for k in ('snapshot','snapshot_valid','frontend_capture','aggregate_relation'):result.pop(k,None)
  result['frontend_capture_valid']=False
 return result
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('log',type=Path);a=p.parse_args();print(json.dumps(decode(a.log.read_text(encoding='utf-8-sig')),indent=2))
