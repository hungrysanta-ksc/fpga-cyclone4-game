"""Bounded real DMC/OAM arbitration and explicit timing differences. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,copy,json,re
from verify_nes_oam_dma import rtl,mesen,snapshots,sha
ROM_SHA='935e243c87e77b0944e59bc74aa1c816c04beaea669e60496165be67b6714d91'

def arbitration(p):
 out=[]
 for line in p.read_text().splitlines():
  v=list(map(int,line.split()));assert len(v)==10
  out.append(dict(zip(('tick','case','req','ack','dmcaddr','sprstate','dmcstate','dmadata','buffer','have'),v)))
 return out

def compare(m,rr,aa,mm,oo,ee,mo,me):
 errors=[];results=[];all_phase=set()
 for c in m['cases']:
  n=c['id']
  def fail(reason):errors.append(dict(case=n,reason=reason))
  rs=[r for r in rr if r['case']==n];ar=[r for r in aa if r['case']==n];ms=[r for r in mm if r['case']==n and r['kind'] in ('R','W')]
  # Normalize both timelines to CPU bus cycles without claiming boot/APU phase equivalence.
  norm=[]
  for name,rows in (('RTL',rs),('Mesen',ms)):
   tr=[r for r in rows if r['address']==0x4014 and (not r['read'] if name=='RTL' else r['kind']=='W')]
   end=[r for r in rows if r['address']==32 and (not r['read'] if name=='RTL' else r['kind']=='W')]
   if len(tr)!=1 or len(end)!=1:fail(name+'_completion');norm.append(None);continue
   tr=tr[0];end=end[0];tk='tick' if name=='RTL' else 'cycle';scale=12 if name=='RTL' else 1
   x=[dict(cycle=(r[tk]-tr[tk])//scale,address=r['address'],read=r['read'] if name=='RTL' else int(r['kind']=='R'),data=r['data']) for r in rows if tr[tk]<=r[tk]<=end[tk]]
   norm.append((x,tr,end))
  if not all(norm):continue
  rt,trigger,stop=norm[0];mt,_,_=norm[1]
  if trigger['data']!=c['page']:fail('page')
  rs=[r for r in rs if trigger['tick']<=r['tick']<=stop['tick']]
  armap={r['tick']:r for r in ar}
  if len(armap)!=len(ar) or any(r['tick'] not in armap for r in rs):fail('observer_alignment');continue
  if any(r['tick']!=trigger['tick']+12*i for i,r in enumerate(rs)):fail('bus_spacing')
  expected=[];source=[((i*73)^(i>>1)^(0x5a if c['page']==2 else 0xa7))&255 for i in range(256)]
  for i,v in enumerate(source):expected.extend([(c['page']*256+i,1,v),(0x2004,0,v)])
  summaries=[]
  for name,rows in (('RTL',rt),('Mesen',mt)):
   transfers=[r for r in rows if (r['read'] and c['page']*256<=r['address']<c['page']*256+256) or (not r['read'] and r['address']==0x2004)]
   dmc=[r for r in rows if r['read'] and 0xc000<=r['address']<0xc011]
   if [(r['address'],r['read'],r['data']) for r in transfers]!=expected:fail(name+'_oam_sequence')
   if not dmc or len(transfers)!=512:fail(name+'_overlap_coverage');continue
   if any(r['data']!=((r['address']-0xc000)*37+0x69)&255 for r in dmc):fail(name+'_dmc_data')
   start=transfers[0]['cycle'];finish=transfers[-1]['cycle'];dcycles=[r['cycle'] for r in dmc]
   if start not in (2,3) or any(not start<d<finish for d in dcycles):fail(name+'_contention_window')
   # Each sample takes one OAM read slot followed by one idle put slot.
   cycle=start;at={r['cycle']:r for r in rows}
   for r in transfers:
    while cycle in dcycles:
     idle=at.get(cycle+1)
     if idle is None or (idle['address'],idle['read'])!=(c['resume_pc'],1):fail(name+'_dmc_idle')
     cycle+=2
    if r['cycle']!=cycle:fail(name+'_arbitration_gap');break
    cycle+=1
   length=start+511+2*len(dmc)
   if finish!=length:fail(name+'_halt_length')
   inc=[(r['read'],r['data'],r['cycle']) for r in rows if r['address']==16]
   if inc!=[(1,n-1,length+3),(0,n-1,length+4),(0,n,length+5)]:fail(name+'_cpu_resume_increment')
   for i,v in enumerate(source):
    dest=(c['oam_start']+i)&255;want=v&(0xe3 if dest%4==2 else 255)
    if (oo if name=='RTL' else mo).get((n,dest))!=want:fail(name+'_oam_snapshot');break
   summaries.append(dict(first_oam_cycle=start,last_oam_cycle=finish,dmc_cycles=dcycles,dmc_addresses=[r['address'] for r in dmc],halt_cycles=length))
  if len(summaries)!=2:continue
  length=summaries[0]['halt_cycles'];paused=[r for r in rs if r['pause']]
  if len(paused)!=length or any((r['tick'],r['cpu_address'],r['cpu_read'])!=(trigger['tick']+12*(i+1),c['resume_pc'],1) for i,r in enumerate(paused)):fail('cpu_hold')
  if summaries[0]['first_oam_cycle']!=2+trigger['put']:fail('phase_alignment')
  all_phase.add(trigger['put'])
  for r in rs:
   a=armap[r['tick']];dmc=int(r['read'] and 0xc000<=r['address']<0xc011)
   oam=int((r['read'] and c['page']*256<=r['address']<c['page']*256+256) or (not r['read'] and r['address']==0x2004))
   if r['dma']!=int(bool(dmc or oam)) or a['ack']!=dmc:fail('grant_or_ack');break
   if dmc:
    nxt=armap.get(r['tick']+12)
    if not a['req'] or a['dmcstate']!=1 or a['sprstate']!=3 or a['dmcaddr']!=r['address'] or a['dmadata']!=r['data'] or r['put']!=0:fail('dmc_priority')
    if nxt is None or nxt['buffer']!=r['data'] or not nxt['have']:fail('sample_buffer_latch')
  # Include the initial sample fetched before OAM and require consecutive source bytes.
  pre=[r for r in ar if r['ack'] and r['tick']<=stop['tick']]
  if [r['dmcaddr'] for r in pre]!=list(range(0xc000,0xc000+len(pre))):fail('dmc_source_progress')
  if ee.get(n)!=(n,c['oam_start']) or me.get(n)!=(n,-1):fail('completion_snapshot')
  exact=summaries[0]==summaries[1]
  results.append(dict(id=n,delay_nops=c['delay_nops'],rtl=summaries[0],mesen=summaries[1],runtime_timing_match=exact,oam_bytes=256))
 if len(results)!=8 or all_phase!={0,1}:errors.append(dict(case=0,reason='coverage'))
 if len(oo)!=2048 or len(mo)!=2048 or len(ee)!=8 or len(me)!=8:errors.append(dict(case=0,reason='snapshots'))
 return dict(passed=not errors,errors=errors,cases=results,runtime_timing_match=bool(results) and all(r['runtime_timing_match'] for r in results))

def main():
 p=argparse.ArgumentParser()
 for n in ('rom','rtl','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.rom/'manifest.json').read_text());assert len(m['cases'])==8 and sha(a.rom/'dmc-oam.nes')==m['sha256']==ROM_SHA
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ('manifest.json','prg.hex','chr.hex'))
 log=(a.rtl/'simulation.log').read_text();assert 'PASS NES DIAGNOSTIC' in log and 'period_errors=0 unknown_bus=0' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 cap=json.loads((a.mesen/'capture.json').read_text());assert cap['exit_code']==0 and cap['rom_sha256']==ROM_SHA
 rr=rtl(a.rtl/'dma-bus.tsv');aa=arbitration(a.rtl/'arbitration.tsv');mm=mesen(a.mesen/'dma-bus.tsv');oo,ee=snapshots(a.rtl/'oam.tsv');mo,me=snapshots(a.mesen/'oam.tsv')
 result=compare(m,rr,aa,mm,oo,ee,mo,me);negative={}
 for kind in ('data','address','tick','pause','ack','request','buffer','oam','increment','truncate'):
  rb=copy.deepcopy(rr);ab=copy.deepcopy(aa);ob=oo.copy()
  d=next(r for r in rb if r['case']==1 and r['dma'] and 0xc001<=r['address']<0xc011)
  if kind=='truncate':rb=rb[:len(rb)//2]
  elif kind=='oam':ob[1,0]^=1
  elif kind=='ack':next(r for r in ab if r['tick']==d['tick'])['ack']=0
  elif kind=='request':next(r for r in ab if r['tick']==d['tick'])['req']=0
  elif kind=='buffer':next(r for r in ab if r['tick']==d['tick']+12)['buffer']^=1
  elif kind=='increment':next(r for r in rb if r['case']==1 and r['address']==16 and not r['read'])['data']^=1
  else:d[kind]^=1
  negative[kind]=not compare(m,rb,ab,mm,ob,ee,mo,me)['passed']
 result.update(candidate='NES-P2-DMC-OAM-017',implementation_candidate='NES-P2-RDY-014',negative_tests=negative,rom_sha256=ROM_SHA,verifier_sha256=sha(Path(__file__)),trace_hashes={n:sha(a.rtl/n) for n in ('dma-bus.tsv','arbitration.tsv','oam.tsv')},scope='Bounded arbitration/data/CPU continuation PASS is separate from runtime_timing_match. Actual CPU-programmed DMC rate15, nonlooping17-byte source, eight OAM windows, no forced inputs. Mesen DMC refill timing differs and is unresolved; no full APU/cycle-accuracy/audio/IRQ/DMC boundary or hardware claim.')
 result['passed']=result['passed'] and all(negative.values());a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ('passed','runtime_timing_match','errors','negative_tests')},indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
