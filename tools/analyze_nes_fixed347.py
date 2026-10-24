# SPDX-License-Identifier: MIT
"""NES347 source codec evidence + conditional time/whole-area budgets."""
import csv,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_decode280 import records,chunks,golden,encode280
from nes_fixed347 import encode347
from analyze_nes_order343 import plans


def main():
 root=BASE/'probes/nes-fixed347';pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 base=js(ROOT/'analysis/ingress338-verification.json');last=js(ROOT/'analysis/execute346-verification.json')
 for p,h in last['pins'].items():assert sha(Path(p))==h; pins[p]=h
 rr=js(root/'reference01/result.json');cr=js(root/'arm01/result.json');guards=js(root/'guards01/result.json')
 for tag,r in [('reference01',rr),('arm01',cr)]:
  assert r['passed'] and len(r['frames'])==71 and r['reconstructed_bytes']==348610
  for n,k in [('decoder.elf','ELF_sha256'),('nes_decode280.c','C_sha256')]:
   p=root/tag/n;assert sha(p)==r[k];pins[str(p)]=r[k]
  for p,h in r['input_hashes'].items():assert sha(Path(p))==h;pins[p]=h
  for n in ('frames.csv','blocks.csv','size.log','build.log','control.json'):read(root/tag/n)
  stackfiles=list((root/tag).glob('*nes_decode280.su'));assert len(stackfiles)==1;read(stackfiles[0])
 assert guards['passed'] and guards['ELF_sha256']==cr['ELF_sha256'] and len(guards['cases'])==10
 old=bytes(4398);prior=None;rows=[]
 for f,a,b in zip(range(905,976),rr['frames'],cr['frames']):
  g,raw=golden(f)
  ref=records(root/f'reference01/frame{f}.records');candidate=records(root/f'arm01/frame{f}.records')
  assert ref==encode280(old,g,raw,prior,f-904,f-904)
  assert candidate==encode347(old,g,raw,prior,f-904,f-904)
  maps=lambda rs:[r for r in rs[1:] if (r[0]&127)<32]
  assert maps(ref)==maps(candidate) # exact MASK/SHIFT, not just final content
  hybrid=records(BASE/f'probes/nes-hybrid340/arm03/frame{f}.records')
  for p in (root/f'reference01/frame{f}.records',root/f'arm01/frame{f}.records',BASE/f'probes/nes-hybrid340/arm03/frame{f}.records'):read(p)
  wire=lambda rs:sum(map(len,rs))+15*len(chunks(rs))+8
  counts={w:sum(r[0]&128!=0 and 32<=(r[0]&127)<76 and r[1]==w for r in candidate[1:]) for w in (1,2)}
  delta=b['instructions']-a['instructions']
  rows.append(dict(frame=f,reference_wire_B=wire(ref),candidate_wire_B=wire(candidate),hybrid340_wire_B=wire(hybrid),reference_banks=len(chunks(ref)),candidate_banks=len(chunks(candidate)),repeat8=counts[1],repeat16=counts[2],reference_decode_instructions=a['instructions'],candidate_decode_instructions=b['instructions'],decode_delta_instructions=delta,decode_delta_ms_at_CPI1_84MHz=delta/84000,
    serial_wire_decode_proxy_saving_ms=(wire(ref)-wire(candidate))*8/2625000*1000-delta/84000))
  old,prior=g,raw
 assert sum(r['reference_wire_B'] for r in rows)==52113
 assert all(r['candidate_wire_B']<=r['reference_wire_B'] for r in rows)
 assert all(r['decode_delta_instructions']<0 for r in rows)
 warm=rows[2];fixed=base['runs']['fixed01']['rows'][-1];req=fixed['first_request_ms']-fixed['start_ms'];close=6.089722
 current=dict(host_queue_plan=2161+798+459,source=1747,validator_aperture=1159,outside=10950)
 caps=dict(host_queue_plan=2044,source=1100,validator_aperture=1159,outside=10950)
 assert sum(current.values())==17274 and sum(caps.values())==15253
 plan_models=[]
 for f in (905,906,907):
  p=BASE/f'probes/nes-ingress338/window03/actual-plans293-{f}.bin';pins[str(p)]=sha(p);pp=plans(p)
  lengths=[len(x[2]) for x in pp];assert all(3<=n<=32 for n in lengths)
  extra=32*len(pp)-sum(lengths)
  plan_models.append(dict(frame=f,plans=len(pp),wire_plan_payload_B=sum(lengths),normalized_storage_B=32*len(pp),
   extra_normalized_storage_bytes=extra,extra_sequential_read_ms_if_two_clocks_per_byte=extra*2/22000,
   extra_SPI_ms_if_sent_as32byte_wire=extra*8/2625000*1000,
   host_initialization_ms_if32writes_per_plan=32*len(pp)/84000,
   scope='Storage-only expansion in existing16x32B bank; keep E9 wire unchanged. Read/clear arithmetic excludes port stalls, checks and extra execution-state cost.'))
 for n in ('nes_fixed347.py','probe_nes_fixed347.py','check_nes_fixed347.py','analyze_nes_fixed347.py','analyze_nes_order343.py'):read(ROOT/'tools'/n)
 for n in ('nes_core257.sv','nes_mux260.sv','nes_queue260.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_plan_batch206.sv','nes_plan_rom267.sv'):read(BASE/'probes/nes-ingress338/window03'/n)
 result=dict(stage=347,passed=True,selected_RTL=338,selected_ARM=336,new_RTL=False,new_MAP=False,new_full_ARM=False,new_codec_ARM=True,baseline346_pins_rehashed=len(last['pins']),rows=rows,
   wire_totals={n:sum(r[n] for r in rows) for n in ('reference_wire_B','candidate_wire_B','hybrid340_wire_B')},
   candidate_vs340_regressions=[dict(frame=r['frame'],extra_wire_B=r['candidate_wire_B']-r['hybrid340_wire_B']) for r in rows if r['candidate_wire_B']>r['hybrid340_wire_B']],
   decode_delta_range=[min(r['decode_delta_instructions'] for r in rows),max(r['decode_delta_instructions'] for r in rows)],
   decoder=dict(reference_size=rr['size'],candidate_size=cr['size'],reference_stack=rr['stack_observed'],candidate_stack=cr['stack_observed'],guards=guards['cases']),
   warm907_conditional=dict(baseline_fixed_request_ms=req,prior_window_close_ms=close,required_advance_ms=req-close,serial_wire_decode_proxy_saving_ms=warm['serial_wire_decode_proxy_saving_ms'],still_missing_if_only_serial_terms_change_ms=req-close-warm['serial_wire_decode_proxy_saving_ms'],scope='Conditional serial arithmetic, NOT a request-time prediction or bound; no RTL/query/IRQ/SPI polling/staging/VBlank schedule run.'),
   area_current=current,area_caps=caps,required_comb_reduction=2021,host_queue_plan_reduction=1374,source_reduction=647,
   plan_storage_models=plan_models,
   if_source_no_saving=dict(required_host_queue_plan_reduction=2021,host_queue_plan_cap=1397,whole_if_only1374_removed=15900,deficit_if_only1374_removed=492),
   selected_gap_ms=4.022994145333332,selected_comb_deficit=1866,new_measured_fullpath_gain_ms=0,new_measured_comb_gain=0,
   scope='New Python N5v4 encoder + actual isolated M4 decoder71/10guards; map MASK/SHIFT exact. Proposed RTL reuse and joint control budget only. Prior wholeLite/schedules retained, not remeasured. NoFITSTA/fullRUN/physical60fps.',pins=pins)
 (ROOT/'analysis/fixed347-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
 print(json.dumps({k:v for k,v in result.items() if k not in ('rows','pins')},indent=2))
if __name__=='__main__':main()
