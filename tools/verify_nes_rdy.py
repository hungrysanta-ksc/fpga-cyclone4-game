"""Check paired no-stall/RDY runs and interrupt retention. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,copy,hashlib,json,re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):
 rows=[];ends=[]
 for s in p.read_text().splitlines():
  kind,*words=s.split();v=list(map(int,words))
  if kind=='B':rows.append(dict(zip(('pass','tick','address','read','data','case','step','rdy','irq','nmi'),v)))
  elif kind=='E':ends.append(dict(zip(('pass','case','ram16','ram17','ram18'),v)))
  else:raise ValueError(kind)
 return rows,ends

def compare(m,rows,ends):
 errors=[];results=[]
 def bus(rs):return [(r['address'],r['read'],r['data']) for r in rs]
 for c in m['cases']:
  n=c['id'];runs=[]
  def fail(reason):errors.append(dict(case=n,reason=reason))
  for run in (0,1):
   rs=[r for r in rows if r['pass']==run and r['case']==n and r['step']>=0]
   stop=next((i for i,r in enumerate(rs) if r['address']==32 and not r['read']),None)
   if stop is None:fail('case_incomplete');runs.append([]);continue
   rs=rs[:stop+1];runs.append(rs)
   if rs[0]['address']!=c['anchor'] or any(r['step']!=i or r['tick']!=rs[0]['tick']+12*i for i,r in enumerate(rs)):fail('cycle_spacing')
   snap=[r for r in ends if r['pass']==run and r['case']==n]
   if len(snap)!=1 or [snap[0][k] for k in ('ram16','ram17','ram18')]!=[90,90,8]:fail('architectural_memory')
   ack=[r for r in rs if r['address']==2 and not r['read']]
   for i,r in enumerate(rs):
    low=run==1 and c['stall_cycle']<=i<c['stall_cycle']+3
    irq=int(run==1 and c['interrupt_mode'] in (1,3) and i>=c['stall_cycle']+1 and (not ack or i<ack[0]['step']))
    nmi=int(run==1 and c['interrupt_mode'] in (2,3) and i==c['stall_cycle']+1)
    if (r['rdy'],r['irq'],r['nmi'])!=(int(not low),irq,nmi):fail('input_waveform');break
    if not r['rdy'] and r['read'] and (i+1==len(rs) or bus([r])!=bus([rs[i+1]])):fail('read_hold_bus')
   vectors=[r['address'] for r in rs if r['read'] and r['address'] in (0xfffa,0xfffe)]
   counts={0xfffe:int(run==1 and c['interrupt_mode'] in (1,3)),0xfffa:int(run==1 and c['interrupt_mode'] in (2,3))}
   if any(vectors.count(v)!=count for v,count in counts.items()):fail('interrupt_retention')
   if len(ack)!=counts[0xfffe]:fail('irq_ack_count')
   for address,vec,hi in [(3,0xfffe,0xfb),(4,0xfffa,0xfc)]:
    writes=[r['data'] for r in rs if r['address']==address and not r['read']]
    if len(writes)!=2*counts[vec] or any(writes[i+1]!=(writes[i]+1)&255 for i in range(0,len(writes)-1,2)):fail('handler_count')
    for i,r in enumerate(rs):
     if r['read'] and r['address']==vec:
      if i+1==len(rs) or r['data']!=0 or (rs[i+1]['address'],rs[i+1]['read'],rs[i+1]['data'])!=(vec+1,1,hi):fail('vector_pair')
  if not all(runs):continue
  stalled=sum(not r['rdy'] and r['read'] for r in runs[1]);writes=sum(not r['rdy'] and not r['read'] for r in runs[1])
  if stalled+writes!=3:fail('rdy_window_length')
  if c['interrupt_mode']==0:
   resumed=[r for r in runs[1] if r['rdy'] or not r['read']]
   if bus(resumed)!=bus(runs[0]):fail('resume_bus_equivalence')
  results.append(dict(id=n,shape=c['shape'],stall_cycle=c['stall_cycle'],interrupt_mode=c['interrupt_mode'],blocked_read_cycles=stalled,unblocked_write_cycles=writes,baseline_cycles=len(runs[0]),stimulus_cycles=len(runs[1]),observed_vectors=[r['address'] for r in runs[1] if r['read'] and r['address'] in (0xfffa,0xfffe)]))
 if len(ends)!=112:errors.append(dict(case=0,reason='completion_count'))
 return dict(passed=not errors,errors=errors,cases=results)

def main():
 p=argparse.ArgumentParser()
 for n in ('rom','rtl','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.rom/'manifest.json').read_text());assert len(m['cases'])==56 and sha(a.rom/'rdy.nes')==m['sha256']
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ('manifest.json','prg.hex'))
 log=(a.rtl/'simulation.log').read_text();assert 'PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 rows,ends=parse(a.rtl/'rdy.tsv');result=compare(m,rows,ends);negative={}
 for kind in ('address','data','rdy','nmi','vector','snapshot','truncate'):
  rr=copy.deepcopy(rows);ee=copy.deepcopy(ends)
  if kind=='snapshot':ee[56]['ram18']^=1
  elif kind=='truncate':rr=rr[:len(rr)//2]
  elif kind=='vector':next(r for r in rr if r['pass']==1 and r['step']>=0 and r['address']==0xfffa)['address']=0xfffe
  elif kind=='nmi':next(r for r in rr if r['pass']==1 and r['nmi'])['nmi']=0
  else:next(r for r in rr if r['pass']==1 and not r['rdy'] and r['read'])[kind]^=1
  negative[kind]=not compare(m,rr,ee)['passed']
 result.update(candidate='NES-P2-RDY-014',negative_tests=negative,rom_sha256=m['sha256'],trace_sha256=sha(a.rtl/'rdy.tsv'),verifier_sha256=sha(Path(__file__)),scope='56 paired original scenarios: 3-cycle RDY low at read/write/BEQ positions; held IRQ and one-cycle NMI during pause. Ideal external memory, no actual DMA/bus arbitration/MMIO/hardware or exact IRQ/NMI service latency claim.')
 result['passed']=result['passed'] and all(negative.values());a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=result['passed'],errors=result['errors'],negative_tests=negative),indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
