# SPDX-License-Identifier: MIT
"""Bind native CPU, identical ARM, expanded RTL, same-phase schedules and Lite."""
import argparse,csv,json,re
from nes_delta231 import BASE,ROOT,sha
from probe_nes_arm264 import ELFFile

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--single-stage',action='store_true');args=ap.parse_args()
 d=BASE/'probes/nes-expand325';pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 baseline=js(ROOT/'analysis/owner319-verification.json');runs={}
 boardtag='board01' if args.single_stage else 'board02'
 guardtag='guards01' if args.single_stage else 'guards02'
 board=js(d/boardtag/'result.json');assert board['passed']
 for n,h in board['actual_inputs'].items():assert sha(d/boardtag/n)==h;pins[str(d/boardtag/n)]=h
 whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',board['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
 log=read(d/boardtag/'map.log');assert 'Warning (10034)' not in log
 assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
 pairs=[('fixed02','fixed02'),('window01','window01'),('normal01','normal01')] if args.single_stage else [('fixed03','fixed02'),('window02','window01'),('normal02','normal01')]
 for tag,basetag in pairs:
  q=d/tag;r=js(q/'result.json');assert r['passed']
  for n,h in r['rtl_hashes'].items():assert sha(q/n)==h;pins[str(q/n)]=h
  for n in ('nes_mux260.sv','nes_bulk_aperture188.sv','nes_validator278.sv'):
   a=read(d/boardtag/n);b=read(q/n)
   if n=='nes_mux260.sv':
    assert a.count(' output wire tile_closed267,\n')==1 and a.count('assign tile_closed267=tiles_closed;')==1
    a=a.replace(' output wire tile_closed267,\n','').replace('assign tile_closed267=tiles_closed;','')
   assert a==b,n
  assert sha(q/'output.elf')==r['ELF_sha256']
  images=[]
  for path in (q/'output.elf',BASE/'probes/nes-owner319'/basetag/'output.elf'):
   pins[str(path)]=sha(path)
   with path.open('rb') as f:images.append([(s['p_vaddr'],s['p_memsz'],s.data()) for s in ELFFile(f).iter_segments() if s['p_type']=='PT_LOAD'])
  assert images[0]==images[1]
  assert sha(q/'joint266_tb.sv')==r['tb_sha256'];read(q/'joint266_tb.sv')
  for n in ('ordinary.sfc','bus.csv','timing.csv','capture.lua','packets.hex'):
   assert sha(q/('CPU-'+n))==sha(d/'cpu01'/n);pins[str(d/'cpu01'/n)]=sha(d/'cpu01'/n)
  events=list(csv.reader(read(q/'joint-events.csv').splitlines()))
  source={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(q/'cycles.csv').splitlines())}
  rows=[]
  for f in (905,906,907):
   e=[x for x in events if len(x)>1 and x[1]==str(f)]
   first=lambda name:next(x for x in e if x[0]==name)
   end=first('frame_done');start=first('start319');arm=next(x for x in r['ARM']['frames'] if x['frame']==f)
   old=next(x for x in baseline['runs'][basetag]['rows'] if x['frame']==f)
   total=source[f]+int(end[3])/1e9;finish=int(end[2])/1e9
   if basetag=='fixed02':assert int(start[2])/1e9==old['start_ms'] and int(start[3])==old['start_ROM_cycle']
   bg=int(next(x for x in e if x[:3]==['romtile305',str(f),'0'])[-1])/1e9
   meta=int(next(x for x in e if x[:3]==['release312',str(f),'15'])[-1])/1e9
   assert sum(int(x[3]) for x in e if x[0]=='arm267')==arm['SPI_bytes']
   transfers=js(q/f'arm{f}.json')['transfers'];previous=js(BASE/'probes/nes-owner319'/basetag/f'arm{f}.json')['transfers']
   for opcode in ('e1','e9'):
    assert [x['tx'] for x in transfers if x['tx'].startswith(opcode)]==[x['tx'] for x in previous if x['tx'].startswith(opcode)],(tag,f,opcode)
   row=dict(frame=f,start_ms=int(start[2])/1e9,start_ROM_cycle=int(start[3]),finish_ms=finish,total_ms=total,gap_ms=total-1000/60,
    first_BG_ms=bg,metadata_release_ms=meta,ARM_instructions=arm['instructions'],SPI_bytes=arm['SPI_bytes'],
    max_credit=max(int(x[2]) for x in e if x[0]=='credits'),finish_delta_ms=finish-old['finish_ms'],duration_delta_ms=total-old['total_ms'],
    ARM_delta=arm['instructions']-old['ARM_instructions'],SPI_delta=arm['SPI_bytes']-old['SPI_bytes'],identical_E1_E9=True)
   assert row['max_credit']<=2
   stage=[x for x in e if x[0]=='stage325']
   if stage:row['staging_host_ticks']=dict(zip(('expand','tile_owner_wait','chunk_ready'),map(int,stage[0][2:])))
   row['ROM_wait_cumulative']=list(map(int,first('romwait267')[2:]))
   rows.append(row)
  runs[tag]=dict(rows=rows,SysTick=len(r['ARM']['IRQ_cases']),EXTI=len(r['ARM']['EXTI284']),stack=r['ARM']['stack_observed'],ELF=r['ELF_sha256'])
 cpu=js(d/'cpu01/result.json');cg=js(d/'cpuguard02/result.json')
 stop=js(d/'cpustop03/result.json');assert stop['passed'] and stop['CPU']['zero_DMA_fills']==11 and stop['ROM_sha256']==cpu['ROM_sha256']
 stopbus=list(csv.DictReader(read(d/'cpustop03/bus.csv').splitlines()))
 assert len([x for x in stopbus if x['write']=='1' and int(x['address'])==0x6006 and int(x['value'])==0xa5 and x['case']=='2'])==1
 read(d/'cpustop03/capture.lua')
 guards=dict(passed=None,cases=[],interrupted='Rejected single-stage architecture; fault work moved to tile-pingpong candidate') if args.single_stage else js(d/guardtag/'result.json')
 assert cpu['passed'] and cg['passed']
 if not args.single_stage:assert guards['passed'] and len(guards['cases'])==10
 assert cpu['CPU']['commands']==544 and cpu['CPU']['output_bytes']==128041 and cpu['CPU']['zero_DMA_fills']==2
 for row in guards['cases']:
  path=d/guardtag/f"case{row['case']}"/'vsim.log';assert sha(path)==row['log_sha256'];raw=read(path)
  expected=7 if row['case']==10 else 3 if row['case']==6 else 4
  assert f"PASS OWNER319 GUARD={row['case']} fault={expected}" in raw
 aperture=None
 if not args.single_stage:
  assert guards['rtl_hashes']==js(d/pairs[0][0]/'result.json')['rtl_hashes']
  aperture=js(d/guardtag/'aperture/result.json');assert aperture['passed'] and aperture['RTL_sha256']==sha(d/boardtag/'nes_bulk_aperture188.sv')
  for n,key in [('aperture325_tb.sv','tb_sha256'),('vsim.log','log_sha256')]:assert sha(d/guardtag/'aperture'/n)==aperture[key];read(d/guardtag/'aperture'/n)
 def nodes(report):
  out={}
  for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
   c=[v.strip() for v in line.split(';')]
   if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):out[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
  return out
 new=nodes(read(d/boardtag/'output_files/board.map.rpt'));old=nodes(read(BASE/'probes/nes-owner319/board01/output_files/board.map.rpt'))
 assert sum(new.values())==whole['comb']
 delta={k:new.get(k,0)-old.get(k,0) for k in sorted(set(new)|set(old))};delta={k:v for k,v in delta.items() if v}
 timings={};staging={}
 for name,p in [('old',BASE/'probes/nes-executor313/cpu03/timing.csv'),('new',d/'cpu01/timing.csv')]:
  rows=list(csv.DictReader(read(p).splitlines()));timings[name]={str(f):sum(int(x['total_clocks']) for x in rows if int(x['serial'])==f-904) for f in (905,906,907)}
  case_frame={int(x['case']):int(x['serial'])+904 for x in rows}
  bus=list(csv.DictReader(read(p.parent/'bus.csv').splitlines()))
  staging[name]={str(f):sum(1 for x in bus if case_frame[int(x['case'])]==f and x['write']=='0' and 0x400800<=int(x['address'])<0x401800) for f in (905,906,907)}
 for n in ('nes_expand325.py','probe_nes_expand325.py','probe_nes_consumer325.py','probe_nes_stop325.py','map_nes_expand325.py','guard_nes_expand325.py','analyze_nes_expand325.py'):read(ROOT/'tools'/n)
 out=dict(stage=325,variant='single_stage' if args.single_stage else 'tile_pingpong',passed=True,baseline=319,identical_ARM_PT_LOAD=True,runs=runs,whole=whole,whole_delta=dict(LE=whole['LE']-22618,comb=whole['comb']-17824,FF=whole['FF']-9022,RAM_bits=whole['RAM_bits']-307808),comb_deficit=whole['comb']-15408,
  entity_comb_delta=delta,CPU=cpu['CPU'],CPU_ROM_bytes=cpu['rom_body_bytes'],CPU_guards=cg['CPU'],CPU_STOP=stop['CPU'],CPU_total_master_clocks=timings,CPU_staging_reads=staging,
  fault_guards=guards,aperture_test=aperture,board_sim_difference='tile_closed267 output alias only; rest of host, validator and aperture exact',full71_ARM=False,FIT=False,STA=False,physical_60fps=False,input_hashes=pins)
 (ROOT/('analysis/expand325-single-stage.json' if args.single_stage else 'analysis/expand325-verification.json')).write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ('input_hashes','fault_guards')},indent=2))

if __name__=='__main__':main()
