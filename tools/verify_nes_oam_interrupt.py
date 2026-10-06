"""Actual OAM DMA interrupt retention: bounded bus oracle. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,copy,json,re
from verify_nes_oam_dma import rtl,sha
ROM_SHA='802b7e50f3de706827027d34f135216f61fb54107d7664b884ee2d5800b778d9'

def pins(p):
 out=[]
 for line in p.read_text().splitlines():
  v=list(map(int,line.split()));assert len(v)==10
  out.append(dict(zip(('tick','case','step','irq','nmi','pause','address','read','data','put'),v)))
 return out

def snapshots(p):
 out={};ends={};counts={}
 for line in p.read_text().splitlines():
  k,n,a,b=line.split();n,a,b=map(int,(n,a,b))
  dest,key,value=(out,(n,a),b) if k=='O' else ((ends,n,(a,b)) if k=='E' else (counts,n,(a,b)))
  assert k in ('O','E','I') and key not in dest
  dest[key]=value
 return out,ends,counts

def compare(m,rr,pp,oo,ee,cc):
 errors=[];results=[];groups={}
 for c in m['cases']:
  n=c['id'];mode=c['interrupt_mode'];arrival=c['arrival_cycle']
  def fail(reason):errors.append(dict(case=n,reason=reason))
  rs=[r for r in rr if r['case']==n];ps=[r for r in pp if r['case']==n and r['step']>=0]
  ts=[i for i,r in enumerate(rs) if r['address']==0x4014 and not r['read']]
  if len(ts)!=1 or not ps:fail('trigger_count');continue
  rs=rs[ts[0]:]
  # RAM case ID changes after the next setup starts: stop at this case's completion write.
  for rows in (rs,ps):
   end=next((i for i,r in enumerate(rows) if r['address']==32 and not r['read']),None)
   if end is not None:del rows[end+1:]
  tr=rs[0];length=514 if tr['put'] else 513
  if tr['data']!=c['page']:fail('source_page')
  if any(r['tick']!=tr['tick']+12*i for i,r in enumerate(rs)):fail('bus_spacing')
  if len(rs)<length+2:fail('truncated_dma');continue
  paused=[r for r in rs if r['pause']];dma=[r for r in rs if r['dma']]
  if len(paused)!=length or any((r['tick'],r['cpu_address'],r['cpu_read'])!=(tr['tick']+12*(i+1),c['resume_pc'],1) for i,r in enumerate(paused)):fail('cpu_hold')
  if any(r['tick']!=tr['tick']+2+12*i or r['step']!=i or r['pause']!=int(1<=i<=length) for i,r in enumerate(ps)):fail('pin_alignment')
  stop=[r for r in ps if r['address']==32 and not r['read']]
  if len(stop)!=1:fail('completion_bus')
  ack=[r for r in ps if r['address']==2 and not r['read']]
  want_irq=int(mode in (1,3));want_nmi=int(mode in (2,3))
  if len(ack)!=want_irq:fail('irq_ack_count')
  for r in ps:
   want=(int(want_irq and r['step']>=arrival and (not ack or r['step']<ack[0]['step'])),int(want_nmi and r['step']==arrival))
   if (r['irq'],r['nmi'])!=want:fail('input_waveform');break
  if arrival>length or not any(r['step']==arrival and r['pause'] for r in ps):fail('arrival_not_during_dma')
  resume=rs[length+1]
  if (resume['address'],resume['read'],resume['pause'],resume['dma'])!=(c['resume_pc'],1,0,0):fail('cpu_resume')
  # Independent deterministic source pattern from the original diagnostic contract.
  source=[((i*73)^(i>>1)^(0x5a if c['page']==2 else 0xa7))&255 for i in range(256)]
  expected=[]
  for i,v in enumerate(source):expected.extend([(c['page']*256+i,1,v),(0x2004,0,v)])
  if [(r['address'],r['read'],r['data']) for r in dma]!=expected:fail('dma_data_address')
  if any(r['tick']!=tr['tick']+12*(length-511+i) or r['put']!=i%2 for i,r in enumerate(dma)):fail('dma_timing')
  for i,v in enumerate(source):
   dest=(c['oam_start']+i)&255;v&=0xe3 if dest%4==2 else 255
   if oo.get((n,dest))!=v:fail('oam_snapshot');break
  if ee.get(n)!=(n,c['oam_start']):fail('completion_snapshot')
  if cc.get(n)!=(want_irq,want_nmi):fail('handler_snapshot')
  inc=[(r['read'],r['data'],(r['tick']-tr['tick'])//12) for r in rs if r['address']==16]
  if inc!=[(1,n-1,length+3),(0,n-1,length+4),(0,n,length+5)]:fail('resume_increment')
  vectors=[r['address'] for r in rs if r['read'] and r['address'] in (0xfffa,0xfffe)]
  expected_vectors=([0xfffa] if want_nmi else [])+([0xfffe] if want_irq else [])
  if vectors!=expected_vectors:fail('interrupt_order_count')
  for i,r in enumerate(rs):
   if r['read'] and r['address'] in (0xfffa,0xfffe):
    high=0xfc if r['address']==0xfffa else 0xfb
    if i<=length or i+1==len(rs) or r['data']!=0 or (rs[i+1]['address'],rs[i+1]['read'],rs[i+1]['data'])!=(r['address']+1,1,high):fail('vector_pair_or_early_service')
  # INC completes once, then interrupt entry saves its following instruction PC.
  pc=c['resume_pc']+2;count=want_irq+want_nmi
  writes=[(r['address'],r['data']) for r in rs if not r['read'] and 0x100<=r['address']<0x200]
  if writes!=[(0x1ff,pc>>8),(0x1fe,pc&255),(0x1fd,0x20),(0x1fc,c['page'])]*count:fail('stack_return_pc_status_a')
  pops=[(r['address'],r['data']) for r in rs if r['read'] and r['address'] in (0x1fd,0x1fe,0x1ff)]
  if pops!=[(0x1fd,0x20),(0x1fe,pc&255),(0x1ff,pc>>8)]*count:fail('rti_stack_restore')
  for a,num in ((3,want_irq),(4,want_nmi)):
   if [r['data'] for r in rs if r['address']==a and not r['read']]!=[0,1]*num:fail('handler_increment')
  groups.setdefault((arrival,mode),set()).add(length)
  results.append(dict(id=n,arrival_cycle=arrival,interrupt_mode=mode,paused_cpu_cycles=length,observed_vectors=vectors,observed_vector_cycles=[(r['tick']-tr['tick'])//12 for r in rs if r['read'] and r['address'] in (0xfffa,0xfffe)],dma_pairs=len(dma)//2,oam_bytes=256))
 if len(groups)!=12 or any(v!={513,514} for v in groups.values()):errors.append(dict(case=0,reason='phase_coverage'))
 if len(oo)!=6144 or len(ee)!=24 or len(cc)!=24:errors.append(dict(case=0,reason='snapshot_count'))
 return dict(passed=not errors,errors=errors,cases=results)

def main():
 p=argparse.ArgumentParser()
 for n in ('rom','rtl','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.rom/'manifest.json').read_text());assert len(m['cases'])==24 and sha(a.rom/'oam-interrupt.nes')==m['sha256']==ROM_SHA
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ('manifest.json','prg.hex','chr.hex'))
 log=(a.rtl/'simulation.log').read_text();assert 'PASS NES DIAGNOSTIC' in log and 'period_errors=0 unknown_bus=0' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 rr=rtl(a.rtl/'dma-bus.tsv');pp=pins(a.rtl/'pins.tsv');oo,ee,cc=snapshots(a.rtl/'oam.tsv');result=compare(m,rr,pp,oo,ee,cc);negative={}
 for kind in ('dma_data','dma_address','tick','pause','oam','irq','nmi','vector','stack','handler','increment','truncate'):
  rb=copy.deepcopy(rr);pb=copy.deepcopy(pp);ob=oo.copy();cb=cc.copy()
  if kind=='truncate':rb=rb[:len(rb)//2]
  elif kind=='oam':ob[1,0]^=1
  elif kind=='handler':cb[3]=(0,0)
  elif kind in ('irq','nmi'):next(r for r in pb if r[kind])[kind]=0
  elif kind=='vector':next(r for r in rb if r['read'] and r['address']==0xfffa)['address']=0xfffe
  elif kind=='stack':next(r for r in rb if not r['read'] and r['address']==0x1fe)['data']^=1
  elif kind=='increment':next(r for r in rb if not r['read'] and r['address']==16 and r['case']==1)['data']^=1
  else:next(r for r in rb if r['dma'])[kind.removeprefix('dma_')]^=1
  negative[kind]=not compare(m,rb,pb,ob,ee,cb)['passed']
 result.update(candidate='NES-P2-OAM-INTERRUPT-016',implementation_candidate='NES-P2-RDY-014',negative_tests=negative,rom_sha256=m['sha256'],trace_hashes={n:sha(a.rtl/n) for n in ('dma-bus.tsv','pins.tsv','oam.tsv')},verifier_sha256=sha(Path(__file__)),scope='24 actual OAM DMA cases; synthetic held IRQ / one CPU-cycle NMI / both / none at cycles 1,256,512 after trigger. Both 513/514 halts per mode/arrival. Bounded transfer, retention, stack and continuation oracle. IRQ/NMI inputs forced, DMA/RDY not forced. No Mesen runtime injected-pin comparison, hardware validation or independently calibrated exact interrupt latency claim. DMC and rendering disabled; ideal memory.')
 result['passed']=result['passed'] and all(negative.values());a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=result['passed'],errors=result['errors'],negative_tests=negative),indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
