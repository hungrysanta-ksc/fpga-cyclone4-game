"""Bounded NMI/IRQ priority checks; source-derived reference, not Mesen runtime. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,copy,hashlib,json,re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse(p):return [dict(zip(('tick','address','read','data','case','step','irq','nmi'),map(int,s.split()))) for s in p.read_text().splitlines()]
def expected(c):
 # All enabled IRQs begin at branch cycle0. NMI-only/masked cases also start at 0.
 # Mesen IRQ() chooses its vector after two dummy reads and two PC stack writes.
 irq=c['irq_enabled'] and not c['irq_masked'];nmi=c['nmi_start_cycle']>=0
 if not irq:return [0xfffa] if nmi else []
 if not nmi:return [0xfffe]
 return [0xfffa,0xfffe] if c['nmi_start_cycle']<=c['cycles']+3 else [0xfffe,0xfffa]

def compare(m,rows):
 errors=[];results=[]
 for c in m['cases']:
  n=c['id'];rs=[r for r in rows if r['case']==n and r['step']>=0]
  def fail(reason):errors.append(dict(case=n,reason=reason))
  if not rs or rs[0]['step']!=0 or rs[0]['address']!=c['branch']:fail('missing_branch');continue
  if any(r['step']!=i or r['tick']!=rs[0]['tick']+12*i for i,r in enumerate(rs)):fail('cycle_spacing')
  ack=[r for r in rs if r['address']==2 and not r['read']]
  for r in rs:
   irq=int(c['irq_enabled'] and (not ack or r['step']<ack[0]['step']))
   nmi=int(c['nmi_start_cycle']>=0 and c['nmi_start_cycle']<=r['step']<c['nmi_start_cycle']+c['nmi_width'])
   if (r['irq'],r['nmi'])!=(irq,nmi):fail('input_waveform');break
  vectors=[];steps=[]
  for i,r in enumerate(rs):
   if r['read'] and r['address'] in [0xfffa,0xfffe]:
    vectors.append(r['address']);steps.append(r['step']);high=0xfc if r['address']==0xfffa else 0xfb
    if i+1>=len(rs) or r['data']!=0 or (rs[i+1]['address'],rs[i+1]['read'],rs[i+1]['data'])!=(r['address']+1,1,high):fail('vector_pair')
  want=expected(c)
  if vectors!=want:fail('priority_or_pending_interrupt')
  stack=[i for i,r in enumerate(rs) if not r['read'] and r['address']==0x1ff]
  if not stack:fail('missing_initial_stack')
  else:
   i=stack[0];triplet=rs[i:i+3]
   if len(triplet)!=3 or [(r['address'],r['read']) for r in triplet]!=[(0x1ff,0),(0x1fe,0),(0x1fd,0)]:fail('initial_stack_sequence')
   elif [r['data'] for r in triplet]!=[c['next_pc']>>8,c['next_pc']&255,c['flags']]:fail('initial_return_pc_or_status')
   if rs[i]['step']!=c['cycles']+2 or not steps or steps[0]!=c['cycles']+5:fail('first_entry_timing')
  for addr,vector in [(3,0xfffe),(4,0xfffa)]:
   writes=[r['data'] for r in rs if r['address']==addr and not r['read']]
   if len(writes)!=2*want.count(vector) or any(writes[i+1]!=(writes[i]+1)&255 for i in range(0,len(writes)-1,2)):fail('handler_count')
  if len(ack)!=want.count(0xfffe):fail('irq_ack_count')
  results.append(dict(id=n,mode=c['mode'],nmi_start_cycle=c['nmi_start_cycle'],irq_enabled=c['irq_enabled'],irq_masked=c['irq_masked'],expected_vectors=want,observed_vectors=vectors,vector_read_cycles=steps))
 return dict(passed=not errors,errors=errors,cases=results)

def main():
 p=argparse.ArgumentParser()
 for n in ['rom','rtl','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.rom/'manifest.json').read_text());assert len(m['cases'])==42 and sha(a.rom/'interrupt-priority.nes')==m['sha256']
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ['manifest.json','prg.hex'])
 log=(a.rtl/'simulation.log').read_text();assert 'PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 rows=parse(a.rtl/'interrupt-priority.tsv');result=compare(m,rows);negative={}
 for kind in ['nmi','irq','vector','return_pc','missing_vector','truncate']:
  mutant=copy.deepcopy(rows)
  if kind=='truncate':mutant=mutant[:len(mutant)//2]
  elif kind in ['nmi','irq']:next(r for r in mutant if r['case']==2 and r['step']==0)[kind]^=1
  elif kind=='return_pc':next(r for r in mutant if r['step']>=0 and r['address']==0x1ff and not r['read'])['data']^=1
  else:
   i=next(i for i,r in enumerate(mutant) if r['step']>=0 and r['address']==0xfffa)
   if kind=='vector':mutant[i]['address']=0xfffe
   else:del mutant[i:i+2]
  negative[kind]=not compare(m,mutant)['passed']
 result.update(candidate='NES-P2-INTERRUPT-PRIORITY-013',negative_tests=negative,rom_sha256=m['sha256'],trace_sha256=sha(a.rtl/'interrupt-priority.tsv'),verifier_sha256=sha(Path(__file__)),reference='Bounded vector-selection oracle derived from local Mesen NesCpu.cpp IRQ()/EndCpuCycle, not Mesen runtime or hardware.',scope='42 BEQ scenarios; two-cycle NMI pulse, held IRQ, fixed CPU-edge phase, ideal memory, first-entry timing/vector order/handler counts. No full interrupt, one-cycle NMI, RDY/DMA, BRK hijack or hardware claim.')
 result['passed']=result['passed'] and all(negative.values());a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=result['passed'],errors=result['errors'],negative_tests=negative),indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
