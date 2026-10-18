# SPDX-License-Identifier: MIT
"""Actual joint decoder oracle and measured rejection gate, not physical FPS."""
import inspect
import analyze_nes_maskrun247 as base
from analyze_nes_spantrade247 import spans,encode as spanencode,decode as spandecode
from analyze_nes_validation247 import manifest_wire,manifest_decode
from nes_delta231 import once


def main():
 s=inspect.getsource(base.main)
 s=once(s,"('test','host','client','fault','storage','rtl','model','out')", "('test','host','client','fault','budget','baseline','model','out')")
 s=once(s,";storage=read(a.storage/'result.json');rtl=read(a.rtl/'result.json')", ";budget=read(a.budget/'result.json');client=read(a.client/'result.json')")
 s=once(s,"(test,host,fault,storage,rtl)","(test,host,fault,budget)")
 s=once(s,"len(fault['cases'])==12","len(fault['cases'])==23")
 s=once(s," run=a.test/'run';", " run=a.test/'run';assert not (run/'lua-error.txt').exists() or not (run/'lua-error.txt').read_text().strip()\n jointrows=[r for r in csv.DictReader(pin(a.budget/'joint-frames.csv').open()) if r['mode']=='packed_exact64'];assert len(jointrows)==71\n run=a.test/'run';")
 a=s.index("  wire,recs=encode('mask8'");b=s.index('  ranges=[];',a)
 s=s[:a]+'''  rr=spans(stale[bank],0,64);wire=spanencode(rr,want,True);recs=rr;expectedbitmap=bitmap(stale[bank])
  actualwire=[(int.from_bytes(b[10:12],'little'),b[16:]) for _,b in packets[g] if b[0]==9];assert wire==actualwire
  dense=[(0,expectedbitmap[:240]),(240,expectedbitmap[240:])];compressed=manifest_wire(expectedbitmap)
  manifest=compressed if sum(len(b)+19 for at,b in compressed)<294 else dense;op=11 if manifest is compressed else10
  actualmanifest=[(int.from_bytes(b[10:12],'little'),b[16:]) for _,b in packets[g] if b[0] in (10,11)]
  assert manifest==actualmanifest and all(b[0]==op for _,b in packets[g] if b[0] in (10,11))
  if op==11:assert manifest_decode(manifest)==expectedbitmap
  got,received=spandecode(wire,True,banks[bank],len(valid[bank])==2048,dense);assert got==want
  valid[bank].update(received)
  assert len(received)==int(m['map_words']);mapchecks+=4096;banks[bank]=want;last=want;stale[bank].clear()
''' .replace('else10','else 10')+s[b:]
 a=s.index('     group,mask=b[i:i+2]');b=s.index('    assert i==len(b)',a)
 s=s[:a]+'''     at=int.from_bytes(b[i:i+2],'little');n=b[i+2]*2;ranges.append((2,at,n));i+=3+n
'''+s[b:]
 s=once(s,"len(pp['manifest'])==2","len(pp['manifest'])==len(manifest)")
 s=once(s,'manifest_packets=2','manifest_packets=len(manifest)')
 s=once(s,"row['wire_ready4']=int(m['mask8.ready4']);row['charge']=int(m['mask8.charge'])", "row['wire_ready4']=int(jointrows[g-1]['ready4']);row['charge']=int(m['charge']);assert int(jointrows[g-1]['frame'])==frame\n  row['prior_decoder_allowance_ms']=float(jointrows[g-1]['map_and_manifest_decoder_allowance_ms']);row['decoder_allowance_ms']=1000/60-row['wire_ready4']*8/2625-row['mark_ms']-row['coverage_ms'];row['joint_decoder_ms']=row['mask_ms']+row['manifest_ms'];row['decoder_overrun_ms']=row['joint_decoder_ms']-row['decoder_allowance_ms']")
 a=s.index(' resource={}');b=s.index(' result=dict(',a);s=s[:a]+s[b:]
 a=s.index('storage=resource,');b=s.index('warm={k:stats(k)',a);s=s[:a]+"body_bytes=client['body_bytes'],"+s[b:]
 s=once(s,"'Mask and manifest timings include their actual decode/staging/append routines;other packet dispatch/copy,source/ARM/gaps/DMA/display are not all counted.'", "'Measured decoder routines include record admission,receipt,CPU copy,append and per-record/run service. Outer packet admission and final caller service remain excluded;negative gate already fails before them.'")
 s=once(s,"'5KiB RAM geometry inferred at MAP;whole-board placement and M9K/mapper margin remain unverified.'", "'No new MAP/FIT/STA:time gate rejected this decoder before storage or whole-board synthesis.'")
 s=once(s," raw=a.out/'result.json';", ''' assert fault['client_sha256']==sha(pin(a.client/'sink165.sfc')) and fault['normal_sha256']==sha(a.test/'result.json')
 oldtest=read(a.baseline/'result.json');assert oldtest['passed']
 assert budget['input_hashes'][(a.baseline/'result.json').resolve().relative_to(BASE).as_posix()]==sha(a.baseline/'result.json')
 oldpackets={g:[] for g in range(1,72)}
 for f in sorted((a.baseline/'run').glob('req-*.bin')):
  b=pin(f).read_bytes();oldpackets[int.from_bytes(b[8:10],'little')].append(b)
 for old,new in zip(budget['rows'],rows):
  g=new['frame']-904;before=oldpackets[g];after=[b for f,b in packets[g]]
  aa=[b for b in before if b[0] not in (1,3,7)];bb=[b for b in after if b[0] not in (1,3,7)]
  actual_delta=sum(len(b)-16+19 for b in bb)-sum(len(b)-16+19 for b in aa)+20*((len(bb)+3)//4-(len(aa)+3)//4)
  assert new['wire_ready4']==old['wire_ready4']+actual_delta
  assert [int.from_bytes(b[14:16],'little') for b in before if b[0]==7]==[int.from_bytes(b[14:16],'little') for b in after if b[0]==7]
  new.update(actual_nonbulk_data_packets=len(bb),actual_bulk_packets=sum(b[0]==7 for b in after),observed_packet_ready4_delta=actual_delta)
 for f in sorted(a.fault.rglob('*')):
  if f.is_file() and f.suffix in ('.json','.py','.lua','.log'):pin(f)
 # Every span and RLE run retains its service call. Dense fragments have the
 # existing caller service, outside the measured manifest routine.
 detail=list(csv.DictReader(pin(run/'joint-detail247.csv').open()));counts={};pendingservice={};lastreturn={};maxgap={};serviceclocks={}
 for x in detail:
  key=(int(x['generation']),int(x['ordinal']));name=x['event'];t=int(x['clock'])
  counts[key,name]=counts.get((key,name),0)+1
  if name in ('span_service247','manifest_service247'):pendingservice[key,name.replace('_service247','')]=t
  elif name in ('span_serviced247','manifest_serviced247'):
   kind=name.replace('_serviced247','');serviceclocks[kind]=serviceclocks.get(kind,0)+t-pendingservice.pop((key,kind))
   if (key,kind) in lastreturn:maxgap[kind]=max(maxgap.get(kind,0),t-lastreturn[key,kind])
   lastreturn[key,kind]=t
 assert not pendingservice;records=runs=0
 for g,packetlist in packets.items():
  for f,b in packetlist:
   key=(g,int(f.stem.split('-')[1]))
   if b[0]==9:
    at=17;n=0
    while at<len(b):at+=3+2*b[at+2];n+=1
    assert counts[key,'span_record247']==counts[key,'span_service247']==counts[key,'span_serviced247']==n;records+=n
   elif b[0]==11:
    at=17;n=0
    while at<len(b):code=b[at];at+=1+(0 if code&128 else (code&127)+1);n+=1
    assert counts[key,'manifest_run247']==counts[key,'manifest_service247']==counts[key,'manifest_serviced247']==n;runs+=n
 oldrows=budget['rows'];comparison={}
 for old,new in zip(oldrows,rows):
  for k in ('frame','map_words','commands','dma_bytes','charge'):assert old[k]==new[k],(new['frame'],k)
 for k in ('mark_ms','mask_ms','manifest_ms','coverage_ms','conditional_wire_plus_measured_ms'):
  comparison[k]=dict(old_total=sum(r[k] for r in oldrows[2:]),new_total=sum(r[k] for r in rows[2:]),old_max=max(r[k] for r in oldrows[2:]),new_max=max(r[k] for r in rows[2:]))
 result.update(comparison=comparison,span_records=records,rle_runs=runs,service_clocks=serviceclocks,max_within_packet_service_gap_clocks=maxgap,decoder_budget_failures=[r['frame'] for r in rows[2:] if r['decoder_overrun_ms']>0],decision='REJECT_THIS_JOINT_CPU_DECODER_BEFORE_FIT',wire_version='2472',extra_persistent_bytes=2,old_failed_test='jointdecode-test01:audit-rejection.json',outer_dispatch_included=False)
 result['limitations'].append('Per-packet service return gap is not a global STOP latency bound. Rejection is specific to this CPU decoder and conditional serial schedule,not all packed encodings or all overlapping architectures.')
 raw=a.out/'result.json';''')
 s=once(s,"('actual_frames','commands','dma_bytes','warm_multi_vblank','storage')", "('actual_frames','commands','dma_bytes','warm_multi_vblank','comparison','decoder_budget_failures')")
 ns=dict(base.__dict__);ns.update(spans=spans,spanencode=spanencode,spandecode=spandecode,manifest_wire=manifest_wire,manifest_decode=manifest_decode,__file__=__file__,__doc__=__doc__)
 exec(compile(s,'jointdecode247-analysis','exec'),ns);ns['main']()


if __name__=='__main__':main()
