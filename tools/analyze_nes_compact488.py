# SPDX-License-Identifier: MIT
"""Bind488 measured costs and rejected delivery gates; never infer physical FPS."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from check_nes_game478 import sha
from analyze_nes_mmc479 import resources
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for n in ['private','board','snes','phase','faults','units','live','bootbus','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();read=lambda q:json.loads(q.read_text(encoding='utf8'))
audit=read(a.private/'audit06/result.json');old=read(ROOT.parent/'probes/nes-output487/candidate-audit01/result.json')
window=read(a.private/'window01/result.json');sender=read(a.private/'sender02/result.json');guards=read(a.private/'armguards02/result.json')
normal,phase,faults,units,live,boot=[read(q/'result.json')for q in [a.snes,a.phase,a.faults,a.units,a.live,a.bootbus]]
assert all(x['passed']for x in [audit,old,window,sender,guards,normal,phase,faults,units,live,boot])
assert len(audit['frames'])==71 and len(units['cases'])==16 and len(sender['rows'])==8 and len(guards['rows'])==12
for x,y in zip(old['frames'],audit['frames']):assert x['frame']==y['frame'] and y['raw_rows']==2 and x['E1_wire_B']-y['E1_wire_B']==1797
arm=a.private/'ARM06/src';tested=a.private/'ARM04/src'
fw=(arm/'obj-nes-100/firmware.stm').read_bytes();before=(tested/'obj-nes-100/firmware.stm').read_bytes()
assert fw[:4]==before[:4] and fw[8:]==before[8:]
# genhdr.c derives header bytes4..7 from CLOCK_REALTIME. Payload and CRC equal.
assert 'calculate version magic CRC from current time'in(arm/'utils/genhdr.c').read_text()
assert sha(tested/'obj-nes-100/firmware.stm')==audit['firmware_SHA256']==window['compact_firmware_SHA256']==guards['firmware_SHA256']
assert sha(arm/'obj-nes-100/firmware.stm')==sender['firmware_SHA256']
assert re.search(r'202809\s+10040\s+18572',(a.private/'ARM06/size.log').read_text())
assert 'nes_sink212_seal\t304\tstatic'in(arm/'obj-nes-100/nes_native_sink165.su').read_text()
assert sum(len(read(a.private/f"audit06/frame{x['frame']}/plans.json"))for x in audit['frames'])==598
client=a.private/'client14';client_info=read(client/'build.json');pins=read(a.board/'source-pins.json')
for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
assert pins['client_SHA256']==sha(client/'sink165.sfc')==live['client_sha256']
program=bytes.fromhex((a.board/'sink-program.hex').read_text());assert len(program)==8192
assert hashlib.sha256(program).hexdigest()==pins['program_SHA256']==boot['program_SHA256'] and boot['reads']==8196
mifs=list((a.board/'db').glob('board.ram0_nes_sink_bus165*.hdl.mif'));assert len(mifs)==1
values={int(i):int(x,2)for i,x in re.findall(r'^\s*(\d+)\s*:\s*([01]{8})\s*;',mifs[0].read_text(),re.M)}
assert len(values)==8192 and bytes(values[i]for i in range(8192))==program
assert 'Successful'in(a.board/'output_files/board.fit.summary').read_text()
assert re.search(r'; M9Ks\s*; 51 / 56',(a.board/'output_files/board.fit.rpt').read_text(encoding='latin1'))
fit=resources(a.board/'output_files/board.fit.summary');prior=read(ROOT/'analysis/mmc482-verification.json')['FIT'];timing={};paths={}
for view in ['implementation','nominal']:
 rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'))
 paths[view]={k:min((x for x in rows if x['kind']==k and((x['from_clock']=='nes')==(x['to_clock']=='nes'))),key=lambda x:float(x['slack']))for k in ['setup','hold']}
 timing[view]={k:float(v['slack'])for k,v in paths[view].items()}
periods=[]
for label,test in [('same_start',normal),('start_plus4ms',phase)]:
 b,c=test['cases'];assert len(b['frames'])==len(c['frames'])==12 and b['commits']==c['commits']==12
 for f in range(905,917):assert(a.snes if label=='same_start'else a.phase).joinpath('baseline-normal',f'frame-{f}.rgb').read_bytes()==(a.snes if label=='same_start'else a.phase).joinpath('compact-normal',f'frame-{f}.rgb').read_bytes()
 elapsed=[(x['frames'][-1]['ACK_masterclock']-test['start_masterclock'])/21477.272 for x in [b,c]]
 periods.append({'comparison':label,'start_masterclock':test['start_masterclock'],'baseline_12_frames_ms':elapsed[0],'compact_12_frames_ms':elapsed[1],'saved_ms':elapsed[0]-elapsed[1],
 'decode_ms_range':[min(x['decode_masterclocks']for x in c['frames'])/21477.272,max(x['decode_masterclocks']for x in c['frames'])/21477.272],
 'max_decoder_service_gap_ms':max(x['decode_max_service_gap']for x in c['frames'])/21477.272,'observed_stack_B':[b['observed_stack_B'],c['observed_stack_B']],
 'final_DMA_ready_saved_us_range':[min((x['final_ready_masterclock']-y['final_ready_masterclock'])/21.477272 for x,y in zip(b['frames'],c['frames'])),max((x['final_ready_masterclock']-y['final_ready_masterclock'])/21.477272 for x,y in zip(b['frames'],c['frames']))]})
for case in faults['cases'][2:]:assert case['commits']==1 and case['last_status']==(228 if case['mode'].startswith('stop_')else 224)
seals=sorted(a.live.glob('req-*.bin'));seal=[q.read_bytes()for q in seals if q.read_bytes()[0]==3];assert len(seal)==1 and int.from_bytes(seal[0][38:40],'little')==0
instructions=[sum(x['target_instructions']for x in r['frames'])for r in [old,audit]];wire=[sum(x['E1_wire_B']for x in r['frames'])for r in [old,audit]]
r={'passed':True,'candidate':'compact488 canonical ABI4882','adopted_for_hardware':False,'hardware_trial_ready':False,'new_hardware_package':False,'full_path_acceleration_proven':False,'physical_FPS':None,
 'decision':'Candidate implemented and functional, not selected for delivery: no meaningful12-frame display gain and related setup failure. Keep physical485.',
 'M4':{'firmware_SHA256':sha(arm/'obj-nes-100/firmware.stm'),'tested_firmware_SHA256':audit['firmware_SHA256'],'rebuild_only_difference':'genhdr CLOCK_REALTIME version magic bytes4..7; every other firmware byte equal','text':202809,'data':10040,'BSS':18572,'firmware_B':len(fw),'Flash_tail_B':212992-len(fw),'Flash_delta_vs485_B':92,'Flash_delta_vs487_B':80,'seal_static_stack_B':304,'new_global_RAM_B':0,'expired_BG_workspace_B':384,'RUN_workspace_B':31848,'full_stack_IRQ_proof':False,'71_serializer_instructions':instructions,'serializer_reduction_percent':100*(1-instructions[1]/instructions[0]),'window_sample':window['rows'],'window_endpoint':'instant retirement; CPU instructions only'},
 'wire':{'scope':'ordinary/SEAL E1 only; excludes BEGIN, tile/plan, source and polling','71_E1_B':wire,'saved_E1_B':wire[0]-wire[1],'saved_per_raw2_frame_B':1797,'raw_CHR_B':[2048,384],'wire_saving_per_raw2_frame_ms_at2625000bps':1797*8/2625000*1000},
 'SNES':{'client_SHA256':sha(client/'sink165.sfc'),'program_SHA256':pins['program_SHA256'],'body_B':client_info['body_bytes'],'baseline_body_B':3712,'program_B':8192,'program_growth_B':4096,'new_persistent_context_B':0,'new_framebuffer_B':0,'temporary_staging_tail_B':0,'canonical_raw_restored_before_unchanged_validation_and_DMA':True,'comparisons':periods,'limits':'Four-credit wire model and actual65816; no common physical M4/IRQ/source/ROM clock'},
 'FPGA':{'whole_board_inputs':pins['board_inputs'],'changed':pins['changed'],'FIT':fit,'delta_vs482':{k:fit[k]-prior[k]for k in fit},'M9K':51,'remaining_LE':15408-fit['LE'],'remaining_M9K':5,'fit_report_SHA256':sha(a.board/'output_files/board.fit.rpt'),'related_timing_ns':timing,'related_worst_paths':paths,'related_timing_passed':all(v>=0 for t in timing.values()for v in t.values()),'full_CDC_IO_signoff':False},
 'functional':{'canonical_state_and_plans_71':True,'actual_plans':598,'M4_sender_boundary_cases':8,'actual65816_decoder_both_bank_vectors':16,'M4_ownership_guards':12,'full65816_pixels_and_DMA_frames':12,'faults':[{'mode':x['mode'],'commits':x['commits'],'status':x['last_status']}for x in faults['cases'][2:]],'current_C_RTL_65816_join':live,'join_raw_count':0,'raw_path_tested_separately':True,'extended_ROM_reads':8196,'STOP_base_menu_implementation_preserved':True,'new_physical_menu_test':False},
 'preserved_failures':['client01 slow per-word expansion','client02 exceeds3936-byte old layout; not SNES capacity','client07 valid but slower907.008ms/12','client08 DBR error caught by canonical comparison','client10/11 branch range compile errors','client12 absolute SBC under DBR7F caught; explicit DP fixed','ARM05 relative output path before build; fresh ARM06 absolute path PASS','snes23 bootstrap file preload timeout; bundled identical requests and same emulated clocks in25/26','board02 FIT PASS but setup-0.101ns; not waived or seed retried'],
 'next':['Inspect loader check_failed->byte_hold reset/control fanout and prove CRC/STOP cancellation before one future whole FIT','Compare restoration and raw VRAM DMA scheduling including1<->2 row/bank/STOP transitions; require display-time gain before delivery','Only after timing and integrated performance gates pass, build a fresh numbered paired installer preserving485/482/476/164/467 restores']}
assert not r['FPGA']['related_timing_passed']
a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'candidate_functional':True,'delivery_ready':False,'wire_saved_B':r['wire']['saved_E1_B'],'FIT':fit,'timing':timing}))
