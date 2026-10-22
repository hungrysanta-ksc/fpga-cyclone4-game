# SPDX-License-Identifier: MIT
"""Reconcile measured whole costs and exhaustively check proposed page addressing; no new RTL."""
import csv,json,hashlib
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha

def main():
 pins={}
 def pin(p):pins[str(p)]=sha(p);return p
 def js(p):return json.loads(pin(p).read_text())
 base=js(ROOT/'analysis/arch300-verification.json');prev=js(ROOT/'analysis/joint303-verification.json');timing=js(ROOT/'analysis/joint298-verification.json')
 for p,h in prev['input_hashes'].items():assert sha(Path(p))==h
 for n in ('nes_mux260.sv','nes_validator278.sv','nes_joint257.sv'):pin(BASE/'probes/nes-arch300/test03'/n)
 pin(BASE/'probes/nes-joint303/window01/joint266_tb.sv')
 rows=[]
 for tag,mode in [('test01','normal'),('window01','restricted')]:
  d=BASE/'probes/nes-joint303'/tag;events=list(csv.reader(pin(d/'joint-events.csv').open()));last=[0,0,0]
  for f in (905,906,907):
   es=[e for e in events if int(e[1])==f];p=next(x for x in prev[mode] if x['frame']==f)
   arm=js(d/f'arm{f}.json');wait=next(e for e in es if e[0]=='romwait267');counts=list(map(int,wait[2:]));delta=[x-y for x,y in zip(counts,last)];last=counts
   parser=sum(int(e[3]) for e in es if e[0]=='parser')/1e9
   receipt=sum(int(e[3]) for e in es if e[0]=='receipt')/1e9
   first={}
   for kind in ('0','1'):
    for typ in ('plan293','tile293'):
     ts=[int(e[4])/1e9 for e in es if e[0]==typ and e[2]==kind]
     first[typ+'_'+kind+'_absolute_ms']=min(ts) if ts else None
   rows.append(dict(mode=mode,frame=f,total_ms=p['total_ms'],source_ms=p['source_ms'],ARM_instructions=p['ARM_instructions'],ARM_CPI1_ms=p['ARM_instructions']/84000,SPI_bytes=p['SPI_bytes'],parser_service_sum_ms=parser,typed_receipt_sum_ms=receipt,slot_wait_cycles=delta[1],slot_wait_occupancy_ms=delta[1]*45.454/1e6,core_priority_blocks=delta[2],E2=p['E2'],timer_fallbacks=p['timer_fallbacks'],**first))
 # Existing physical layout, alternate address generation only. Every valid bit,
 # both banks, manifest byte, hash byte and final-display byte is compared.
 n=0
 def equal(old,page,offset):
  nonlocal n
  assert 0<=page<4 and 0<=offset<256;assert old==(page<<8)|offset;n+=1
 for bit in range(1328):
  equal(512+(bit>>3),2,bit>>3)
  for bank in (0,1):equal(bank*256+(bit>>3),bank,bit>>3)
 for bit in range(2048):equal(768+(bit>>3),3,bit>>3)
 for bank in (0,1):
  for c in range(422):
   old=bank*256+c if c<144 else 512+c if c<166 else 768+c-166
   phase,local=(0,c) if c<166 else (1,c-166)
   equal(old,(bank if local<144 else 2) if phase==0 else 3,local)
  for idx in range(32):equal(448+bank*32+idx,1,192+bank*32+idx)
 display=[683,699,700,694,695,696,697,698,712,713,714,715]
 for a in display:equal(a,2,a-512)
 assert set(range(716,748)).isdisjoint(set(range(512,678))|set(range(680,716))|set(range(768,1024)))
 guards=[]
 for domain,first,end,want in [(1024,0,1024,True),(1024,0,1025,False),(1328,1312,1328,True),(1328,1327,1329,False),(2048,0,2048,True),(2048,2048,2049,False),(2048,7,7,False),(2048,8,7,False)]:
  ok=0<=first<end<=domain;assert ok==want;guards.append([domain,first,end,ok])
 fields=dict(op=4,section=3,codec=2,encoded_length=9,byte_first=16,byte_end=17,token=32,remaining=6,packet_cursor=9,receipt_first=12,receipt_end=12,domain=3)
 assert sum(fields.values())==125
 caps=dict(host_decode_execution=700,independent_validator=900,queue_and_SPI=450,plan=325,glue=54)
 assert sum(caps.values())==2429 and sum(caps.values())+128==base['fixed_budget']==2557
 for row in rows:
  for kind in ('0','1'):
   a=row['plan293_'+kind+'_absolute_ms'];z=row['tile293_'+kind+'_absolute_ms'];row['first_plan_to_tile_'+kind+'_ms']=z-a if a is not None and z is not None else None
 warm=next(x for x in rows if x['mode']=='restricted' and x['frame']==907)
 naive=warm['parser_service_sum_ms']+warm['typed_receipt_sum_ms']+31275/84000
 r=dict(passed=True,stage=304,implementation=False,new_ARM=False,new_RTL=False,new_MAP=False,FIT=False,STA=False,physical=False,source_reference=300,time_reference=298,measured_baseline_MAP=base['whole_MAP'],rejected303_MAP=prev['whole_MAP'],baseline_regions=base['regions'],fixed_boundary=4827,outside=12851,hard_boundary_cap=2557,proposed_caps=caps,policy_reserve_comb=128,estimated_next_comb=None,estimated_next_ms=None,host_only_zero_still_short=2270-base['regions']['host'],host_validator_only_cap=2557-(4827-3413),record_fields=fields,record_payload_bits=125,record_cap_bits=160,old_logical_storage_upper_bits=189,record_extra_RAM_bits=0,record_storage_choice='Replace active registers; RAM716..747 rejected for hot descriptor due to port contention',address_equalities=n,address_guards=guards,schedules=rows,warm_tail_instructions=31275,fixed_schedule_parser_receipt_tail_optimistic_ms=naive,fixed_schedule_remaining_ms=warm['total_ms']-1000/60-naive,required_net_gain_ms=timing['restricted'][-1]['total_ms']-1000/60,policy_time_margin_ms=.25,required_net_gain_with_margin_ms=timing['restricted'][-1]['total_ms']-1000/60+.25,limitations=['Address oracle is not synthesized RTL or timing','Parser service starts at OSETUP, excludes earlier header and ordinary DMA; not pure decode time','Parser/receipt/ARM/ROM occupancies overlap; optimistic subtraction is not a predicted speedup or a global impossibility bound','ROM window phase can amplify or erase an earlier supply change','Per-module caps are design requirements, not predicted Quartus cost','Full 71 live schedules, full ARM RUN, full65816 and physical60fps remain open'],input_hashes=pins,script_sha256=sha(Path(__file__)))
 (ROOT/'analysis/budget304-verification.json').write_text(json.dumps(r,indent=2)+'\n',newline='\n')
 with (ROOT/'analysis/budget304-costs.csv').open('w',newline='') as fp:
  w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
 print(json.dumps({k:r[k] for k in ('address_equalities','host_only_zero_still_short','host_validator_only_cap','fixed_schedule_parser_receipt_tail_optimistic_ms','fixed_schedule_remaining_ms','required_net_gain_with_margin_ms')},indent=2))
if __name__=='__main__':main()
