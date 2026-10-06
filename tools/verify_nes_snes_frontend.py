# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,re,statistics
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify(run,resource,repo):
 m=json.loads((run/'result.json').read_text());assert m['passed'] and m['queue_equivalence_passed']
 assert m['driver_sha256']==sha(repo/'tools/nes_snes_frontend.py')
 for name,digest in m['sources'].items():assert sha(repo/name)==digest and sha(run/Path(name).name)==digest,name
 for name,digest in m['output_hashes'].items():assert sha(run/name)==digest,name
 eq=(run/'queue_equivalence.log').read_text()
 assert 'PASS QUEUE RAM EQUIVALENCE' in eq and 'checks=14 writes=10492 reads=10460' in eq
 assert not re.search(r'\*\* (?:Fatal|Error):',eq)
 fixtures=[]
 for name in ('split','sprite','resident'):
  e=m['inputs'][name];b=(repo/e['path']).read_bytes()
  assert len(b)==e['bytes'] and sha(repo/e['path'])==e['sha256'];fixtures.append(b)
 cases=[(0,1,fixtures[0]),(1,2,fixtures[1]),(2,3,fixtures[2]),(4,1,bytes((i*17+4*29)&255 for i in range(17))),(3,1,bytes([87]))]
 runs={}
 for name,meta in m['runs'].items():
  log=(run/(name+'.log')).read_text()
  assert 'PASS NES SNES FRONTEND checks=13 readbytes=6406' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
  lines=(run/(name+'.tsv')).read_text().splitlines();pos=0;latency=[]
  for fixture,seq,b in cases:
   assert lines[pos].split()==['P',str(fixture),str(len(b))];pos+=1
   for i,value in enumerate(b):
    row=lines[pos].split();pos+=1
    assert row[:4]==['B',str(seq),str(i),str(value)]
    latency.append(float(row[4]))
  assert pos==len(lines) and len(latency)==6406
  assert max(latency)<=5*meta['host_period_ns']+1
  runs[name]={'exact_bytes':len(latency),'payload_latency_ns':{'min':min(latency),'median':statistics.median(latency),'max':max(latency)},'host_period_ns':meta['host_period_ns'],'queue_period_ns':meta['queue_period_ns'],'cases':meta['cases']}
 rm=json.loads((resource/'result.json').read_text());assert rm['phases']=={'map':0,'fit':0}
 assert rm['driver_sha256']==sha(repo/'tools/nes_transport_resource.py')
 for name,digest in rm['sources'].items():
  assert sha(resource/name)==digest==sha(run/name)==sha(repo/'src/nes'/name)
 rpt=(resource/'output_files/transport.fit.rpt').read_text(encoding='latin-1')
 summary=(resource/'output_files/transport.fit.summary').read_text();assert 'Successful' in summary
 def extract(pattern):
  hit=re.search(pattern,rpt);assert hit,pattern;return int(hit[1].replace(',',''))
 area={'LE':extract(r'; Total logic elements\s*; ([\d,]+) /'),'LAB':extract(r'; Total LABs:  partially or completely used\s*; ([\d,]+) /'),'M9K':extract(r'; M9Ks\s*; ([\d,]+) /'),'memory_bits':extract(r'; Total memory bits\s*; ([\d,]+) /')}
 assert area=={'LE':1139,'LAB':111,'M9K':12,'memory_bits':73728}
 return {'candidate':m['candidate'],'audit_pass':True,'queue_equivalence_cases':14,'queue_reference_reads':10460,'total_exact_pin_bytes':sum(v['exact_bytes'] for v in runs.values()),'runs':runs,'resource':area,'resource_limitations':'Virtual133pins,2unassignedclockpins;no STA/IO signoff/boardPLL/loader/NES core. Arithmetic881+111=992LAB exceeds963 but separate-fit sums do not predict joint packing. Full integration must be measured.','hardware_H0':'User positive report and sampled5.27s video show readable030 pages1/2/3 and wrap; no reset/longrun/FPGA evidence'}
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('run','resource','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();result=verify(a.run,a.resource,Path(__file__).resolve().parents[1])
 a.out.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
