# SPDX-License-Identifier: MIT
"""Whole receiver oracle plus independent pending-span/service accounting."""
import inspect
import analyze_nes_maskfast247 as fast
from nes_delta231 import once


def extra(s):
 s=once(s,"'baseline','out')", "'baseline','profile','bounds','batchstop','out')")
 s=once(s," raw=a.out/'result.json';", ''' profile=read(a.profile/'result.json');bounds=read(a.bounds/'result.json');batchstop=read(a.batchstop/'result.json')
 assert profile['passed'] and bounds['passed'] and bounds['masks']==4 and batchstop['passed'] and len(batchstop['cases'])==2
 for item in (bounds,batchstop):
  assert item['client_sha256']==sha(a.client/'sink165.sfc') and item['normal_sha256']==sha(a.test/'result.json')
 for folder in (a.bounds,a.batchstop):
  pin(folder/'test.py')
  for pattern in ('**/capture.lua','**/mesen.log','**/fault-result.json','**/allmask-result.json','**/allmask-map.bin','**/allmask-receipt.bin'):
   for f in folder.glob(pattern):pin(f)
 details=list(csv.DictReader(pin(run/'batch-detail247.csv').open()));flushes={};starts={};services={};last={};maxgap=0;sumservice=0;warmservices=0;warmflushes=0
 for x in details:
  g=int(x['generation']);ordinal=int(x['ordinal']);t=int(x['clock']);key=(g,ordinal);name=x['event']
  if name=='batch_flush247':flushes.setdefault(key,[]).append((int(x['start']),int(x['finish'])));warmflushes+=int(g>=3)
  elif name=='profile_service247':assert key not in starts;starts[key]=t
  elif name=='profile_serviced247':
   assert key in starts;sumservice+=t-starts.pop(key);services[key]=services.get(key,0)+1;warmservices+=int(g>=3)
   if key in last:maxgap=max(maxgap,t-last[key])
   last[key]=t
 assert not starts
 totalrecords=0
 for g,packetlist in packets.items():
  for f,b in packetlist:
   if b[0]!=9:continue
   key=(g,int(f.stem.split('-')[1]));ranges=[];i=17;records=0
   while i<len(b):
    group,mask=b[i:i+2];i+=2;bits=[k for k in range(8) if mask>>k&1]
    ranges.append((2,group*16+bits[0]*2,2*(bits[-1]-bits[0]+1)));i+=2*len(bits);records+=1
   assert i==len(b) and services[key]==records
   assert flushes[key]==[(at,at+n) for k,at,n in join(ranges)]
   totalrecords+=records
 assert totalrecords==2427 and sum(services.values())==totalrecords
 result.update(profile=profile,span_boundary_test=bounds,pending_stop_cases=batchstop['cases'],records=totalrecords,service_calls=totalrecords,warm_service_calls=warmservices,warm_span_flushes=warmflushes,total_span_flushes=sum(map(len,flushes.values())),max_within_packet_service_return_gap_clocks=maxgap,max_within_packet_service_return_gap_ms=maxgap/21477.270,extra_scratch_bytes=6)
 result['limitations'].append('Service gap is observed between consecutive group service returns within mask packets only,not a global STOP response bound.')
 raw=a.out/'result.json';''')
 return s


def main():
 s=inspect.getsource(fast.main)
 s=once(s,"    ns=dict(base.__dict__);", "    s=extra(s)\n    ns=dict(base.__dict__);")
 ns=dict(fast.__dict__);ns.update(extra=extra,__file__=__file__,__doc__=__doc__)
 exec(compile(s,'maskbatch247-analysis','exec'),ns);ns['main']()


if __name__=='__main__':main()
