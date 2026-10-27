# SPDX-License-Identifier: MIT
"""Reconcile394 functionality, strict failed cadence and matching whole Lite.
An evidence audit can pass while the candidate fails time and area admission."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from analyze_nes_receipt335 import load_image

def main():
 p=argparse.ArgumentParser();p.add_argument('--evidence',type=Path,default=BASE/'probes/nes-jobs394');p.add_argument('--out',type=Path,default=ROOT/'analysis/jobs394-verification.json');a=p.parse_args();d=a.evidence.resolve();pins={}
 def pin(q):pins[q.relative_to(BASE).as_posix()]=sha(q);return pins[q.relative_to(BASE).as_posix()]
 def read(q):pin(q);return q.read_text(encoding='utf-8-sig')
 def js(q):return json.loads(read(q))
 def whole(q):
  r=js(q/'result.json');assert r['passed']and not r['undriven'];return {k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',r['summary'])[1].replace(',',''))for k,v in dict(LE='Total logic elements',comb='Total combinational functions',FF='Dedicated logic registers',RAM_bits='Total memory bits').items()}
 def self_cost(q):
  r={}
  for line in read(q/'output_files/board.map.rpt').splitlines():
   c=[x.strip()for x in line.split(';')]
   if len(c)>4 and re.fullmatch(r'\|[^|]+\|',c[1])and re.fullmatch(r'\d+ \(\d+\)',c[2]):r[c[1].strip('|')]=int(re.search(r'\((\d+)\)',c[2])[1])
  return r
 reference=BASE/'probes/nes-plan390/map01';old=whole(reference);now=whole(d/'map03');before=self_cost(reference);after=self_cost(d/'map03')
 names=('nes_output260:flow','nes_host_context375:context375','nes_queue260:queue','nes_spi270:spi_front270','nes_transport257:transport','nes_plan_batch206:transport','nes_plan_spi200:endpoint','nes_tile_producer260:tiles','nes_tile_link394:tile_link')
 pool_before={n:before.get(n,0)for n in names};pool_after={n:after.get(n,0)for n in names};retained_names=('nes_core257:encoder','nes_validator278:validator')
 retained_before=sum(before[n]for n in retained_names);retained_after=sum(after[n]for n in retained_names)
 outside_before=old['comb']-sum(pool_before.values())-retained_before;outside_after=now['comb']-sum(pool_after.values())-retained_after
 assert old['comb']==17744 and sum(pool_before.values())==3878 and retained_before==2374
 required=old['comb']-15408+155;saving=old['comb']-now['comb'];assert required==2491 and saving==170 and now['comb']==17574
 arm=js(d/'arm10/result.json');assert arm['passed']and len(arm['cases'])==71 and all(x['coverage_exact']for x in arm['cases'])
 for row in arm['cases']:
  for n in ('jobs','wire'):pin(d/'arm10'/f'{n}{row["frame"]}.json')
 rtl=js(d/'guards05/result.json');assert rtl['passed']and rtl['frames']==12 and rtl['source_bytes']==rtl['actual_read_events']==25462 and rtl['max_credit']==2 and len(rtl['guards'])==17
 assert next(x for x in rtl['guards']if x['case']==11)['checker']==2 and next(x for x in rtl['guards']if x['case']==13)['checker']==3
 native=js(d/'native04/result.json');assert native['passed']and len(native['cases'])==13
 for row in native['cases']:
  q=d/'native04'/(str(row['frame'])+('-stop'if row.get('STOP')else''));assert pin(q/'spool.sfc')==row['ROM']and pin(q/'events.csv')==row['events']
  if row.get('STOP'):assert not row['final_ACK']
  else:assert row['ACK_scanline']>=225
 cg=js(d/'cpuguards03/result.json');assert cg['passed']and len(cg['cases'])==7 and all(not r['final_ACK']and r['forcedblank']and r['HDMA_off']for r in cg['cases'])
 loop=js(d/'loop01/result.json');assert loop['passed']and loop['frames']==12 and loop['reset_count']==1 and not loop['WRAM_reinitialized_between_frames']
 heavy=js(d/'heavy02/result.json');hr=heavy['cases'][0];assert hr['frame']==962 and hr['passed']and hr['synthetic_tile_bytes']and hr['PPU_jobs']==30 and hr['ACK_scanline']==260
 # Actual program bytes in the same physical4KiB ROM,not the old sink image.
 image=(d/'native04/907/spool.sfc').read_bytes();program=bytes(int(x,16)for x in read(d/'map03/sink-program.hex').split());assert program==image[:0xfc0]+image[0x7fc0:0x8000]
 manifest=js(d/'joint09/manifest394.json');matched={}
 for n,h in manifest['materialized_RTL'].items():
  assert pin(d/'joint09'/n)==h==pin(d/'map03'/n);matched[n]=h
 assert len(matched)==29
 for n,h in rtl['RTL'].items():assert pin(d/'guards05'/n)==h==sha(d/'map03'/n)
 assert load_image(d/'joint09/output.elf')==load_image(d/'build07/output.elf');pin(d/'joint09/output.elf');pin(d/'build07/output.elf')
 size=list(map(int,read(d/'build07/size368.log').splitlines()[1].split()[:3]));assert size==[35692,4,48720]
 for f in range(905,976):assert (d/'arm10'/f'wire{f}.json').read_bytes()==(d/'arm07'/f'wire{f}.json').read_bytes()
 def joint(q):
  log=read(q/'vsim.log');assert 'Fatal: startup missed fixed capture368'in log and 'Errors: 1, Warnings: 0'in log
  tb=read(q/'joint266_tb.sv');assert 'while(romcycle267<5371247)'in tb and 'MASTER_PERIOD_PS378=46561,SNES_PHASE378=0'in tb and '-gROM_WINDOW=1'in log
  workers=[json.loads(x)for x in read(q/'arm-worker.log').splitlines()if x.startswith('{')];assert [x['frame']for x in workers]==[905,906]
  events=list(csv.reader(read(q/'joint-events.csv').splitlines()));rows=[];rpc=[dict(SPI_bytes=0,E2_bytes=0,E2_requests=0,WFI_requests=0,charged_instruction_cycles=0,exception_cycles=0,requests=0)for w in workers];index=0;digest=hashlib.sha256()
  for request in sorted(q.glob('arm-req*'),key=lambda p:int(p.name[7:])):
   reply=q/f'arm-rsp{request.name[7:]}'
   if not reply.exists():break
   request_raw=request.read_bytes();reply_raw=reply.read_bytes();x=request_raw.decode().splitlines();y=reply_raw.decode().splitlines();low,high,level=map(int,y[0].split());time=low+(high<<32)
   while index<len(workers)and time>workers[index]['last_RTL_ns']:index+=1
   if index==len(workers):break
   count,instructions,extra=map(int,x[0].split());data=bytes.fromhex(x[1])if len(x)>1 else b'';r=rpc[index];r['requests']+=1;r['SPI_bytes']+=len(data);r['E2_bytes']+=len(data)if data[:1]==b'\xe2'else 0;r['E2_requests']+=data[:1]==b'\xe2';r['WFI_requests']+=count==260;r['charged_instruction_cycles']+=instructions;r['exception_cycles']+=extra
   digest.update(request.name.encode()+b'\0'+request_raw+reply.name.encode()+b'\0'+reply_raw)
  for w in workers:
   f=w['frame'];tr=js(q/f'arm{f}.json')['transfers'];tx=[bytes.fromhex(t['tx'])for t in tr];start=next(x for x in events if x[:2]==['start319',str(f)]);done=next(x for x in events if x[:2]==['frame_done',str(f)])
   costs=rpc[len(rows)];assert costs['SPI_bytes']==w['SPI_bytes']
   rows.append(dict(frame=f,source_start_ms=int(start[2])/1e9,done_ms=int(done[2])/1e9,elapsed_ms=(int(done[2])-int(start[2]))/1e9,ARM_instructions=w['instructions'],full_finish_and_commit_RPC=costs,E1_bytes_before_finish=sum(len(t)for t in tx if t[:1]==b'\xe1'),EA_bytes_before_finish=sum(len(t)for t in tx if t[:1]==b'\xea'),IRQ_instructions_before_finish=sum(t.get('IRQ_instructions',0)for t in tr)))
  final_time=int(re.search(r'Time: (\d+) ps',log)[1])/1e9
  rom=re.search(r'ROM368 requests=(\d+) replies=(\d+) pending=(\d+)',log);assert rom
  return dict(passed=False,first_failed_startup_frame=907,target_capture911_reached=False,fixed_capture_cycle=5371247,failure_time_ms=final_time,rows=rows,completed_RPC_sha256=digest.hexdigest(),ROM_requests=int(rom[1]),ROM_replies=int(rom[2]),ROM_pending=int(rom[3]))
 live=joint(d/'joint09');prior_trial=joint(d/'joint07');rejected=joint(d/'joint08')
 assert live['ROM_pending']==0 and live['ROM_requests']==live['ROM_replies']
 for name in ('nes-jobs394-contract.ko.md','nes-jobs394-plan.json'):pin(ROOT/'docs'/name)
 for f in ROOT.glob('tools/*394*'):pin(f)
 for q in (ROOT/'src/fpga/nes_jobs394').glob('*'):pin(q)
 pin(ROOT/'tests/nes-jobs394/record_tb.sv')
 result=dict(audit_passed=True,production_selected=False,time_goal_met=False,area_goal_met=False,scope=__doc__,whole=dict(reference392=old,candidate394=now,delta={k:now[k]-old[k]for k in old},net_comb_saving=saving,required_net_deletion=required,remaining_with_155_reserve=required-saving,raw_comb_shortage=now['comb']-15408,control_pool_before=pool_before,control_pool_after=pool_after,retained_before=retained_before,retained_after=retained_after,outside_before=outside_before,outside_after=outside_after,FIT=False,STA=False),ARM=dict(text=size[0],data=size[1],BSS=size[2],delta392=dict(text=size[0]-36570,BSS=size[2]-48724),delta377=dict(text=size[0]-35982,BSS=size[2]-48476),component_frames=71,component_stack=max(r['stack']for r in arm['cases']),full_IRQ_stack_bound=False,selected=[r for r in arm['cases']if r['frame']in(905,907,908,914,915,962)]),functional=dict(frames=12,actual_read_bytes=25462,RTL_guards=17,freeze_clocks=256,CPU_guards=7,CPU_loop=loop,CPU_body_bytes=1738,program_ROM_bytes=4096,SNES_payload_jobs_map_WRAM=15360,delta392_WRAM=-8481,DP_contiguous_reservation=68,heavy962=hr,heavy962_ROM_supply_is_synthetic=True,fullresident=False),live=live,prior_default_trial=prior_trial,rejected_cold256_trial=rejected,baseline392_first_missed_capture=911,matching_whole_functional_RTL=matched,remaining_legacy_bodies=['source transport','NES plan decoder and queue','SPI snapshot/CRC8 frontend'],not_proven=['60fps continuous display','full resident audio/input/IRQ/WCET','postSTOP normal hardware recovery','71frame heavy7 live schedule','multiple ROM phases','MMC4/MMC5','whole FIT/STA/physical board'],pins=pins)
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps({k:result[k]for k in('audit_passed','time_goal_met','area_goal_met','whole')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
