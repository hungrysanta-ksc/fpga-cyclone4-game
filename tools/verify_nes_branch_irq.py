"""Directed branch IRQ comparison with a source-derived Mesen cycle model. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,hashlib,json,re,copy

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def reference(c):
 # NesCpu.cpp EndCpuCycle/Exec and NesCpu.h BranchRelative; no RTL state reused.
 previous=False;current=False;cycle=0
 def end():
  nonlocal previous,current,cycle
  previous=current;current=cycle>=c['irq_start_cycle'] and (c['held_until_ack'] or cycle==c['irq_start_cycle']);cycle+=1
 end();end() # opcode and displacement
 if c['taken']:
  current=previous;end() # BranchRelative restores the first poll, then dummy read.
  if c['cycles']==4:current=current or previous;end()
 if previous:return dict(entry=cycle,return_pc=c['next_pc'])
 for n in range(6):
  end();end() # NOP opcode and dummy read
  if previous:return dict(entry=cycle,return_pc=c['next_pc']+n+1)
 return None

def parse(p):
 return [dict(zip(('tick','address','read','data','case','step','irq'),map(int,s.split()))) for s in p.read_text().splitlines()]
def compare(manifest,rows):
 errors=[];results=[]
 for c in manifest['cases']:
  n=c['id'];rs=[r for r in rows if r['case']==n and r['step']>=0];expected=reference(c)
  def fail(reason):errors.append(dict(case=n,reason=reason))
  if not rs or rs[0]['step']!=0 or rs[0]['address']!=c['branch']:fail('missing_branch');continue
  if any(r['step']!=i or r['tick']!=rs[0]['tick']+12*i for i,r in enumerate(rs)):fail('cycle_spacing')
  ack=[r for r in rs if r['address']==2 and not r['read']]
  for r in rs:
   want=int(r['step']>=c['irq_start_cycle'] and (c['held_until_ack'] or r['step']==c['irq_start_cycle']) and (not ack or r['step']<ack[0]['step']))
   if r['irq']!=want:fail('stimulus_waveform');break
  stack=[r for r in rs if r['address']==0x1ff and not r['read']]
  actual=None
  if stack:
   if len(stack)!=1:fail('multiple_interrupts')
   idx=rs.index(stack[0]);triplet=rs[idx:idx+3];vector=rs[idx+3:idx+5]
   if [(r['address'],r['read']) for r in triplet]!=[(0x1ff,0),(0x1fe,0),(0x1fd,0)]:fail('stack_sequence')
   if [(r['address'],r['read'],r['data']) for r in vector]!=[(0xfffe,1,0),(0xffff,1,0xfb)]:fail('irq_vector')
   actual=dict(entry=stack[0]['step']-2,return_pc=triplet[0]['data']*256+triplet[1]['data'])
   if triplet[2]['data']!=c['flags']:fail('stack_status')
   if len(ack)!=1:fail('irq_ack_count')
  elif ack:fail('ack_without_irq')
  if actual!=expected:fail('irq_sampling')
  results.append(dict(id=n,mode=c['mode'],irq_start_cycle=c['irq_start_cycle'],held_until_ack=c['held_until_ack'],expected=expected,actual=actual))
 return dict(passed=not errors,errors=errors,cases=results)

def main():
 p=argparse.ArgumentParser()
 for n in ('rom','rtl','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.rom/'manifest.json').read_text());rows=parse(a.rtl/'branch-irq.tsv');result=compare(m,rows)
 assert len(m['cases'])==52 and sha(a.rom/'branch-irq.nes')==m['sha256']
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ['manifest.json','prg.hex'])
 log=(a.rtl/'simulation.log').read_text();assert 'PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 neg={}
 for kind in ('irq','tick','stack_pc','truncate'):
  mutant=copy.deepcopy(rows)
  if kind=='truncate':mutant=mutant[:len(mutant)//2]
  else:
   if kind=='stack_pc':idx=next(i for i,r in enumerate(mutant) if r['address']==0x1ff and not r['read'] and r['step']>=0)
   else:idx=next(i for i,r in enumerate(mutant) if r['case']==1 and r['step']==0)
   field='data' if kind=='stack_pc' else kind;mutant[idx][field]^=1
  neg[kind]=not compare(m,mutant)['passed']
 result.update(candidate='NES-P2-BRANCH-IRQ-012',negative_tests=neg,rom_sha256=m['sha256'],trace_sha256=sha(a.rtl/'branch-irq.tsv'),verifier_sha256=sha(Path(__file__)),reference='Source-derived Mesen EndCpuCycle/Exec/BranchRelative model, not Mesen runtime or hardware.',scope='52 BEQ branch IRQ scenarios, single-cycle and held input, no RDY/DMA/NMI; IRQ driven on preceding master-clock negedge and sampled at CPU enable edge.')
 result['passed']=result['passed'] and all(neg.values());a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=result['passed'],errors=result['errors'],negative_tests=neg),indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
