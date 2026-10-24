# SPDX-License-Identifier: MIT
"""Actual frontier/host schedules and whole Lite costs; rejected source is diagnostic."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image,completed_unit
from analyze_nes_execute334 import wire
from probe_nes_arm264 import ELFFile
from probe_nes_decode280 import records,golden
from nes_runs342 import encode342

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--partial',action='store_true');a=ap.parse_args();root=BASE/'probes/nes-frontier342';pins={}
 def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
 def js(p):return json.loads(read(p))
 baseline=js(ROOT/'analysis/ingress338-verification.json');oldrtl=js(BASE/'probes/nes-ingress338/window03/result.json')['rtl_hashes'];runs={}
 for tag,ref in [('window01','window03'),('fixed01','fixed01'),('normal01','normal01'),('hostwindow02','window03')]:
  d=root/tag
  if not (d/'result.json').exists():assert a.partial,tag;continue
  r=js(d/'result.json');assert r['passed'];changes={n for n,h in r['rtl_hashes'].items() if h!=oldrtl[n]};assert changes==({'nes_mux260.sv'} if tag.startswith('host') else set())
  for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
  assert sha(d/'joint266_tb.sv')==r['tb_sha256'];read(d/'joint266_tb.sv');assert sha(d/'output.elf')==r['ELF_sha256'];pins[str(d/'output.elf')]=sha(d/'output.elf')
  assert load_image(d/'output.elf')==load_image(root/'window01/output.elf')
  for code in d.iterdir():
   if code.is_file() and code.suffix in ('.c','.h','.inc'):read(code)
  assert 'Errors: 0, Warnings: 0' in read(d/'vlog.log') and 'PASS REFILL267 frames=3' in read(d/'vsim.log')
  for n in ('CPU-bus.csv','CPU-timing.csv','CPU-ordinary.sfc','source-ARM-decoder.elf','source-ARM-blocks.csv'):
   assert sha(d/n)==sha(BASE/'probes/nes-ingress338'/ref/n);pins[str(d/n)]=sha(d/n)
  assert read(d/'blocks.txt')==read(BASE/'probes/nes-ingress338'/ref/'blocks.txt')
  events=list(csv.reader(read(d/'joint-events.csv').splitlines()));cycles={int(x['frame']):int(x['total'])*45.454/1e6 for x in csv.DictReader(read(d/'cycles.csv').splitlines())};marks=js(d/'metadata317.json');rows=[]
  for prev in baseline['runs'][ref]['rows']:
   f=prev['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)];first=lambda name:next(x for x in e if x[0]==name)
   start=first('start319');end=first('frame_done');req=next(x for x in e if x[0]=='firstreq305' and x[2]=='0');accept=next(x for x in e if x[0]=='rom_accept327' and x[2]=='0');total=cycles[f]+int(end[3])/1e9
   if tag=='fixed01':assert int(start[2])/1e9==prev['start_ms'] and int(start[3])==prev['start_ROM_cycle']
   transfers=js(d/f'arm{f}.json')['transfers'];oldtrans=js(BASE/'probes/nes-ingress338'/ref/f'arm{f}.json')['transfers'];w=wire(transfers);ow=wire(oldtrans);newplans=w.pop(0xe9);oldplans=ow.pop(0xe9);assert w==ow,(tag,f,'E1/DMA')
   def payload(plans):
    return b''.join((lambda b:b[4:4+int.from_bytes(b[1:3],'little')])(bytes.fromhex(x)) for x in plans)
   assert payload(newplans)==payload(oldplans),(tag,f,'plan order')
   expected=[];observed=[];offset=0;token=None;writes=[];pub=0
   for x in e:
    if x[0]=='read336':
     tok,op,section,pos,off,data,t=map(int,x[2:]);assert off==offset
     if not offset:token=tok
     assert token==tok;offset+=1;u=completed_unit(op,section,pos,2)
     if u:expected.append((tok,int(u[0]),u[1]))
    elif x[0]=='unit336':observed.append(tuple(map(int,x[2:5])))
    elif x[0]=='private336':
     tok,addr,value,t=map(int,x[2:]);assert tok==token;writes.append(t)
    elif x[0]=='publish336':
     tok,n,t=map(int,x[2:]);assert token==tok and n==offset and n>0 and all(z<t for z in writes);offset=0;token=None;writes=[];pub+=1
   assert expected==observed and offset==0
   credit=max(int(x[2]) for x in e if x[0]=='credits');assert credit<=2
   calls=[x for x in marks if x['name']=='advance342' and x['start']['generation']==f-904]
   firstprefix=next((x for x in calls if x['end'].get('prefixes342',0)>x['start'].get('prefixes342',0)),None)
   rows.append(dict(frame=f,total_ms=total,delta_ms=total-prev['total_ms'],start_ms=int(start[2])/1e9,start_delta_ms=int(start[2])/1e9-prev['start_ms'],start_ROM_cycle=int(start[3]),first_request_ms=int(req[-1])/1e9,first_request_after_start_ms=(int(req[-1])-int(start[2]))/1e9,first_accept_ms=int(accept[-1])/1e9,first_OBJ_request_ms=int(next(x for x in e if x[0]=='firstreq305' and x[2]=='1')[-1])/1e9,first_OBJ_accept_ms=int(next(x for x in e if x[0]=='rom_accept327' and x[2]=='1')[-1])/1e9,post_ROM_ms=(int(end[2])-int(accept[-1]))/1e9,gap_ms=total-1000/60,first_E9_wire=len(bytes.fromhex(newplans[0])),plan_wire=sum(len(bytes.fromhex(x)) for x in newplans),first_frontier_check_after_start_ms=(calls[0]['start']['modeled_ns']/1e6-int(start[2])/1e9) if calls else None,last_frontier_check_after_start_ms=(calls[-1]['end']['modeled_ns']/1e6-int(start[2])/1e9) if calls else None,first_E9_after_start_ms=(int(next(x for x in e if x[0]=='ARM_wire_start334' and x[2]=='233')[-1])-int(start[2]))/1e9,advance_calls=len(calls),advance_instructions=sum(x['end']['instruction']-x['start']['instruction'] for x in calls),last_frontier=calls[-1]['end'].get('frontier342') if calls else None,last_checks=calls[-1]['end'].get('checks342') if calls else None,prefix_timing=firstprefix,qualified_units=len(observed),published_chunks=pub,max_credit=credit))
  with (d/'output.elf').open('rb') as fp:
   elf=ELFFile(fp);sizes={n:elf.get_section_by_name(n)['sh_size'] if elf.get_section_by_name(n) else 0 for n in ('.text','.data','.bss')}
  runs[tag]=dict(rows=rows,sizes=sizes,stack=r['ARM']['stack_observed'],IRQ_cases=len(r['ARM']['IRQ_cases']))
 if 'hostwindow02' in runs:
  assert js(root/'hostwindow02/result.json')['ARM']==js(root/'window01/result.json')['ARM']
  for n in ('joint-events.csv','cycles.csv','arm905.json','arm906.json','arm907.json'):assert read(root/'hostwindow02'/n)==read(root/'window01'/n)
 boards={}
 for tag,changed in [('hostmap01',{'nes_mux260.sv'}),('sourcehostmap02',{'nes_core257.sv','nes_mux260.sv'})]:
  d=root/tag
  if not (d/'result.json').exists():assert a.partial;continue
  r=js(d/'result.json');assert r['passed'];old=js(BASE/'probes/nes-ingress338/board01/result.json');assert {n for n,h in r['actual_inputs'].items() if h!=old['actual_inputs'].get(n)}==changed
  for n,h in r['actual_inputs'].items():assert sha(d/n)==h;read(d/n)
  log=read(d/'map.log');assert 'Warning (10034)' not in log;assert all('cache_index141' in x for x in re.findall(r'Warning \(10240\):[^\r\n]+',log))
  whole={k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',','')) for k,v in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
  nodes={};report=read(d/'output_files/board.map.rpt')
  for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
   c=[x.strip() for x in line.split(';')]
   if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
  assert sum(nodes.values())==whole['comb']
  for name in ('nes_core257:encoder|state','nes_output260:flow|state','nes_output260:flow|owner','nes_output260:flow|tap_state278'):
   assert any('State Machine - ' in line and name in line for line in report.splitlines()),name
  boards[tag]=dict(whole=whole,delta={k:whole[k]-baseline['whole'][k] for k in whole},comb_deficit=whole['comb']-15408,own={k:v for k,v in nodes.items() if k.endswith(('nes_output260:flow','nes_core257:encoder'))})
 if 'hostwindow02' in runs:
  host=read(root/'hostmap01/nes_mux260.sv').replace(' output wire tile_closed267,\n','').replace('reg tiles_closed;assign tile_closed267=tiles_closed;','reg tiles_closed;');assert host==read(root/'hostwindow02/nes_mux260.sv')
 codec=js(root/'codec02/result.json');assert codec['passed'] and len(codec['frames'])==71
 for n,k in [('decoder.elf','ELF_sha256'),('nes_decode280.c','C_sha256')]:assert sha(root/'codec02'/n)==codec[k];pins[str(root/'codec02'/n)]=codec[k]
 for name,h in codec['input_hashes'].items():assert sha(Path(name))==h;read(Path(name))
 before=bytes(4398);raw_before=None
 for f in range(905,976):
  geom,raw=golden(f);p=root/f'codec02/frame{f}.records';assert records(p)==encode342(before,geom,raw,raw_before,f-904,f-904);read(p);before=geom;raw_before=raw
 blocks=list(csv.DictReader(read(root/'codec02/blocks.csv').splitlines()));ref=js(ROOT/'analysis/structure339-verification.json');wire_rows=[]
 for row in ref['rows']:
  v=[x for x in blocks if int(x['frame'])==row['frame']];wire_bytes=sum(int(x['length']) for x in v)+15*len(v)+8
  wire_rows.append(dict(frame=row['frame'],wire=wire_bytes,delta=wire_bytes-row['reference_wire']))
 cg=js(root/'codecguards01/result.json');ag=js(root/'armguards01/result.json');assert cg['passed'] and ag['passed'] and cg['ELF_sha256']==codec['ELF_sha256'] and ag['ELF_sha256']==sha(root/'window01/output.elf')
 guards=[]
 if not a.partial:
  for name,h in baseline['pins'].items():assert sha(Path(name))==h
  g=js(root/'guards02/result.json');assert g['passed'] and g['rtl_hashes']==js(root/'hostwindow02/result.json')['rtl_hashes'] and g['ELF_sha256']==sha(root/'hostwindow02/output.elf')
  for x in g['cases']:
   p=root/f"guards02/case{x['case']}/vsim.log";assert sha(p)==x['log_sha256'];read(p);guards.append(x['case'])
  for n in ('final-raw0','aperture'):assert js(root/'guards02'/n/'result.json')['passed']
 for p in ROOT.glob('tools/*342.py'):read(p)
 out=dict(stage=342,passed=True,selected=False,selected_RTL=338,selected_ARM=336,runs=runs,boards=boards,source_wire_rows=wire_rows,source_wire_total=sum(x['wire'] for x in wire_rows),source_regressions=[x for x in wire_rows if x['delta']>0],codec_guards=len(cg['cases']),ARM_frontier_guards=len(ag['cases']),RTL_guards=guards,source_RTL_fullpath_verified=False,scope='Frontier actual M4 on338 RTL; host replacement separately integrated. Uniform source has actual71 M4 decoder and whole MAP only, rejected wire before full RTL schedule. No FIT/STA/fullRUN/physical60fps.',pins=pins)
 if not a.partial:(ROOT/'analysis/frontier342-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
 print(json.dumps({k:v for k,v in out.items() if k not in ('pins','source_wire_rows','source_regressions')},indent=2))
if __name__=='__main__':main()
