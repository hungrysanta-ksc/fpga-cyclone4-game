# SPDX-License-Identifier: MIT
"""Audit396 actual frontier/FIFO, partial control replacement and rejected cost.
Audit success does not mean60fps, full RAM executor completion or board admission.
"""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from analyze_nes_receipt335 import load_image

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=BASE/'probes/nes-joint396');p.add_argument('--out',type=Path,default=ROOT/'analysis/joint396-verification.json');a=p.parse_args();d=a.evidence.resolve();pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return sha(q)
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 def whole(q):
  r=js(q/'result.json');assert r['passed']and not r['undriven'];return {k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',',''))for k,v in dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits').items()}
 def costs(q):
  r={}
  for line in read(q/'output_files/board.map.rpt').splitlines():
   c=[x.strip()for x in line.split(';')]
   if len(c)>4 and re.fullmatch(r'\|[^|]+\|',c[1])and re.fullmatch(r'\d+ \(\d+\)',c[2]):r[c[1].strip('|')]=int(re.search(r'\((\d+)\)',c[2])[1])
  return r
 baseline=BASE/'probes/nes-jobs394';old=whole(baseline/'map03');now=whole(d/'map03');before=costs(baseline/'map03');after=costs(d/'map03')
 names=('nes_output260:flow','nes_transport257:transport','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_spi270:spi_front270','nes_queue260:queue','nes_tile_link394:tile_link','nes_check396:record_check','nes_walk396:execution')
 pool_before={n:before.get(n,0)for n in names};pool_after={n:after.get(n,0)for n in names};retained=('nes_core257:encoder','nes_validator278:validator')
 rbefore=sum(before[n]for n in retained);rafter=sum(after[n]for n in retained)
 assert old==dict(LE=22416,comb=17574,FF=9024,RAM_bits=300640)
 assert now==dict(LE=22872,comb=18108,FF=9033,RAM_bits=310112)
 assert sum(pool_before.values())==3716 and sum(pool_after.values())==3872
 manifest=js(d/'live07/manifest396.json');matched={}
 for n,h in manifest['RTL'].items():assert pin(d/'live07'/n)==h==pin(d/'map03'/n);matched[n]=h
 assert len(matched)==32
 rtl=js(d/'unit08/result.json');repeat=js(d/'repeat-unit05/result.json');edges=js(d/'edges03/result.json')
 assert rtl['passed']and rtl['frames']==12 and rtl['actual_read_events']==rtl['source_bytes']==25462 and rtl['max_credit']==2 and len(rtl['guards'])==19
 assert next(x for x in rtl['guards']if x['case']==11)['checker']==2 and next(x for x in rtl['guards']if x['case']==13)['checker']==3
 assert 'Fatal: frame905 flow1 checker0 state16'in read(d/'unit07-regression/vsim.log')
 assert pin(d/'unit07-regression/nes_mux260.sv')==sha(d/'build07/nes_mux260.sv')
 assert pin(d/'unit07-regression/record_tb.sv')==pin(d/'unit08/record_tb.sv')
 assert 'footer_pause396=14'in read(d/'unit08/record_tb.sv')
 assert repeat['passed']and repeat['actual_read_events']==26560 and repeat['max_credit']==2
 assert edges['passed']and edges['vectors']==24000 and 'full192stamps wrap=1 reads=10240'in read(d/'edges03/stage.log')
 for n,h in rtl['RTL'].items():assert pin(d/'unit08'/n)==h==sha(d/'map03'/n)
 for name in('nes_check396.sv','nes_walk396.sv','nes_stage396.sv'):assert pin(d/'edges03'/name)==sha(d/'map03'/name)
 arm=js(d/'arm01/result.json');assert arm['passed']and len(arm['cases'])==71
 for row in arm['cases']:
  f=row['frame'];assert row['coverage_exact'];assert read(d/'arm01'/f'wire{f}.json')==read(baseline/'arm10'/f'wire{f}.json');pin(d/'arm01'/f'jobs{f}.json')
 assert load_image(d/'build08/output.elf')==load_image(d/'live07/output.elf');pin(d/'build08/output.elf');pin(d/'live07/output.elf')
 size=list(map(int,read(d/'build08/size368.log').splitlines()[1].split()[:3]));assert size==[35776,4,48728]
 frontier=js(d/'armguard03/result.json');assert frontier['passed']and frontier['cases']==1770 and frontier['full_cases']==450 and frontier['accounted_ahead_cases']==150
 assert load_image(d/'build07/output.elf')==load_image(d/'build08/output.elf');pin(d/'build07/output.elf')
 assert frontier['ELF']==sha(d/'build07/output.elf')and frontier['case_sha']==pin(d/'armguard03/cases.json')
 native=js(d/'native01/result.json');assert native['passed']and len(native['cases'])==2
 for row in native['cases']:
  q=d/'native01'/(str(row['frame'])+('-stop'if row.get('STOP')else''));assert pin(q/'spool.sfc')==row['ROM']and pin(q/'events.csv')==row['events']
  if row.get('STOP'):assert not row['final_ACK']and row['PPU_jobs']==0
  else:assert row['ACK_scanline']>=225 and row['staged']==52
 image=(d/'native01/905/spool.sfc').read_bytes();assert bytes(int(x,16)for x in read(d/'map03/sink-program.hex').split())==image[:0xfc0]+image[0x7fc0:0x8000]
 q=d/'live07';log=read(q/'vsim.log');tb=read(q/'joint266_tb.sv')
 assert 'Fatal: next capture deadline missed367 frame911'in log and 'startup missed fixed capture368'not in log and 'Errors: 1, Warnings: 0'in log
 assert 'while(romcycle267<5371247)'in tb and 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in tb and '-gROM_WINDOW=1'in log
 workers=[json.loads(x)for x in read(q/'arm-worker.log').splitlines()if x.startswith('{')];assert [x['frame']for x in workers]==[905,906,907,908]
 events=list(csv.reader(read(q/'joint-events.csv').splitlines()));rows=[];rpc=[dict(SPI_bytes=0,E2_bytes=0,E2_requests=0,WFI_requests=0,charged_instruction_cycles=0,exception_cycles=0,requests=0)for _ in workers];index=0;digest=hashlib.sha256()
 for request in sorted(q.glob('arm-req*'),key=lambda p:int(p.name[7:])):
  reply=q/f'arm-rsp{request.name[7:]}'
  if not reply.exists():break
  raw=request.read_bytes();response=reply.read_bytes();x=raw.decode().splitlines();y=response.decode().splitlines();low,high,level=map(int,y[0].split());time=low+(high<<32)
  while index<len(workers)and time>workers[index]['last_RTL_ns']:index+=1
  if index==len(workers):break
  count,instructions,extra=map(int,x[0].split());data=bytes.fromhex(x[1])if len(x)>1 else b'';r=rpc[index];r['requests']+=1;r['SPI_bytes']+=len(data);r['E2_bytes']+=len(data)if data[:1]==b'\xe2'else 0;r['E2_requests']+=data[:1]==b'\xe2';r['WFI_requests']+=count==260;r['charged_instruction_cycles']+=instructions;r['exception_cycles']+=extra
  digest.update(request.name.encode()+b'\0'+raw+reply.name.encode()+b'\0'+response)
 old392=BASE/'probes/nes-plan390/joint04';prior=list(csv.reader(read(old392/'joint-events.csv').splitlines()))
 for w,r in zip(workers,rpc):
  f=w['frame'];start=next(x for x in events if x[:2]==['start319',str(f)]);done=next(x for x in events if x[:2]==['frame_done',str(f)]);present=next(x for x in events if x[:2]==['present394',str(f)])
  assert r['SPI_bytes']==w['SPI_bytes'];tr=js(q/f'arm{f}.json')['transfers']
  row=dict(frame=f,source_start_ms=int(start[2])/1e9,source_ROM_cycle=int(start[3]),done_ms=int(done[2])/1e9,elapsed_ms=(int(done[2])-int(start[2]))/1e9,PPU_present_ms=int(present[2])/1e9,VBlank_index=int(present[3]),ARM_instructions=w['instructions'],full_finish_and_commit_RPC=r,IRQ_instructions_before_finish=sum(t.get('IRQ_instructions',0)for t in tr))
  if f>=907:
   previous=next(x for x in prior if x[:2]==['start319',str(f)]);assert start==previous;row['source_start_and_ROM_cycle_exact392']=True
  rows.append(row)
 rom=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+) input_requests=(\d+) input_replies=(\d+) input_pending=(\d+)',log);assert rom and tuple(map(int,rom.groups()))==(45566,45566,0,8564,8564,0)
 for f in ROOT.glob('tools/*396*'):pin(f)
 for f in (ROOT/'src/fpga/nes_joint396').glob('*'):pin(f)
 for name in('nes-joint396-contract.ko.md','nes-joint396-plan.json'):
  if (ROOT/'docs'/name).exists():pin(ROOT/'docs'/name)
 result=dict(audit_passed=True,production_selected=False,time_goal_met=False,area_goal_met=False,full_RAM_executor_completed=False,scope=__doc__,whole=dict(reference394=old,candidate396=now,delta={k:now[k]-old[k]for k in old},remaining_with_155_reserve=now['comb']-15253,raw_comb_shortage=now['comb']-15408,required_control_cap_with_current_outside=15253-11885-2351,control_pool_before=pool_before,control_pool_after=pool_after,retained_before=rbefore,retained_after=rafter,outside_before=old['comb']-sum(pool_before.values())-rbefore,outside_after=now['comb']-sum(pool_after.values())-rafter,FIT=False,STA=False),ARM=dict(text=size[0],data=size[1],BSS=size[2],delta394=dict(text=84,BSS=8),component_frames=71,frontier=frontier,component_stack=304,full_IRQ_stack_bound=False,wire_equal394=True),functional=dict(frames=12,actual_reads=25462,RTL_guards=19,repeat_reads=26560,repeat_internal_fragments=[512,512,76],repeat_is_directed_equivalent_ABI=True,edge_vectors=24000,edge_FIFO_reads=10240,stamp_capacity=192,TAKE_preemption_cycles=14,preemption_reproduced_then_fixed=True,full_FIFO_and_ordinary_reservation=True,wrap_and_midcopy_STOP=True,CPU=native,fullresident=False),live=dict(passed=False,fixed907_startup_passed=True,fixed_capture_cycle=5371247,fixed_capture_ms=250.090631567,first_missed_capture=911,rows=rows,ROM_requests=45566,ROM_pending=0,input_requests=8564,input_pending=0,completed_RPC_sha256=digest.hexdigest(),CPI=1,full_WCET=False),matching_whole_functional_RTL=matched,remaining_legacy_bodies=['host packet/manifest/receipt protocol FSM and hot registers','source transport D4/D5 and source codec FSM','plan field semantics/lifetime and endpoint','queue storage/credit counters','SPI capture/response lifecycle'],unused_proposed_context_RAM='800..1023: no shared RAM context register file implemented',not_proven=['60fps continuous cadence','full395 RAM executor deletion budget','full resident audio/input/IRQ/WCET','normal recovery after STOP','71frame heavy7 live','multiple ROM phases','MMC4/MMC5','whole FIT/STA and physical board'],pins=pins)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('audit_passed','full_RAM_executor_completed','whole','live')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
