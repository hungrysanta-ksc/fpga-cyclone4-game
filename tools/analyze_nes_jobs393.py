# SPDX-License-Identifier: MIT
"""393 replacement boundary and ABI budgets;no new RTL/fullpath timing claim."""
import argparse,csv,hashlib,json,re,shutil,struct,subprocess
from pathlib import Path
from probe_nes_arm264 import ARM,plans
from nes_delta231 import ROOT,BASE,sha
from analyze_nes_source368 import whole

def source_bits(pp,expected):
 bits=bytearray(256);seen=set()
 for p in pp:
  if p[:2]!=bytes([9,2]):continue
  assert p[16]==3;at=17
  while at<len(p):
   first=int.from_bytes(p[at:at+2],'little');n=p[at+2]*2;at+=3;assert p[at:at+n]==expected[first:first+n]
   for w in range(first//2,(first+n)//2):assert w not in seen;seen.add(w);bits[w//8]|=1<<(w%8)
   at+=n
  assert at==len(p)
 return bytes(bits),seen

def packets393(sizes):
 #10B frame envelope+CRC/prefix3. Complete records are packed in source order.
 # A large HOST record has HEAD_ONLY, then ordered DATA(offset16,payload).
 wire=0;packets=0;used=0;count=0
 def flush():
  nonlocal wire,packets,used,count
  if used:wire+=13+used;packets+=1;used=count=0
 for data,align in sizes:
  cost=12+data
  if cost>246:
   flush();wire+=25;packets+=1
   while data:
    take=min(data,(244//align)*align);assert take>0;wire+=15+take;packets+=1;data-=take
  else:
   if used+cost>246 or count==16:flush()
   used+=cost;count+=1
 flush();return dict(wire=wire,packets=packets)

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve();d.mkdir(parents=True,exist_ok=False);pins={}
 def pin(p):pins[p.relative_to(BASE).as_posix()if p.is_relative_to(BASE)else'component/'+p.name]=sha(p)
 shutil.copyfile(ROOT/'tools/nes_jobs393.c',d/'jobs.c')
 (d/'stub.c').write_text('#include <stdint.h>\nuint8_t bits393[256],map393[4096],jobs393[3072],payload393[4096];uint32_t info393[8];\n',newline='\n')
 (d/'unit.ld').write_text('SECTIONS { . = 0x08000000; .text : { *(.text*) *(.rodata*) } . = 0x20000000; .data : { *(.data*) } .bss : { *(.bss*) } }\n',newline='\n')
 tool=BASE/'.tools/arm-gnu-toolchain-13.3.rel1/arm-gnu-toolchain-13.3.rel1-mingw-w64-i686-arm-none-eabi/bin'
 for name,args,label in [('gcc',['-std=c11','-Os','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-mthumb','-mcpu=cortex-m4','-mfloat-abi=soft','-fstack-usage','-fno-builtin','-nostdlib','-Wl,-T,unit.ld','-Wl,-e,build_jobs393','jobs.c','stub.c','-o','unit.elf'],'build'),('size',['unit.elf'],'size'),('objdump',['-dr','unit.elf'],'disassembly')]:
  r=subprocess.run([str(tool/f'arm-none-eabi-{name}.exe'),*args],cwd=d,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW);(d/f'{label}.log').write_bytes(r.stdout);assert r.returncode==0,r.stdout.decode(errors='replace')
 oracle,groups=plans();rows=[];fixture_digest=hashlib.sha256();fixture_count=0
 for f in sorted(oracle.glob('req-*.bin'))+sorted(oracle.glob('expected-*.bin')):
  fixture_digest.update(f.name.encode()+b'\0'+f.read_bytes());fixture_count+=1
 for serial,pp in groups.items():
  f=serial+904;expected=(oracle/f'expected-{serial}.bin').read_bytes();bits,required=source_bits(pp,expected);outputs=[]
  if 907<=f<=916:assert bits==(BASE/f'probes/nes-plan390/arm01/map{f}.bin').read_bytes()
  for mode in (0,1,2):
   arm=ARM(d/'unit.elf',None);arm.symbols.update(io259=0x0800f000,trace259=0x0800f004);arm.uc.mem_write(arm.symbols['bits393'],bits);arm.uc.mem_write(arm.symbols['map393'],expected[:4096]);ok=arm.call('build_jobs393',[mode,(serial-1)&1]);info=list(struct.unpack('<8I',arm.uc.mem_read(arm.symbols['info393'],32)));assert ok
   jobs=bytes(arm.uc.mem_read(arm.symbols['jobs393'],12*info[0]));data=bytes(arm.uc.mem_read(arm.symbols['payload393'],info[3]));seen=set();order=[];sizes=[];at=0
   for j in range(info[0]):
    x=jobs[j*12:j*12+12];ppu,store,n=struct.unpack('<HHH',x[:6]);first=int.from_bytes(x[10:12],'little');stride=32 if x[8]==0x81 else 1
    assert store==0xc000+at and ppu==(((serial-1)&1)*0x2000+0x3000)|first
    assert x[6]==4|(32 if stride==32 else 0)and x[7]==0x7e and x[9]==2 and n>0 and n%2==0
    for i in range(n//2):
     w=first+i*stride;assert w in required and w not in seen;seen.add(w);order.append(w);assert data[at:at+2]==expected[2*w:2*w+2];at+=2
    sizes.append((n,2))
   assert seen==required and at==2*len(required)==len(data)
   wire=packets393(sizes);outputs.append(dict(mode=mode,chosen=info[2],jobs=info[0],row_runs=info[4],column_runs=info[5],bytes=info[3],instructions=arm.instructions,stack=0x2003f000-arm.low_sp,map_only_budget_clocks=info[6],old_monotonic_checker_compatible=order==sorted(order),wire=wire))
   if mode==2:(d/f'jobs{f}.bin').write_bytes(jobs);(d/f'payload{f}.bin').write_bytes(data)
  bounds=set()
  for c in range(64):
   rr=[(w//32)%32 for w in required if (w&31)+(w//1024)*32==c]
   if rr:bounds.update((c//32)*1024+r*32+(c%32)for r in range(min(rr),max(rr)+1))
  rows.append(dict(frame=f,required_words=len(required),bounds_extra_words=len(bounds-required),policies=outputs))
 # Empty and bounds domains cannot be inferred from one scrolling frame.
 directed=[]
 for name,required in [('empty',set()),('edge',{0,31,32,1023,1024,2047}),('alternating',set(range(0,2048,2))),('columnholes',{r*32+7 for r in(0,3,7,11,19,31)}|{1024+r*32+9 for r in(0,2,31)}),('checkerboard_reject',{w for w in range(2048)if ((w//32)+(w%32))%2}),('invalid_bank',set())]:
  bits=bytearray(256)
  for w in required:bits[w//8]|=1<<(w%8)
  arm=ARM(d/'unit.elf',None);arm.symbols.update(io259=0x0800f000,trace259=0x0800f004);arm.uc.mem_write(arm.symbols['bits393'],bytes(bits));arm.uc.mem_write(arm.symbols['jobs393'],b'\xa5'*3072);ok=arm.call('build_jobs393',[2,3 if name=='invalid_bank'else 0]);info=list(struct.unpack('<8I',arm.uc.mem_read(arm.symbols['info393'],32)));reject=name in('checkerboard_reject','invalid_bank');assert bool(ok)!=reject
  if reject:assert info[0]==0 and bytes(arm.uc.mem_read(arm.symbols['jobs393'],3072))==b'\xa5'*3072
  else:assert info[1]==len(required)
  directed.append(dict(name=name,jobs=info[0],row_runs=info[4],column_runs=info[5],empty_valid=not required and not reject,rejected_before_job_publication=reject))
 current=BASE/'probes/nes-plan390/map01';reference=BASE/'probes/nes-context375/map03';names=['nes_transport257:transport','nes_spi270:spi_front270','nes_output260:flow','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_queue260:queue','nes_host_context375:context375','nes_tile_producer260:tiles'];cost={};retained={};ffs={}
 for line in(current/'output_files/board.map.rpt').read_text(errors='replace').splitlines():
  c=line.split(';');name=c[1].strip().strip('|')if len(c)>3 else''
  if name in names+['nes_core257:encoder','nes_validator278:validator']and '('in c[2]:
   v=int(re.search(r'\((\d+)\)',c[2])[1]);(cost if name in names else retained)[name]=v
   if name in names:ffs[name]=int(re.search(r'\((\d+)\)',c[3])[1])
 assert len(cost)==8 and sum(cost.values())==3878 and sum(retained.values())==2374
 actual=whole(current);old=whole(reference);required=actual['comb']-15408+155;outside=actual['comb']-sum(cost.values())-sum(retained.values());assert required==2491 and outside==11492
 wire_rows=[]
 for f in range(907,917):
  q=BASE/('probes/nes-plan390/joint04'if f<=908 else'probes/nes-present378/control02');tr=json.loads((q/f'arm{f}.json').read_text())['transfers'];packets=[bytes.fromhex(t['tx'])for t in tr if t['tx'].startswith('e1')];old_map=sum(len(p)for p in packets if p[1]in(12,14));plan=next(x for x in json.loads((BASE/'probes/nes-plan390/arm01/result.json').read_text())['cases']if x['frame']==f)['bytes']+19
  p=next(r['policies'][2]for r in rows if r['frame']==f);actual_meta=f<=908;nonmap=[];ref_jobs=0;tile_count=0;other=0
  for pkt in packets:
   op,section=pkt[1],pkt[2]
   if op==7:tile_count+=1
   elif op in (2,4,5,8)and section in(3,4,5):nonmap.append((len(pkt)-19,16 if section==3 else 2));ref_jobs|=1 if section==3 else 2 if section==4 else 0
   elif op not in(12,14)and not(op==2 and section==6):other+=1
  # Conservative live issue order: tile HEADs separate;ordinarys preserve
  # encoded bytes. Reference jobs cost12B and share only proven free capacity
  # in an offline packet packing calculation,not a timing/credit assertion.
  refs=ref_jobs.bit_count();new_nonmap=packets393(nonmap+[(0,1)]*refs);old_nonmap=sum(len(pkt)for pkt in packets if pkt[1]in(2,4,5,8)and pkt[2]in(3,4,5));old_tiles=sum(len(pkt)for pkt in packets if pkt[1]==7)
  old_selected=old_map+plan+old_tiles+old_nonmap+sum(len(pkt)for pkt in packets if pkt[1]not in(7,12,14,2,4,5,8));new_selected=p['wire']['wire']+25*tile_count+new_nonmap['wire']+sum(len(pkt)-6 for pkt in packets if pkt[1]not in(7,12,14,2,4,5,8))
  no_batch=sum(packets393([s])['wire']for s in nonmap)+25*refs;safe=new_selected+no_batch-new_nonmap['wire']
  native=BASE/f'probes/nes-plan390/native01/{f}';ev=[list(map(int,x))for x in csv.reader((native/'events.csv').read_text().splitlines())];tm=list(csv.DictReader((native/'timings.csv').read_text().splitlines()));regs={};old_map_jobs=old_map_bytes=0
  for mark in [int(t['clock'])for t in tm if t['phase']=='PPU_trigger']:
   for e in ev:
    if e[4]>mark:break
    if e[1]==1:regs[e[2]]=e[3]
   address=regs.get(0x2116,0)+256*regs.get(0x2117,0);baseppu=0x3000+((f-905)%2)*0x2000
   if regs[0x4301]==0x18 and baseppu<=address<baseppu+2048:old_map_jobs+=1;old_map_bytes+=regs[0x4305]+256*regs.get(0x4306,0)
  cpu=json.loads((native/'cpu-result.json').read_text());ppu=[e for e in ev if e[1]==1 and e[2]in(0x2118,0x2119,0x2122,0x2104)];new_jobs=cpu['PPU_jobs']-old_map_jobs+p['jobs'];new_bytes=len(ppu)-old_map_bytes+p['bytes'];budget=3328+1280*new_jobs+8*new_bytes
  wire_rows.append(dict(frame=f,recorded392=actual_meta,comparison='Actual392 wire'if actual_meta else'Recorded377 wire plus390 plan;no new live frame',old_map_wire=old_map,plan_wire=plan,new_map_wire=p['wire']['wire'],old_tile_wire=old_tiles,new_tile_wire=25*tile_count,old_nonmap_wire=old_nonmap,new_nonmap_wire=new_nonmap['wire'],old_output_E1_wire=old_selected,new_output_E1_wire_budget=new_selected,new_output_E1_no_nonmap_batch=safe,wire_saving=old_selected-new_selected,wire_saving_no_nonmap_batch=old_selected-safe,wire_time_us=(old_selected-new_selected)*64/21,wire_time_no_nonmap_batch_us=(old_selected-safe)*64/21,extra_E2_removed_credit=0,
    PPU=dict(old_map_jobs=old_map_jobs,old_map_bytes=old_map_bytes,old_all_jobs=cpu['PPU_jobs'],new_all_jobs=new_jobs,new_all_bytes=new_bytes,unchanged_1280_setup_3328_commit_budget=budget,within_49104=budget<=49104)))
 for p in [current/'output_files/board.map.rpt',current/'result.json',reference/'result.json',ROOT/'tools/nes_jobs393.c',ROOT/'tools/analyze_nes_jobs393.py',ROOT/'analysis/plan392-verification.json']:pin(p)
 #908's two runs happen to be in different screens and stay monotone.
 #909 and other frames prove why a general column ABI must replace the gate.
 assert next(r for r in rows if r['frame']==908)['policies'][2]['old_monotonic_checker_compatible']
 assert not next(r for r in rows if r['frame']==909)['policies'][2]['old_monotonic_checker_compatible']
 checker=(current/'nes_validator278.sv').read_text();assert 'unit359<v_map_end'in checker and 'v_q!=v_value'in checker and 'if(v_q&v_mask)fault<=2'in checker
 caps={'SPI_frontend_snapshot_CRC8':320,'host_record_executor_and_context':380,'queue_credit_storage':104,'NES_source_plan_tile_resume':460,'new_port_arbiter_and_bridge_delta':123};assert sum(caps.values())==1387
 readiness=[];old_component=json.loads((BASE/'probes/nes-plan390/arm01/result.json').read_text())['cases']
 for f in (907,908):
  w=next(r for r in wire_rows if r['frame']==f);r=next(r for r in rows if r['frame']==f)['policies'][2];prior=next(r for r in old_component if r['frame']==f);component_gain=(prior['instructions']-r['instructions'])/84000
  required_advance=.175209043+.100 if f==908 else .100-(238*1364-271951)*46561/1e9
  readiness.append(dict(frame=f,new_component_instructions=r['instructions'],old_component_instructions=prior['instructions'],component_CPI1_gain_ms=component_gain,post_view_target_ms=.100,required_advance_at_current_phase_ms=required_advance,
   conditional_overhead_ceiling_no_nonmap_batch_ms=w['wire_time_no_nonmap_batch_us']/1000+component_gain-required_advance,
   conditional_overhead_ceiling_batched_ms=w['wire_time_us']/1000+component_gain-required_advance,
   assumption='ALL wire and component gains advance ready;unproven critical-path attribution. No E2/IRQ/stall reduction credited. Not new processing or capture timing.'))
 whole_ppu=[]
 for r in rows:
  f=r['frame'];pp=groups[f-904];m=r['policies'][2];tiles=[p for p in pp if p[0]==7];cg=any(p[0]in(2,4,5,8)and p[1]==3 for p in pp);oam=any(p[0]in(2,4,5,8)and p[1]==4 for p in pp);vjobs=m['jobs']+len(tiles);j=vjobs+cg+oam;data=m['bytes']+sum(int.from_bytes(p[14:16],'little')for p in tiles)+512*cg+544*oam
  old_budget=3328+1280*j+8*data;target=3328+1200*vjobs+1408*(cg+oam)+8*data+512
  whole_ppu.append(dict(frame=f,fixture_only=True,VRAM_jobs=vjobs,other_jobs=int(cg)+int(oam),bytes=data,current_1280_budget=old_budget,current_plus512=old_budget+512,target_1200_VRAM_1408_other_plus512=target,target_below49104=target<=49104))
 observed={}
 for f in range(907,917):
  q=BASE/f'probes/nes-plan390/native01/{f}';e=[list(map(int,x))for x in csv.reader((q/'events.csv').read_text().splitlines())];tm=list(csv.DictReader((q/'timings.csv').read_text().splitlines()));tr=[int(x['clock'])for x in tm if x['phase']=='PPU_trigger'];done=[int(x['clock'])for x in tm if x['phase']=='PPU_done'];regs={};prior=None
  for start,end in zip(tr,done):
   for x in e:
    if x[4]>start:break
    if x[1]==1:regs[x[2]]=x[3]
   n=regs[0x4305]+256*regs.get(0x4306,0);kind=regs[0x4301]
   if prior is not None:observed[str(kind)]=max(observed.get(str(kind),0),end-prior-8*n)
   prior=end
 for p in [current/'nes_validator278.sv',BASE/'probes/nes-plan390/arm01/result.json',BASE/'probes/nes-plan390/joint04/joint266_tb.sv',d/'unit.elf']:pin(p)
 report=dict(stage=393,analysis_passed=True,new_RTL=False,new_MAP=False,new_live_schedule=False,component_ARM=True,component_cases=71*3+len(directed),fixture_file_count=fixture_count,fixture_digest=fixture_digest.hexdigest(),component_BSS_is_fixture=True,ARM_size=(d/'size.log').read_text(),map_jobs=rows,directed=directed,wire=wire_rows,readiness_budget=readiness,whole_PPU_fixture_budget=whole_ppu,old_native_observed_interjob_control_by_BBUS=observed,new_1200_1408_caps_are_unproven=True,whole_current392=actual,whole_reference375=old,disjoint_control=cost,disjoint_control_FF=ffs,control_FF_sum=sum(ffs.values()),retained_codec_checker=retained,other_retained_comb=outside,control_pool=3878,base_pool_without_tile_adapter=3678,required_net_deletion=required,replacement_ceiling=1387,base_replacement_ceiling=1187,replacement_hard_caps=caps,checker_delta_outside_budget=True,
  scope='Actual compiled M4 map job/packing component on71 recorded material fixtures;wire and exclusive wholeMAP structural budgets,not integrated ARM/IRQ/2slot/ROM timing or new area savings.',pins=pins)
 (d/'result.json').write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(dict(cases=report['component_cases'],control=cost,ceiling=1387,selected_wire=wire_rows[:2],selected=[r for r in rows if r['frame']in(907,908,914,915)]),indent=2))
if __name__=='__main__':main()
