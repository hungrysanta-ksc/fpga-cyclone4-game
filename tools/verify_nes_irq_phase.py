"""Compare IRQ bus landmarks without fitting interrupt timing. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,json,hashlib

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def parse_rtl(path):
 out=[]
 for s in path.read_text().splitlines():
  tick,line,dot,counter,cart,cpu,address,read,data,boundary,irq=map(int,s.split())
  out.append(dict(tick=tick,line=line,dot=dot,counter=counter,cart=cart,cpu=cpu,address=address,read=read,data=data,boundary=boundary,irq=irq))
 return out

def parse_mesen(path):
 out=[]
 for s in path.read_text().splitlines():
  kind,frame,line,dot,master,cycle,counter,address,data,pc,unsupported_irq=s.split()
  if kind=='X':continue # Mesen exec callback runs before opcode fetch; not a bus sample.
  out.append(dict(kind=kind,frame=int(frame),line=int(line),dot=int(dot),cycle=int(cycle),counter=int(counter),address=int(address),read=int(kind=='R'),data=int(data)))
 return out

def coord(r):return r['line']*341+r['dot']
def landmarks(rows,counter):
 rows=[r for r in rows if r['counter']==counter]
 stack=next(i for i,r in enumerate(rows) if r['address']==0x1ff and not r['read'])
 end=next(i for i,r in enumerate(rows) if i>stack and r['address']==0xe000 and not r['read'])
 checks=[r for r in rows[stack:end+1] if r['address'] in (0x1ff,0x1fe,0x1fd,0xfffe,0xffff,0x1fc,3,0xe000)]
 assert [(r['address'],r['read']) for r in checks]==[(0x1ff,0),(0x1fe,0),(0x1fd,0),(0xfffe,1),(0xffff,1),(0x1fc,0),(3,1),(3,0),(3,0),(0xe000,0)]
 assert [r['data'] for r in checks]==[0xe1,0x84,0x23,0xe2,0xe1,0,counter-1,counter-1,counter,0]
 before=[r for r in rows[:stack] if r['address']==8 and r['read'] and r['line']==62 and r['dot']<261][-3:]
 assert len(before)==3
 return before,checks

def compare(rtl,mesen):
 errors=[];result=[];cart=[r for r in rtl if r['cart']];cpu={r['tick']:r for r in rtl if r['cpu']};paired=0
 for r in cart:
  other=cpu.get(r['tick']+2)
  if other is None:continue # Narrow capture-window endpoint may omit the other strobe.
  if any(r[k]!=other[k] for k in ('address','read','data','counter')):errors.append('cart_cpu_bus_pair')
  paired+=1
 assert paired>100
 common=sorted({r['counter'] for r in cart}&{r['counter'] for r in mesen});assert common==[3,4,5,6]
 for count in common:
  rb,rl=landmarks(cart,count);mb,ml=landmarks(mesen,count)
  prior_deltas=[coord(m)-coord(r) for r,m in zip(rb,mb)]
  # Phase offset is measured ONLY from pre-IRQ RAM reads. No post-IRQ fitting.
  if len(set(prior_deltas))!=1:errors.append('pre_irq_phase_unstable')
  offset=prior_deltas[0];deltas=[coord(m)-coord(r) for r,m in zip(rl,ml)]
  if any(v!=offset for v in deltas):errors.append('interrupt_added_phase')
  rtl_cycles=[(r['tick']-rl[0]['tick'])/12 for r in rl]
  mesen_cycles=[r['cycle']-ml[0]['cycle'] for r in ml]
  expected=[0,1,2,3,4,7,10,11,12,18]
  if rtl_cycles!=expected or mesen_cycles!=expected:errors.append('irq_bus_cycle_sequence')
  result.append(dict(counter=count,pre_irq_read_dot_pairs=[[r['dot'],m['dot']] for r,m in zip(rb,mb)],pre_irq_phase_offset_ppu_dots=offset,
   landmark_addresses=[r['address'] for r in rl],rtl_landmark_dots=[r['dot'] for r in rl],mesen_landmark_dots=[r['dot'] for r in ml],landmark_differences=deltas,
   rtl_relative_cpu_cycles=rtl_cycles,mesen_relative_cpu_cycles=mesen_cycles,added_irq_path_cpu_cycles=(mesen_cycles[-1]-rtl_cycles[-1])))
 return dict(passed=not errors,errors=errors,paired_cart_cpu_observations=paired,frames=result)

def main():
 p=argparse.ArgumentParser();p.add_argument('--rtl',type=Path,required=True);p.add_argument('--mesen',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 rtl=parse_rtl(a.rtl/'cpu-phase.tsv');mesen=parse_mesen(a.mesen/'cpu-phase.tsv');result=compare(rtl,mesen)
 damaged=[r.copy() for r in mesen];r=next(r for r in damaged if r['counter']==3 and r['address']==0xe000 and not r['read']);r['cycle']+=1;r['dot']+=3
 negative=not compare(rtl,damaged)['passed'];result['one_cpu_cycle_ack_delay_rejected']=negative
 result['passed']=result['passed'] and negative;result['candidate']='NES-P2-IRQ-PHASE-010'
 result['sources']={'verifier_sha256':sha(Path(__file__)),'rtl_cpu_trace_sha256':sha(a.rtl/'cpu-phase.tsv'),'mesen_cpu_trace_sha256':sha(a.mesen/'cpu-phase.tsv')}
 result['conclusion']='The four-dot offset is present in pre-IRQ polling reads and remains unchanged through ten matched IRQ bus landmarks. No added IRQ entry/handler cycle difference in counters3..6. This is not a proof of absolute CPU/PPU phase or hardware IRQ timing.'
 result['limits']=['Mesen exec callbacks are pre-opcode and not bus reads; excluded. cpu.irqFlag is not exposed by this getState mapping (recorded -1), so Mesen IRQ input assertion was not measured.', 'Taken-branch discarded-read address differs: RTL reads branch target E182, Mesen reads sequential E186. Outside compared IRQ landmarks; no full CPU bus conformance claim.', 'Independent boot/alignment and bus callback phase are not calibrated to one external time origin; no arbitrary delay or core change applied.']
 a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n');print(json.dumps(result,indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
