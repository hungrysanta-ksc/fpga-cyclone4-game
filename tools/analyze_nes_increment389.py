# SPDX-License-Identifier: MIT
"""Native388 and paired per-record service audit;no free source/initialization work."""
import argparse,csv,json,re
from pathlib import Path
import analyze_nes_source368 as old
from analyze_nes_receipt335 import completed_unit,load_image
from nes_bg295 import unbatch
from probe_nes_spool383 import plans,current_view
from nes_delta231 import ROOT,BASE,sha

MS=46561/1e9
def bus(p):return [list(map(int,x))for x in csv.reader(p.read_text().splitlines())]
def frame(q):
 ev=bus(q/'events.csv');jobs=old.js(q/'fixture.json');r=old.js(q/'cpu-result.json')
 starts={i:next(x[4]for x in ev if x[0]==i and x[1:3]==[0,0x6001])for i in range(1,len(jobs)+2)}
 overhead=[starts[i+1]-starts[i]-len(bytes.fromhex(j['data']))*8 for i,j in enumerate(jobs,1)]
 pre=next(x[4]for x in ev if x[1:3]==[0,0x4212])-max(x[4]for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b)
 origin=max(x[4]for x in ev if x[1:3]==[0,0x4212]and x[4]<r['PPU_start'])
 return dict(initial_clocks=starts[1],control_clocks=overhead,control_ms=sum(overhead)*MS,preflight_clocks=pre,preflight_ms=pre*MS,tail_clocks=r['ACK_master']-origin,tail_ms=(r['ACK_master']-origin)*MS),ev,jobs,r

def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--reference',type=Path,required=True);p.add_argument('--joint',type=Path,required=True);a=p.parse_args()
 root=BASE/'probes/nes-increment388';n=root/'native07';nr=old.js(n/'result.json');gr=old.js(root/'guards05/result.json');oracle,_=plans();native=[];pins={}
 assert nr['passed']and len(nr['cases'])==11 and gr['passed']and len(gr['cases'])==16
 assert nr['source']==sha(ROOT/'tools/probe_nes_increment388.py')==sha(n/'probe_nes_increment388.py')
 assert gr['source']==sha(ROOT/'tools/guard_nes_increment388.py')==sha(root/'guards05/guard_nes_increment388.py')
 for r in nr['cases']:
  f=r['frame'];q=n/(str(f)+('-stop'if r.get('STOP')else''))
  for fn,key in [('spool.sfc','ROM'),('events.csv','events'),('fixture.json','fixture'),('timings.csv','timings')]:assert sha(q/fn)==r[key];pins[str(q/fn)]=r[key]
  if r.get('STOP'):assert not r['final_ACK'];continue
  assert sha(q/'events.csv')==sha(root/f'native06/{f}/events.csv')and sha(q/'timings.csv')==sha(root/f'native06/{f}/timings.csv')
  data,ev,jobs,cpu=frame(q);prev,_,_,_=frame(BASE/f'probes/nes-burst386/native08/{f}')
  assert sha(q/'fixture.json')==sha(BASE/f'probes/nes-burst386/native08/{f}/fixture.json')
  script=(q/'capture.lua').read_text();prior=(oracle/f'expected-{f-906}.bin').read_bytes();expect=(oracle/f'expected-{f-904}.bin').read_bytes()
  for key,value in [('INITMAP',prior[:4096]),('INITOAM',prior[4608:5152]),('EXPECTMAP',expect[:4096]),('EXPECTOAM',expect[4608:5152])]:assert bytes.fromhex(re.search('local '+key+'="([0-9a-f]*)"',script)[1])==value
  assert bytes(x[3]for x in ev if x[1]==0 and 0x6070<=x[2]<=0x607b)==current_view(f)
  assert bytes(x[3]for x in ev if x[1]==1 and x[2]in(0x210d,0x210e))==current_view(f)[8:12]
  for i,j in enumerate(jobs,1):
   e=[x for x in ev if x[0]==i];reads=[x for x in e if x[1]==0 and 0x400800<=x[2]<=0x4017ff];assert bytes(x[3]for x in reads)==bytes.fromhex(j['data'])
   tokens=[x for x in e if x[1]==0 and 0x6048<=x[2]<=0x604b];writes=[x for x in e if x[1]==1 and 0x604c<=x[2]<=0x604f]
   assert [x[2]for x in tokens]==list(range(0x6048,0x604c)) and min(x[4]for x in tokens)>max(x[4]for x in reads)
   assert bytes(x[3]for x in tokens)==bytes(x[3]for x in writes)==j['token'].to_bytes(4,'little')
  pp=[x for x in ev if x[1]==1 and x[2]in(0x2118,0x2119,0x2122,0x2104)];st=[x for x in ev if x[1]==1 and x[2]in(0x6050,0x6059)]
  assert len(st)==len(jobs)and min(x[4]for x in pp)>max(x[4]for x in st)
  assert all(225<=x[5]<262 and x[4]//357368==cpu['ACK_master']//357368 for x in pp)
  budget=3328+cpu['PPU_jobs']*1280+8*len(pp);cut=246 if budget<=20000 else 238 if budget<=30000 else 230 if budget<=40000 else 225
  native.append(dict(frame=f,ROM_body_bytes=cpu['body_bytes']if'body_bytes'in cpu else r['body_bytes'],strategy=cpu['strategy'],PPU_jobs=cpu['PPU_jobs'],PPU_bytes=len(pp),native_cutoff_line=cut,current=data,reference386=prev,
   extra_source_control_ms=data['control_ms']-prev['control_ms'],preflight_gain_ms=prev['preflight_ms']-data['preflight_ms'],source_and_preflight_CPU_gain_ms=prev['control_ms']+prev['preflight_ms']-data['control_ms']-data['preflight_ms'],late_immutable_token_reads_checked=True))
 for r in gr['cases']:
  q=root/'guards05'/r['name'];assert sha(q/'spool.sfc')==r['ROM']and sha(q/'events.csv')==r['events']
  if r.get('STOP_or_capacity_abort'):assert not r['final_ACK']
  else:
   ev=bus(q/'events.csv');assert all(225<=x[5]<262 and x[4]//357368==r['ACK_master']//357368 for x in ev if x[1]==1 and x[2]in(0x2118,0x2119,0x2122,0x2104))
 assert next(x for x in gr['cases']if x['name']=='tilebudget')['staged']==4
 assert next(x for x in gr['cases']if x['name']=='mapoverflow')['staged']==256
 runs={};board=BASE/'probes/nes-context375/map03';shared={};normTB=None
 for key,d in [('reference386',a.reference),('incremental388',a.joint)]:
  raw=(d/'vsim.log').read_text();ev=old.events(d);m=old.js(d/'manifest384.json');meta=old.js(d/'manifest389.json');tb=(d/'joint266_tb.sv').read_text()
  assert '-gROM_WINDOW=1'in raw and load_image(d/'output.elf')==load_image(BASE/'probes/nes-frontier377/joint01/output.elf')
  if normTB is None:normTB=tb
  else:assert tb==normTB
  for name in set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',(board/'board.qsf').read_text())):
   if(d/name).exists():assert sha(d/name)==sha(board/name);shared[name]=sha(d/name)
  assert len(shared)==31
  for prof in m['profiles']:
   f=prof['frame'];actual,_,_,_=frame(Path(meta['native'])/str(f));base,_,_,_=frame(BASE/f'probes/nes-burst386/native08/{f}')
   assert prof['per_record_control_clocks']==actual['control_clocks']
   assert prof['first_source_init_extra_clocks']==max(0,actual['initial_clocks']-base['initial_clocks'])
   words=[int(x,16)for x in(d/f'spool-records{f}.hex').read_text().split()];assert [x>>40 for x in words[1:]]==prof['per_record_control_clocks']
  fs=[];done=[int(x[1])for x in ev if x[0]=='frame_done']
  for f in done:
   assert unbatch((d/f'actual-plans293-{f}.bin').read_bytes())==unbatch((BASE/f'probes/nes-frontier377/joint01/actual-plans293-{f}.bin').read_bytes())
   expected=[];seen=[];at=0;token=None;private=[]
   for x in ev:
    if x[1]!=str(f):continue
    if x[0]=='read336':
     tok,op,section,pos,off,val,t=map(int,x[2:]);assert off==at
     if not at:token=tok
     assert token==tok;at+=1;u=completed_unit(op,section,pos,2)
     if u:expected.append((tok,int(u[0]),u[1]))
    elif x[0]=='unit336':seen.append(tuple(map(int,x[2:5])))
    elif x[0]=='private336':assert int(x[2])==token;private.append(int(x[-1]))
    elif x[0]=='publish336':
     tok,count,t=map(int,x[2:]);assert tok==token and count==at and all(v<t for v in private);at=0;private=[];token=None
   assert expected==seen and not at
   start=old.event(ev,'start319',f);end=old.event(ev,'frame_done',f);r=dict(frame=f,start_ps=int(start[2]),ROM_start_cycle=int(start[3]),done_ps=int(end[2]),processing_ms=(int(end[2])-int(start[2]))/1e9,qualified_units=len(seen))
   if f>=907:
    ready=old.event(ev,'display_ready378',f);poll=old.event(ev,'display_poll378',f);window=old.event(ev,'vblank384',f);present=old.event(ev,'present384',f)
    cut=next(x['native_cutoff_line']for x in native if x['frame']==f);assert int(window[3])//1364<=cut
    pp=[x for x in ev if x[:2]==['ppu384',str(f)]];stores=[x for x in ev if x[:2]==['stored384',str(f)]]
    assert len(stores)==next(x['source_records']for x in m['profiles']if x['frame']==f)and max(int(x[-1])for x in stores)<min(int(x[-2])for x in pp)
    assert all(225*1364<=int(x[-1])<357368 for x in pp)
    r.update(ready_ps=int(ready[2]),display_poll_ps=int(poll[2]),display_poll_phase=int(poll[3]),native_cutoff_line=cut,VBlank_index=int(present[3]),present_ps=int(present[2]),VBlank_service_ms=(int(present[2])-int(window[2]))/1e9)
   fs.append(r)
  fail=re.search(r'Fatal: next capture deadline missed367 frame(\d+) owned(\d+)',raw)
  assert('Errors: 1, Warnings: 0'in raw)if fail else('PASS REFILL267'in raw and'Errors: 0, Warnings: 0'in raw)
  captures=[dict(frame=int(x[1]),admitted=x[3]=='1',time_ps=int(x[5]))for x in ev if x[0]=='capture_attempt367']
  runs[key]=dict(passed=not bool(fail),first_missed_capture=int(fail[1])if fail else None,completed=done,frames=fs,captures=captures,CPU_service_manifest=meta,profiles=m['profiles'],TB_sha256=sha(d/'joint266_tb.sv'))
  for name in('vsim.log','joint-events.csv','joint266_tb.sv','output.elf','manifest389.json','manifest384.json'):pins[str(d/name)]=sha(d/name)
 original=(BASE/'probes/nes-spool383/joint04/joint266_tb.sv').read_text();expected_tb=original
 for item in('dut.flow.tkind','2','dut.flow.header[1]'):expected_tb=expected_tb.replace('overhead384['+item+']','records384[record384+1][63:40]')
 expected_tb=expected_tb.replace('   if(recordlen384||record384>=records384[0])','   if(record384==0)#(config384[8]*MASTER_NS378);\n   if(recordlen384||record384>=records384[0])');assert normTB==expected_tb
 diffs=[]
 for r in runs['incremental388']['frames']:
  prev=next((x for x in runs['reference386']['frames']if x['frame']==r['frame']),None)
  if prev:diffs.append(dict(frame=r['frame'],same_start_and_ROM_cycle=(prev['start_ps'],prev['ROM_start_cycle'])==(r['start_ps'],r['ROM_start_cycle']),absolute_completion_gain_ms=(prev['done_ps']-r['done_ps'])/1e9,ready_gain_ms=(prev.get('ready_ps',0)-r.get('ready_ps',0))/1e9))
 assert next(x for x in diffs if x['frame']==907)['same_start_and_ROM_cycle']
 latest=next(x for x in runs['incremental388']['frames']if x['frame']==908)
 native908=next(x for x in native if x['frame']==908)
 cutoff_clocks=latest['native_cutoff_line']*1364-latest['display_poll_phase']
 pre=native908['current']['preflight_clocks'];budget=next(x['budget_clocks']for x in runs['incremental388']['profiles']if x['frame']==908)
 remaining=357368-latest['display_poll_phase']-pre
 causal=dict(frame=908,post_view_phase=latest['display_poll_phase'],native_cutoff_line=latest['native_cutoff_line'],post_view_to_native_cutoff_clocks=cutoff_clocks,post_view_to_native_cutoff_ms=cutoff_clocks*MS,
  actual_preflight_clocks=pre,preflight_over_native_cutoff_ms=(pre-cutoff_clocks)*MS,modeled_remaining_after_preflight_clocks=remaining,modeled_tail_budget_clocks=budget,modeled_tail_shortfall_clocks=budget-remaining,
  do_not_relax_cutoff_budget_or_phase=True)
 for name in('probe_nes_increment388.py','guard_nes_increment388.py','probe_nes_increment389.py','analyze_nes_increment389.py'):pins[str(ROOT/'tools'/name)]=sha(ROOT/'tools'/name)
 report=dict(stage=389,audit_completed=True,native388=native,guards=gr,runs=runs,paired_differences=diffs,causal_deadline=causal,shared_board_RTL=shared,
  cost=dict(ROM_body_bytes=3274,previous386_ROM_body_bytes=3290,payload_record_WRAM_bytes=24769,previous386_payload_record_WRAM_bytes=24705,job_bytes=3072,map_coordinate_bytes=1024,dirty_column_bytes=64,additional_DP_reservation_bytes=37,DP_copy_bytes_not_reclaimed_from_fullresident=8,
   inherited375_MAP=old.whole(board),new_FPGA_savings=0,comb_deficit=2255,required_net_deletion_with155reserve=2410,new_MAP=False,ROM_installed_on_board=False),
  normal_timing_unchanged_by_display_STOP_fix=True,scope='Actual native388 CPU plus live375RTL/377M4 with recorded per-record source/PPU service;325ordinaryWRAM and381head retained. Not one fullresidentCPU lockstep/WCET.',
  limits=['Prior-bank WRAM/VRAM/OAM/validbits and HDMA terminators are explicit warm fixtures. No cold or normal postSTOP recovery.','Sparse threshold activation/replay and initial CPU delta are charged. Work moved into source service is not free.','Per-record total control is conservatively placed before live source reads;not instruction-exact CPU/SPI bus lockstep.','Independent FPGA checker validates source read/CRC/coverage,not unseen SNES cache/PPU values.','No wholeFITSTA/livecoremapper/71heavy7/multiplephases/fullresidentIO/audio/WCET/physical60fps/MMC4-5 margin proof.'],physical=False,sustained60fps=False,pins=pins)
 a.out.write_text(json.dumps(report,indent=2)+'\n',newline='\n');print(json.dumps(dict(runs={k:dict(completed=v['completed'],miss=v['first_missed_capture'])for k,v in runs.items()},paired=diffs),indent=2))
if __name__=='__main__':main()
