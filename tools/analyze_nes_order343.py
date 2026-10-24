# SPDX-License-Identifier: MIT
"""NES343 footprint/order and SHIFT-preserving wire budgets, not new execution."""
import json,struct,itertools
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_decode280 import golden,encode280,chunks,records
from nes_hybrid340 import runs,REGIONS,encode340

def plans(p):
 b=p.read_bytes();out=[];at=0
 while at<len(b):
  size=int.from_bytes(b[at:at+2],'little');count=b[at+2];at+=3;end=at+size
  for _ in range(count):
   x=b[at:];k=x[0]&3;n=(7 if x[0]==128 else 8 if x[0]==129 else 3) if x[0]&128 else 16+2*x[1].bit_count()
   pos=3 if x[0]&128 else 4;slot=0 if k>=2 else int.from_bytes(x[pos:pos+2],'little');out.append((k,slot,b[at:at+n]));at+=n
  assert at==end
 return out

def bulk(pp):
 out=[];active=None
 for k,slot,data in pp:
  if k==3:
   active=None;continue
  kind=int(k==1);width=32 if kind else 16
  if active is None or active[0]!=kind or slot!=active[1]+active[2]//width or active[2]+width>2048:
   active=[kind,slot,0];out.append(active)
  active[2]+=width
 return out

def footprint(pp):
 out={}
 for k,slot,data in pp:
  if k==3:continue
  kind=int(k==1);width=32 if kind else 16
  for lane in range(width):
   key=(kind,slot*width+lane);assert key not in out
   out[key]=(data,lane) # symbolic bytes of the same complete plan, not pixels
 return out

def main():
 pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 base=js(ROOT/'analysis/ingress338-verification.json');last=js(ROOT/'analysis/frontier342-verification.json');budget=js(ROOT/'analysis/frontier341-verification.json')
 verified={}
 for a in (base,last):
  for p,h in a['pins'].items():assert sha(Path(p))==h,p;verified[p]=h
 d=BASE/'probes/nes-ingress338/window03'
 for n in ('nes_resident211.c','nes_native289.c','nes_plan_batch206.sv','nes_tile_producer260.sv','nes_joint257.sv','nes_mux260.sv','nes_core257.sv'):read(d/n)
 order=[]
 for f in (905,906,907):
  p=d/f'actual-plans293-{f}.bin';pins[str(p)]=sha(p);pp=plans(p);ref=footprint(pp);old=len(bulk(pp));ix=[i for i,x in enumerate(pp) if x[0]==0];variants=[]
  assert pp[0][0]==2 and all(i<next(j for j,x in enumerate(pp) if x[2][0]==0x87) for i in ix)
  for i in ix:
   new=[pp[0],pp[i],*pp[1:i],*pp[i+1:]];assert footprint(new)==ref
   variants.append(dict(slot=pp[i][1],extra_chunks=len(bulk(new))-old))
  # Deliberate duplicate/overlap must fail; don't infer independence from IDs alone.
  try:footprint([pp[0],pp[0]])
  except AssertionError:pass
  else:raise AssertionError('duplicate clear accepted')
  order.append(dict(frame=f,BG_plans=len(ix),baseline_chunks=old,promotions=variants,max_extra_chunks=max(x['extra_chunks'] for x in variants),scope='Recorded complete plans promoted after clear within BG only; actual discovery/ready times unknown. Symbolic destination equality, not RTL/PPU execution.'))
 old=bytes(4398);raw_old=None;rows=[];maximum=0
 for f in range(905,976):
  g,raw=golden(f);cold=f==905;rr=encode340(old,g,raw,raw_old,f-904,f-904)
  p=BASE/f'probes/nes-hybrid340/arm03/frame{f}.records';assert records(p)==rr;read(p)
  maps=[];reconstructed=bytearray(old[:2112]);shift_count=0
  for at in range(0,2112,66):
   u=old[at:at+66];v=g[at:at+66]
   if not cold and u==v:continue
   if not cold and v[:64]==u[2:]:
    maps.append(bytes([128+at//66,1])+v[-2:]);reconstructed[at:at+66]=u[2:]+v[-2:];shift_count+=1
   elif not cold and v[2:]==u[:64]:
    maps.append(bytes([128+at//66,255])+v[:2]);reconstructed[at:at+66]=v[:2]+u[:64];shift_count+=1
   else:
    for b in runs(0,u,v,cold):
     pos=at+int.from_bytes(b[1:3],'little');count=(b[3]&63)+1;mode=b[3]>>6;assert mode in (0,1) and at<=pos<pos+count<=at+66
     maps.append(b[:1]+struct.pack('<H',pos)+b[3:]);reconstructed[pos:pos+count]=b[4:]*count if mode else b[4:]
  assert reconstructed==g[:2112]
  # Length-only ABI alternative: fixed H20/GEO10/END6; checksum values and
  # count fields deliberately not asserted as a new working protocol.
  model=[rr[0],*maps,*[b for b in rr[1:] if not ((b[0]&127)<32)]]
  ref=encode280(old,g,raw,raw_old,f-904,f-904)
  maximum=max(maximum,max(map(len,ref)),max(map(len,rr)))
  wire=lambda x:sum(map(len,x))+15*len(chunks(x))+8
  rows.append(dict(frame=f,reference_wire=wire(ref),hybrid340_wire=wire(rr),SHIFT_run_model_wire=wire(model),SHIFT_rows=shift_count,map_reconstruction=True))
  old=g;raw_old=raw
 ref_total=sum(r['reference_wire'] for r in rows);assert ref_total==52113
 hybrid_total=sum(r['hybrid340_wire'] for r in rows);assert hybrid_total==32236
 regress=[dict(frame=r['frame'],extra_wire=r['SHIFT_run_model_wire']-r['reference_wire']) for r in rows if r['SHIFT_run_model_wire']>r['reference_wire']]
 arm=js(d/'arm907.json');op7={len(bytes.fromhex(x['tx'])) for x in arm['transfers'] if x['tx'].startswith('e107')};assert op7=={23}
 prefix_budgets={}
 for n in (18,25,46):
  prefix_budgets[str(n)]=1.728002081999989-(206*8/2625000*1000+.016-.004190476190476)-(.008+n*8/2625000*1000)
 read(ROOT/'tools/analyze_nes_order343.py')
 out=dict(stage=343,passed=True,selected_RTL=338,selected_ARM=336,new_RTL=False,new_ARM=False,new_MAP=False,new_measured_gain_ms=0,new_measured_comb_gain=0,evidence_rehashed=len(verified),order_models=order,source_rows=rows,reference_wire=ref_total,hybrid340_wire=hybrid_total,SHIFT_run_model_wire=sum(r['SHIFT_run_model_wire'] for r in rows),SHIFT_run_regressions=regress,extra_chunk_E1_wire_B=23,extra_chunk_wire_only_ms=23*8/2625000*1000,max_existing_record_B=maximum,contiguous_record_buffer_budget_B=128,conditional_nonwire_room_ms_by_prefix_B=prefix_budgets,source_model_scope='Size and map reconstruction only; not a new ABI/CRC/ARM/RTL or timing proof. SHIFT retained, MASK replaced by byte runs; nonmap340 bytes retained.',whole_baseline=base['whole'],selected_comb_deficit=1866,whole_comb_cap=15253,net_comb_reduction_required=2021,area_current=budget['area_current'],area_caps=budget['area_caps'],time_budgets=budget['time_budgets'],pins=pins)
 (ROOT/'analysis/order343-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ('pins','source_rows','order_models')},indent=2));print('order summary',[(r['frame'],r['BG_plans'],r['baseline_chunks'],r['max_extra_chunks']) for r in order])
if __name__=='__main__':main()
