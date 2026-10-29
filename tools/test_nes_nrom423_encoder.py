# SPDX-License-Identifier: MIT
"""Exercise BI3 escaping and long-run boundaries, including EOF runs."""
import argparse,json,subprocess,sys
from pathlib import Path
from nes_delta231 import ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
encoder=ROOT/'tools/build_nes_nrom423_bi3.py';cases=[]
def decode(data):
 out=bytearray();i=0
 while i<len(data):
  op=data[i];i+=1
  if op==0x9b:assert i<len(data);out.append(data[i]);i+=1
  elif op in (0x5b,0x77):
   n=3 if op==0x77 else 2;assert i+n<=len(data);v=data[i];count=data[i+1]+(256*data[i+2] if n==3 else 0);assert count;i+=n;out.extend(bytes([v])*count)
  else:out.append(op)
 return bytes(out)
for value in (0,0x5b,0x77,0x9b,0xff):
 for length in (1,2,3,4,255,256,65535,65536):
  payload=bytes([0x12])+bytes([value])*length
  raw=d/('in-%02x-%d'%(value,length));encoded=d/('out-%02x-%d'%(value,length));raw.write_bytes(payload)
  r=subprocess.run([sys.executable,str(encoder),'--input',str(raw),'--out',str(encoded)],capture_output=True,timeout=30,creationflags=subprocess.CREATE_NO_WINDOW)
  assert r.returncode==0,(value,length,r.stderr.decode(errors='replace'))
  assert decode(encoded.read_bytes())==payload,(value,length)
  cases.append({'value':value,'length':length,'encoded_bytes':encoded.stat().st_size})
result={'passed':True,'case_count':len(cases),'cases':cases,'encoder_sha256':sha(encoder),'scope':'exact BI3 encoding and independent decoding; no physical FPGA configuration'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'passed':True,'case_count':len(cases)}))
