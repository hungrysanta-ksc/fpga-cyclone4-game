"""Actual OAM DMA bus, snapshot and Mesen comparison. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,copy,hashlib,json,re

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def rtl(p):return [dict(zip(('tick','address','read','data','case','cpu_address','cpu_read','pause','dma','put'),map(int,l.split()))) for l in p.read_text().splitlines()]
def mesen(p):
 out=[]
 for l in p.read_text().splitlines():
  k,*v=l.split();out.append(dict(kind=k,**dict(zip(('cycle','address','data','case'),map(int,v)))))
 return out

def snapshots(p):
 out={};end={}
 for l in p.read_text().splitlines():
  k,n,a,v=l.split();n=int(n);a=int(a);v=int(v)
  if k=='E':assert n not in end;end[n]=(a,v)
  else:assert (n,a) not in out;out[n,a]=v
 return out,end

def compare(manifest,prg,rr,mr,ro,re,mo,me):
 errors=[];results=[];groups={}
 for c in manifest['cases']:
  n=c['id']
  def fail(reason):errors.append(dict(case=n,reason=reason))
  rs=[r for r in rr if r['case']==n];ms=[r for r in mr if r['case']==n];triggers=[i for i,r in enumerate(rs) if not r['read'] and r['address']==0x4014];mts=[r for r in ms if r['kind']=='W' and r['address']==0x4014]
  if len(triggers)!=1 or len(mts)!=1:fail('trigger_count');continue
  i=triggers[0];trigger=rs[i];mt=mts[0];rs=rs[i:];ms=[r for r in ms if r['cycle']>=mt['cycle']]
  if trigger['data']!=c['page'] or mt['data']!=c['page']:fail('source_page')
  dma=[r for r in rs if r['dma']];paused=[r for r in rs if r['pause']];length=514 if trigger['put'] else 513
  if len(dma)!=512:fail('dma_transfer_count')
  if len(paused)!=length or any(r['cpu_address']!=c['resume_pc'] or r['cpu_read']!=1 for r in paused):fail('cpu_hold')
  if any(r['tick']!=trigger['tick']+12*(j+1) for j,r in enumerate(paused)):fail('pause_contiguous')
  if len(rs)<=length+1 or (rs[length+1]['address'],rs[length+1]['cpu_address'],rs[length+1]['read'],rs[length+1]['pause'],rs[length+1]['dma'])!=(c['resume_pc'],c['resume_pc'],1,0,0):fail('cpu_resume')
  source=prg[0x6000+(c['page']-2)*256:0x6100+(c['page']-2)*256];expected=[]
  for off,data in enumerate(source):expected.extend([(c['page']*256+off,1,data),(0x2004,0,data)])
  if [(r['address'],r['read'],r['data']) for r in dma]!=expected:fail('dma_address_data_sequence')
  if any((r['tick']-trigger['tick'])!=12*(length-511+j) or r['put']!=j%2 for j,r in enumerate(dma)):fail('dma_cycle_alignment')
  md=[r for r in ms if (r['kind']=='R' and c['page']*256<=r['address']<c['page']*256+256) or (r['kind']=='W' and r['address']==0x2004)]
  if [(r['address'],int(r['kind']=='R'),r['data']) for r in md]!=expected:fail('mesen_transfer_sequence')
  if len(md)!=len(dma) or any(m['cycle']-mt['cycle']!=(r['tick']-trigger['tick'])//12 for r,m in zip(dma,md)):fail('mesen_relative_cycles')
  for source_index,value in enumerate(source):
   dest=(c['oam_start']+source_index)&255;want=value&(0xe3 if dest%4==2 else 255)
   if ro.get((n,dest))!=want or mo.get((n,dest))!=want:fail('oam_snapshot');break
  if re.get(n)!=(n,c['oam_start']) or n not in me or me[n][0]!=n:fail('completion_or_oam_wrap')
  rb=[(r['read'],r['data'],(r['tick']-trigger['tick'])//12) for r in rs if r['address']==16]
  mb=[(int(r['kind']=='R'),r['data'],r['cycle']-mt['cycle']) for r in ms if r['address']==16 and r['kind'] in ('R','W')]
  want=[(1,n-1,length+3),(0,n-1,length+4),(0,n,length+5)]
  if rb!=want or mb!=want:fail('post_dma_cpu_increment')
  groups.setdefault((c['page'],c['oam_start']),set()).add(length)
  results.append(dict(id=n,page=c['page'],oam_start=c['oam_start'],trigger_put_phase=trigger['put'],paused_cpu_cycles=len(paused),dma_read_write_pairs=len(dma)//2,first_dma_cycle=length-511,last_dma_cycle=length,oam_bytes=256))
 if len(ro)!=4096 or len(mo)!=4096 or len(re)!=16 or len(me)!=16:errors.append(dict(case=0,reason='snapshot_count'))
 if len(groups)!=8 or any(v!={513,514} for v in groups.values()):errors.append(dict(case=0,reason='phase_coverage'))
 return dict(passed=not errors,errors=errors,cases=results)

def main():
 p=argparse.ArgumentParser()
 for n in ('rom','rtl','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();m=json.loads((a.rom/'manifest.json').read_text());assert len(m['cases'])==16 and sha(a.rom/'oam-dma.nes')==m['sha256'];prg=(a.rom/'oam-dma.nes').read_bytes()[16:32784]
 assert all(sha(a.rom/n)==sha(a.rtl/n) for n in ['prg.hex','manifest.json'])
 log=(a.rtl/'simulation.log').read_text();assert 'PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
 cap=json.loads((a.mesen/'capture.json').read_text());assert cap['exit_code']==0 and cap['rom_sha256']==m['sha256']
 rr=rtl(a.rtl/'dma-bus.tsv');mr=mesen(a.mesen/'dma-bus.tsv');ro,rend=snapshots(a.rtl/'oam.tsv');mo,me=snapshots(a.mesen/'oam.tsv');result=compare(m,prg,rr,mr,ro,rend,mo,me);negative={}
 for kind in ('data','address','tick','pause','oam','missing_transfer','truncate'):
  mutant=copy.deepcopy(rr);om=ro.copy()
  if kind=='oam':om[1,0]^=1
  elif kind=='truncate':mutant=mutant[:len(mutant)//2]
  else:
   i=next(i for i,r in enumerate(mutant) if r['dma'])
   if kind=='missing_transfer':del mutant[i]
   else:mutant[i][kind]^=1
  negative[kind]=not compare(m,prg,mutant,mr,om,rend,mo,me)['passed']
 result.update(candidate='NES-P2-OAM-DMA-015',negative_tests=negative,rom_sha256=m['sha256'],rtl_trace_sha256=sha(a.rtl/'dma-bus.tsv'),mesen_trace_sha256=sha(a.mesen/'dma-bus.tsv'),verifier_sha256=sha(Path(__file__)),scope='16 actual $4014 OAM DMA cases, rendering/APU DMC/interrupts disabled, ideal memory; 2 RAM pages, 4 OAM start addresses, both alignment phases. Full DMA bus and OAM snapshots compared with actual Mesen runtime. No DMC contention, rendering-time writes, arbitrary RMW triggers, external stalls, fit or hardware claim.')
 result['passed']=result['passed'] and all(negative.values());a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(dict(passed=result['passed'],errors=result['errors'],negative_tests=negative,halt_lengths=sorted(set(c['paused_cpu_cycles'] for c in result['cases']))),indent=2));raise SystemExit(0 if result['passed'] else 1)
if __name__=='__main__':main()
