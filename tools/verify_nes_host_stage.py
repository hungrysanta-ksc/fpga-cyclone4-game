# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,re
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(run,repo):
 m=json.loads((run/'result.json').read_text());assert m['passed']
 assert m['driver_sha256']==sha(repo/'tools/nes_host_stage.py')
 for name,digest in m['sources'].items():assert sha(repo/name)==digest and sha(run/Path(name).name)==digest
 for name,digest in m['output_hashes'].items():assert sha(run/name)==digest,name
 fixtures=[]
 for name in ('split','sprite','resident'):
  e=m['inputs'][name];b=(repo/e['path']).read_bytes()
  assert len(b)==e['bytes'] and sha(repo/e['path'])==e['sha256'];fixtures.append(b)
 fixtures += [bytes((i*17+f*29)&255 for i in range(n)) for f,n in [(3,3072),(4,17)]]
 result={}
 for label,entry in m['runs'].items():
  log=(run/(label+'.log')).read_text()
  assert not re.search(r'\*\* (?:Fatal|Error):',log)
  assert 'PASS NES HOST STAGE checks=10 readbytes=9477' in log
  stream=(run/(label+'.tsv')).read_text().splitlines();pos=0;times=[]
  for f,b in enumerate(fixtures):
   header=stream[pos].split();pos+=1;assert header[:3]==['P',str(f),str(len(b))]
   times.append(int(header[3]))
   for i,value in enumerate(b):
    assert stream[pos].split()==['B',str(f),str(i),str(value)],(label,f,i);pos+=1
   assert stream[pos]==f'E {f}';pos+=1
  assert pos==len(stream)
  result[label]={'bytes_exact':sum(map(len,fixtures)),'start_to_read_test_ns':times,'cases':entry['cases']}
 return {'candidate':m['candidate'],'audit_pass':True,'total_exact_bytes':sum(v['bytes_exact'] for v in result.values()),'runs':result,'scope':'Logical integrated queue/CDC/stage. P timestamps include status/guard test overhead, not pure fill latency. No physical DMA timing claim.'}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 result=verify(a.run,Path(__file__).resolve().parents[1]);a.out.write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))
