# SPDX-License-Identifier: MIT
"""Audit402 measured alternatives, not acceptance of a failed area/60fps goal."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_joint400 import image,timing
from cost_nes_joint402 import measure

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,default=ROOT/'analysis/joint402-verification.json');a=p.parse_args();d=BASE/'probes/nes-joint402';prior=BASE/'probes/nes-control401/live02';pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 baseline=js(ROOT/'analysis/control401-verification.json');assert baseline['live_clean']and baseline['capture917']['accepted']
 captures=js(d/'capture07/result.json');assert captures['passed'];clog=read(d/'capture07/vsim.log');assert 'PASS CAPTURE402 frames=5 events=38078 reads=6226 STOP=256'in clog
 for n,h in captures['files'].items():assert pin(d/'capture07'/n)==h
 cache=js(d/'cache04/result.json');assert cache['passed'];assert 'PASS CACHE402 requests=977 replies=977 cycles=20424 lateDONE=32'in read(d/'cache04/vsim.log')
 for n,h in cache['files'].items():assert pin(d/'cache04'/n)==h
 separate_cache=js(d/'cache02/result.json');assert separate_cache['passed']
 assert 'PASS CACHE402 requests=972 replies=972 cycles=20322 lateDONE=32'in read(d/'cache02/vsim.log')
 for n,h in separate_cache['files'].items():assert pin(d/'cache02'/n)==h
 assert pin(d/'capture07/nes_native_compact181.sv')==pin(ROOT/'src/fpga/nes_joint402/nes_native_compact181.sv')
 assert pin(d/'cache04/cache.sv')==pin(ROOT/'src/fpga/nes_joint402/cache_shared.sv')
 for run,n in(('host02',19),('host03',20)):
  r=js(d/run/'result.json');assert r['passed']and r['frames']==12 and r['source_bytes']==r['actual_read_events']==25462 and r['max_credit']==2 and len(r['guards'])==n
  assert next(v for v in r['guards']if v['case']==11)['checker']==2 and next(v for v in r['guards']if v['case']==13)['checker']==3
  for name,h in r['RTL'].items():assert pin(d/run/name)==h
 publication=js(d/'header01/result.json');assert publication['audit_passed']
 assert [(v['variant'],v['contract_passed'])for v in publication['cases']]==[('fixed_host',False),('funded_RAM',True)]
 for v in publication['cases']:
  for name,h in v['RTL'].items():assert pin(d/'header01'/v['variant']/name)==h
  assert pin(d/'header01'/v['variant']/'header402_tb.sv')==v['test']
  read(d/'header01'/v['variant']/'vsim.log')
  if v['variant']=='funded_RAM':assert pin(d/'header01/funded_RAM/program398.hex')==pin(d/'host03/program398.hex')
 rows={}
 for label,build,mp,live,unit in(('fixed_host','build05','map04','live02','host02'),('funded_RAM','build07','map07','live04','host03')):
  b=d/build;q=d/mp;l=d/live;m=js(l/'manifest402.json');mr=js(q/'result.json');br=js(b/'manifest402.json');assert mr['passed']and len(m['RTL'])==(33 if label=='fixed_host'else 34)
  assert m['test']==pin(l/'joint266_tb.sv')and m['worker_reference']==pin(prior/'executed-worker367.py')==pin(l/'executed-worker367.py')
  assert image(l/'output.elf')==image(b/'output.elf')==image(prior/'output.elf');pin(l/'output.elf');pin(b/'output.elf')
  assert br['RTL']==m['RTL']==mr['functional_RTL']
  command=next(v for v in read(l/'vlog.log').splitlines()if v.startswith('vlog -sv '));assert set(command.split()[2:])==set(m['RTL'])|{'joint266_tb.sv'}
  for name,h in m['RTL'].items():assert pin(l/name)==h==pin(q/name)==pin(b/name)
  ur=js(d/unit/'result.json')
  for name,h in ur['RTL'].items():assert pin(q/name)==h
  assert pin(q/'nes_native_compact181.sv')==pin(d/'capture07/nes_native_compact181.sv')
  if label=='funded_RAM':assert pin(q/'nes_chr_cache192.sv')==pin(d/'cache04/cache.sv')
  else:assert pin(q/'nes_chr_cache192.sv')==pin(d/'cache02/cache.sv')
  assert pin(q/'sink-program.hex')==pin(BASE/'probes/nes-joint400/map01/sink-program.hex')
  # Preserve every original functional assertion and absolute clock/capture
  # origin. Differences are passive obsolete-VM monitors and cache alias.
  base=read(prior/'joint266_tb.sv');end=base.rindex('endmodule');expected=base[:base.index('integer trace399;')]+base[end:]
  if label=='fixed_host':expected=expected.replace('dut.flow.cpufault',"1'b0")
  alias='planrom.source.cache_path.cache.pending';replacement='(planrom.source.cache_path.cache.state==planrom.source.cache_path.cache.WAIT)'
  actual=read(l/'joint266_tb.sv');assert actual in(expected,expected.replace(alias,replacement))
  assert 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in actual and 'while(romcycle267<5371247)'in actual
  for f in range(905,917):
   model=js(prior/f'model401-{f}.json');assert model==js(l/f'model401-{f}.json')
   for name,h in model['files'].items():assert pin(l/name)==h==pin(prior/name)
  host=read(l/'nes_mux260.sv');program=None
  if label=='fixed_host':
   assert 'nes_byte398'not in host and 'program398'not in host and 'IO_'not in host
   assert 'nes_byte398.sv'not in read(q/'board.qsf')and m['semantic_VM_removed']
   assert pin(l/'nes_mux260.sv')==pin(ROOT/'src/fpga/nes_joint402/nes_mux260.sv')
  else:
   program=js(b/'program-layout402.json');assert program['used']==1979 and program['capacity']==2048 and program['PC_bits']==11 and program['maximum_control_target']==1966
   words=[int(v,16)for v in read(l/'program398.hex').split()];old=[int(v,16)for v in read(prior/'program398.hex').split()]
   assert len(words)==2048 and words==old[:2048]and all(v==(15<<14|255)for v in old[1979:])
   assert all((v&4095)<1979 for v in words[:1979]if v>>14 in(12,13))
   assert pin(l/'program398.hex')==m['program']==pin(q/'program398.hex')==pin(b/'program398.hex')==pin(d/unit/'program398.hex')
   assert ".PC_BITS(11)"in host and '.irq(1\'b0)'in host and 'program398[0:2047]'in host and not m['semantic_VM_removed']
  cost=measure(q);pin(q/'output_files/board.map.rpt');pin(q/'output_files/board.map.summary')
  ram=read(q/'map.log');assert not re.search(r'RAM logic "[^\n]*(?:previous|rank402|metadata402|storage402)" is uninferred',ram)
  report=read(q/'output_files/board.map.rpt');assert 'previous_rtl_0'in report and 'rank402_rtl_0'in report and 'maps_rtl_0'in report
  if label=='funded_RAM':assert 'storage402_rtl_0'in report
  log=read(l/'vsim.log');assert 'PASS REFILL267 frames=12'in log and not re.search(r'^# \*\* Fatal:',log,re.M)
  ev=list(csv.reader(read(l/'joint-events.csv').splitlines()));t=timing(ev)
  finals=re.findall(r'^# FINAL398 t(\d+) f(\d+) phase(\d+) empty(\d) active(\d) tileempty(\d) sealed(\d) view(\d+) data([\da-f]+) mask([\da-f]+) written([\da-f]+) fence([\da-f]+) accepted(\d+) retired(\d+) reserved(\d)',log,re.M)
  assert len(finals)==12 and all(v[2:8]==('4','1','0','1','1','12')and v[8:10]==('5a','f')and v[10]==v[11]and v[12]==v[13]and v[14]=='0'for v in finals)
  rom=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',log);assert rom;rv=list(map(int,rom.groups()));assert rv[0]==rv[1]and rv[2]==0 and rv[3]==rv[4]and rv[5]==0
  assert len(t['captures'])==10
  first=[]
  for f in(907,908):
   x=next(v for v in t['starts']if v['frame']==f);y=next(v for v in baseline['timing']['starts']if v['frame']==f)
   assert x['ROM_cycle']==y['ROM_cycle']+1 and abs(x['ms']-y['ms']-46561/1e9)<1e-6
   first.append(x)
  windows=[];presents={v['frame']:v for v in t['present']}
  for e in ev:
   if e[0]!='display_gate401' or int(e[1])<907:continue
   f,phase,cut,tail,at=map(int,e[1:]);previous=presents[f-1]['VBlank']if f>907 else 15;target=previous+1
   latest=(target*357368+min((cut+1)*1364-1,357368-tail))*46561/1e9
   windows.append(dict(frame=f,previous_actual_VBlank=previous,target_next_VBlank=target,actual_VBlank=presents[f]['VBlank'],gate_ms=at/1e9,latest_gate_ms=latest,additional_advance_ms=max(0,at/1e9-latest),gate_headroom_ms=latest-at/1e9,not_independent_of_prior_skips=True,WCET=False))
  cap=next(v for v in t['captures']if v['frame']==917);material=next(v for v in t['materialized']if v['frame']==916)
  arm=js(l/'arm-result.json');assert arm['passed']and len(arm['frames'])==12
  fills=[int(v[2])/1e9 for v in ev if v[:2]==['hint_fill367','908']];assert fills;close=baseline['hint908_window']['close_ms'];assert min(fills)<close
  rows[label]=dict(build=build,whole_map=mp,live=live,unit=unit,RTL_files=len(m['RTL']),semantic_VM_removed=m['semantic_VM_removed'],source_plan_SPI_bodies_replaced=False,program=program,cost=cost,timing=t,local_display_windows=windows,capture917_margin_ms=cap['ms']-material['ms'],initial_ROM_origins=first,hint908=dict(fill_ms=min(fills),close_ms=close,headroom_ms=close-min(fills)),ROM=dict(zip(('requests','replies','pending','input_requests','input_replies','input_pending'),rv)),ARM=dict(instructions=sum(v['instructions']for v in arm['frames']),SPI_bytes=sum(v['SPI_bytes']for v in arm['frames']),component_stack=arm['stack_observed'],full_RUN=arm['full_RUN'],hardware_cycles=arm['hardware_cycles']),max_warm_completion_interval_ms=max(y['ms']-x['ms']for x,y in zip(t['present'],t['present'][1:])if x['frame']>=907),capture_goal=all(v['accepted']for v in t['captures']),time_goal=not t['presentation_gaps']and all(v['accepted']for v in t['captures']),area_goal=cost['whole']['LE']<=15408 and cost['whole']['comb']<=15253 and cost['control']['comb']<=1172)
 for label,row in rows.items():
  row['publication_contract_passed']=next(v['contract_passed']for v in publication['cases']if v['variant']==label)
  row['production_selected']=False
  row['prototype_rejected']=label=='fixed_host'
  row['cache_unit']='cache02:972pairs'if label=='fixed_host'else'cache04:977pairs,22bit/wrap guards'
  row['timing_scope']='Legal-client positive replay; unpublished-header regression is separately exposed'if label=='fixed_host'else'All 20 unit guards plus unpublished-header gate; modeled native401 service'
 base_cost=measure(BASE/'probes/nes-joint400/map01');alternative=measure(d/'map05')
 for row in rows.values():
  row['whole_delta_vs401']={k:v-base_cost['whole'][k]for k,v in row['cost']['whole'].items()}
  row['initial_source_delay_vs401_NES_clocks']=1
 # A fixed capture origin alone did not preserve the initial source phase:
 # RAM-owned is one clock later. Require a completed, otherwise unchanged
 # reference replay with that exact one-clock admission delay before publish.
 ref=d/'live06';rm=js(ref/'manifest402.json');assert len(rm['RTL'])==34 and not rm['semantic_VM_removed']
 assert image(ref/'output.elf')==image(prior/'output.elf');pin(ref/'output.elf')
 assert pin(ref/'executed-worker367.py')==pin(prior/'executed-worker367.py')==rm['worker_reference']
 for n,h in rm['RTL'].items():assert pin(ref/n)==h==pin(prior/n)==pin(BASE/'probes/nes-joint400/map01'/n)
 assert pin(ref/'program398.hex')==pin(prior/'program398.hex')
 expected=base[:base.index('integer trace399;')]+base[base.rindex('endmodule'):]
 expected=expected.replace(alias,replacement).replace('.source_start_ready(start_ready)','.source_start_ready(start_ready&&admission402)')
 expected=expected.replace('  nes_native_capture365 #'," reg admission402=0;\n always @(posedge clk)if(reset)admission402<=0;else admission402<=owned&&geometry_valid;\n  nes_native_capture365 #")
 assert read(ref/'joint266_tb.sv')==expected and rm['test']==pin(ref/'joint266_tb.sv')
 rlog=read(ref/'vsim.log');assert 'PASS REFILL267 frames=12'in rlog and not re.search(r'^# \*\* Fatal:',rlog,re.M)
 ref_events=list(csv.reader(read(ref/'joint-events.csv').splitlines()));ref_timing=timing(ref_events)
 ref_arm=js(ref/'arm-result.json');assert ref_arm['passed']and len(ref_arm['frames'])==12
 ref_rom=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',rlog);assert ref_rom
 ref_rv=list(map(int,ref_rom.groups()));assert ref_rv[0]==ref_rv[1]and ref_rv[2]==0 and ref_rv[3]==ref_rv[4]and ref_rv[5]==0
 assert len(re.findall(r'^# FINAL398 ',rlog,re.M))==12
 assert len(ref_timing['captures'])==10 and all(v['accepted']for v in ref_timing['captures'])
 for row in rows.values():
  for x in row['initial_ROM_origins']:assert x==next(v for v in ref_timing['starts']if v['frame']==x['frame'])
  row['matched_reference']='402/live06: unchanged401 RTL plus one-clock test admission delay'
  ref_present={v['frame']:v for v in ref_timing['present']}
  row['present_ms_delta_vs_matched_reference']=[dict(frame=v['frame'],delta_ms=v['ms']-ref_present[v['frame']]['ms'])for v in row['timing']['present']]
  row['materialized916_ms_delta_vs_matched_reference']=next(v['ms']for v in row['timing']['materialized']if v['frame']==916)-next(v['ms']for v in ref_timing['materialized']if v['frame']==916)
  row['gate_advance_ms_vs_matched_reference']=[dict(frame=v['frame'],advance_ms=next(int(e[-1])/1e9 for e in ref_events if e[:2]==['display_gate401',str(v['frame'])])-v['gate_ms'])for v in row['local_display_windows']]
 funded=rows['funded_RAM']
 assert funded['timing']==ref_timing and all(v['advance_ms']==0 for v in funded['gate_advance_ms_vs_matched_reference'])
 assert funded['ARM']['instructions']==sum(v['instructions']for v in ref_arm['frames'])and funded['ARM']['SPI_bytes']==sum(v['SPI_bytes']for v in ref_arm['frames'])
 assert list(funded['ROM'].values())==ref_rv
 funded['matched_recorded_schedule_ARM_SPI_ROM_exact']=True
 report=dict(audit_passed=True,scope=__doc__,safety=dict(reads_each=25462,independent_duplicate_fault=2,independent_coverage_fault=3,STOP_freeze_clocks=256,late_cache_DONE_clocks=32,capture_frames=5,capture_events=38078,capture_queries=6226,cache_backing_pairs=977,cache_cycle_exact_reference=True,all8OBJranks=True,raw_rows=True,mixed_planes=True,physical22bit_addresses=True,epoch32_and_generation16_wrap=True),variants=rows,baseline401=baseline['timing'],baseline_whole=base_cost['whole'],separate_RAM_only_area=alternative['whole'],same_native401_service=True,all_phase_WCET=False,physical60fps=False,FIT=False,STA=False,hardware_ready=False,pins=pins)
 report['matched_reference_timing']=ref_timing
 report['publication_counterexample']=publication
 report['matched_reference_cost']=dict(ROM_pairs=ref_rv[0],input_ROM_pairs=ref_rv[3],ARM_instructions=sum(v['instructions']for v in ref_arm['frames']),SPI_bytes=sum(v['SPI_bytes']for v in ref_arm['frames']))
 report['matched_reference_is_production_change']=False
 for q in sorted((ROOT/'tools').glob('*402*.py'))+[ROOT/'src/fpga/nes_joint402'/n for n in('nes_mux260.sv','nes_native_compact181.sv','nes_chr_cache192.sv','cache_shared.sv')]+sorted((ROOT/'tests/nes-joint402').glob('*.sv')):pin(q)
 a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',newline='\n');print(json.dumps({n:{k:v[k]for k in('time_goal','area_goal','capture917_margin_ms','ARM','whole_delta_vs401')}for n,v in rows.items()},ensure_ascii=False))
if __name__=='__main__':main()
