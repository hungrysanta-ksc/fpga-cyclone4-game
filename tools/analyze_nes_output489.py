# SPDX-License-Identifier: MIT
"""Bind489 one-source functional, elapsed-time, whole-FIT and paired-trial gates."""
import argparse,csv,hashlib,json,re
from pathlib import Path
from check_nes_game478 import sha,ELFFile
from analyze_nes_mmc479 import resources
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
for n in ['private','board','loader','live','bootbus','programmer','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();read=lambda p:json.loads(p.read_text(encoding='utf8'));temp=a.live.parent
audit=read(a.private/'audit01/result.json');old=read(ROOT.parent/'probes/nes-output487/candidate-audit01/result.json');prior=read(ROOT/'analysis/compact488-verification.json')
loader,live,boot,pgm=[read(x/'result.json')for x in [a.loader,a.live,a.bootbus,a.programmer]];asm=read(a.private/'assembly01/result.json')
guards=read(a.private/'armguards02/result.json');sender=read(a.private/'sender01/result.json');window=read(a.private/'window01/result.json')
assert all(x['passed']for x in [audit,loader,live,boot,pgm,asm,guards,sender,window])
assert len(audit['frames'])==71 and sum(len(read(a.private/f"audit01/frame{x['frame']}/plans.json"))for x in audit['frames'])==598
assert loader['states']==294912 and len(loader['negative_controls'])==3 and guards['actual_M4'] and len(guards['rows'])==12
pins=read(a.board/'source-pins.json')
for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
assert sha(a.board/'nes_rom_loader.sv')==loader['new_SHA256']
client=a.private/'client04';meta=read(client/'build.json');program=bytes.fromhex((a.board/'sink-program.hex').read_text());assert len(program)==5120
assert pins['client_SHA256']==sha(client/'sink165.sfc')==live['client_sha256']
assert pins['program_SHA256']==hashlib.sha256(program).hexdigest()==boot['program_SHA256'] and boot['reads']==5124
mifs=list((a.board/'db').glob('board.ram0_nes_sink_bus165*.hdl.mif'));assert len(mifs)==1
values={int(i):int(x,2)for i,x in re.findall(r'^\s*(\d+)\s*:\s*([01]{8})\s*;',mifs[0].read_text(),re.M)}
assert len(values)==5120 and bytes(values[i]for i in range(5120))==program
assert asm['RBF_SHA256']==pgm['rbf_sha256']==sha(a.board/'output_files/board.rbf') and asm['BI3_SHA256']==pgm['image_sha256']
assert 'Successful'in(a.board/'output_files/board.fit.summary').read_text();fit=resources(a.board/'output_files/board.fit.summary')
assert re.search(r'; M9Ks\s*; 51 / 56',(a.board/'output_files/board.fit.rpt').read_text(encoding='latin1'))
timing={};paths={}
for view in ['implementation','nominal']:
 rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'))
 paths[view]={k:min((x for x in rows if x['kind']==k and((x['from_clock']=='nes')==(x['to_clock']=='nes'))),key=lambda x:float(x['slack']))for k in ['setup','hold']}
 timing[view]={k:float(x['slack'])for k,x in paths[view].items()};assert min(timing[view].values())>=0
def funcs(p):
 with p.open('rb')as f:
  e=ELFFile(f);ret={}
  for s in e.get_section_by_name('.symtab').iter_symbols():
   if s['st_info']['type']=='STT_FUNC'and s['st_size']and isinstance(s['st_shndx'],int):
    sec=e.get_section(s['st_shndx']);i=(s['st_value']&~1)-sec['sh_addr'];ret[(s.name,s['st_value'],s['st_size'])]=sec.data()[i:i+s['st_size']]
  return ret
tested=a.private/'ARM01/src';arm=a.private/'ARM02/src';assert funcs(tested/'obj-nes-100/sd2snes.elf')==funcs(arm/'obj-nes-100/sd2snes.elf')
assert sha(tested/'obj-nes-100/firmware.stm')==audit['firmware_SHA256']==sender['firmware_SHA256']
assert sha(arm/'obj-nes-100/firmware.stm')==guards['firmware_SHA256']
assert re.search(r'202825\s+10040\s+18572',(a.private/'ARM02/size.log').read_text())
for name in ['nes_checkpoint112.c','nes_menu_diagnostic.c']:
 s=(arm/name).read_text();assert '485'not in s and '489'in s
assert 'nes_sink212_seal\t304\tstatic'in(arm/'obj-nes-100/nes_native_sink165.su').read_text()
comparisons=[]
for name,expected in [('snes04',12),('snes06',71),('snes07',12),('cold01',12)]:
 run=read(temp/('nes-output489-'+name)/'result.json');b,c=run['cases'];assert b['commits']==c['commits']==expected
 elapsed=[(x['frames'][-1]['ACK_masterclock']-run['start_masterclock'])/21477.272 for x in [b,c]];assert elapsed[1]<elapsed[0]-10
 comparisons.append({'name':name,'frames':expected,'start_masterclock':run['start_masterclock'],'baseline_ms':elapsed[0],'candidate_ms':elapsed[1],'saved_ms':elapsed[0]-elapsed[1],'reduction_percent':100*(1-elapsed[1]/elapsed[0]),'VRAM_DMA_B':[b['vram_DMA_B'],c['vram_DMA_B']],'observed_stack_B':[b['observed_stack_B'],c['observed_stack_B']],'first_packet_poll_clocks':[b.get('first_packet_poll_masterclock'),c.get('first_packet_poll_masterclock')]})
faults=read(temp/'nes-output489-snes05/result.json');stop=read(temp/'nes-output489-transition-stop01/result.json')
for c in faults['cases'][2:]:assert c['commits']==1 and c['last_status']==(228 if c['mode'].startswith('stop_')else 224)
for c in stop['cases'][1:]:assert c['commits']==2 and c['last_status']==228
for name in ['transition01','transition02']:
 x=read(temp/('nes-output489-'+name)/'result.json');assert all(c['commits']==20 for c in x['cases'])
seal=[p.read_bytes()for p in a.live.glob('req-*.bin')if p.read_bytes()[0]==3];assert len(seal)==1 and int.from_bytes(seal[0][38:40],'little')==0
before=sum(x['E1_wire_B']for x in old['frames']);after=sum(x['E1_wire_B']for x in audit['frames']);ds=[b['E1_wire_B']-c['E1_wire_B']for b,c in zip(old['frames'],audit['frames'])]
fw=arm/'obj-nes-100/firmware.stm';base=read(ROOT/'analysis/mmc482-verification.json')['FIT']
r={'passed':True,'candidate':'MMC489 / ABI4891','limited_hardware_trial_ready':True,'hardware_verified':False,'physical_FPS':None,'full_physical_acceleration_proven':False,
 'physical_baseline':'MMC485 idle13.55fps,gameplay-inclusive8.22fps unchanged until user trial',
 'ARM':{'firmware_SHA256':sha(fw),'tested_firmware_SHA256':audit['firmware_SHA256'],'all781_linked_function_addresses_sizes_bytes_equal_after_label_change':True,'text':202825,'data':10040,'BSS':18572,'firmware_B':fw.stat().st_size,'Flash_tail_B':212992-fw.stat().st_size,'Flash_delta_vs485_B':108,'Flash_delta_vs488_B':16,'new_global_RAM_B':0,'expired_BG_workspace_B':384,'SEAL_static_stack_B':304,'RUN_workspace_B':31848,'full_stack_IRQ_proof':False,'serializer_instructions':[sum(x['target_instructions']for x in old['frames']),sum(x['target_instructions']for x in audit['frames'])],'window_costs':window['rows'],'final_labels':['NES MMC3 489.nh1','mmc489.nes','fpga_mmc489.bi3','nes-progress-mmc489.txt','nes-budget-mmc489.txt','nes-game-last-mmc489.txt']},
 'wire':{'scope':'ordinary/SEAL E1 for fixed71 raw2 captures; not actual494 gameplay replay or whole shared SPI percentage','E1_B':[before,after],'saved_B':before-after,'saved_per_frame_min_max_mean_B':[min(ds),max(ds),sum(ds)/71],'reduction_percent':100*(1-after/before),'raw_logical_CHR_B':[2048,384]},
 'SNES':{'client_SHA256':sha(client/'sink165.sfc'),'program_SHA256':pins['program_SHA256'],'program_B':5120,'body_B':meta['body_bytes'],'new_context_B':8,'retained_implicit_pattern_cache_B':2,'per_frame_context_B':6,'new_frame_buffer_B':0,'boot_zero_fill_B':4096,'implicit_cache_invalidated_before_mutation':True,'cache_certified_in_successful_display_commit_before_ACK_publication':True,'semantic_checks_preserved_with_dynamic_table_pointer':True,'comparisons':comparisons,'normal_frames_all_pixels_and_full_raw_VRAM_equal':71,'synthetic_transition_suites_frames_each':20,'transition_cases':'1<->2,0/3..7 both banks, poisoned initial VRAM/cache; not valid NES gameplay input replay'},
 'FPGA':{'whole_board_inputs':pins['board_inputs'],'changed':pins['changed'],'FIT':fit,'delta_vs488':{k:fit[k]-prior['FPGA']['FIT'][k]for k in fit},'delta_vs_physical482':{k:fit[k]-base[k]for k in fit},'M9K':51,'remaining_M9K':5,'remaining_LE':15408-fit['LE'],'logical_ROM_reduction_is_not_M9K_reclaim':True,'related_timing_ns':timing,'related_worst_paths':paths,'related_timing_passed':True,'full_reset_CDC_IO_signoff':False,'no_new_timing_exception_or_seed_retry':True,'fit_report_SHA256':sha(a.board/'output_files/board.fit.rpt')},
 'loader_equivalence':loader,'faults':[{'mode':x['mode'],'status':x['last_status'],'commits':x['commits']}for x in faults['cases'][2:]],'transition_STOP':[{'mode':x['mode'],'status':x['last_status'],'commits':x['commits']}for x in stop['cases'][1:]],
 'functional_C_RTL_65816_join':live,'join_raw_count':0,'raw_path_tested_separately':True,'bootbus':boot,'assembly':asm,'programmer':pgm,
 'limits':['Actual65816 plus four-credit2.625Mbps file-aperture model is not a common physical M4/IRQ/ROM timeline','Current C/RTL join is first boot raw0; raw reconstruction and elapsed71 frames are separate bounded tests','No new physical STOP/menu/FPS result; preserve proven485 and request controlled user installation','5KiB logical ROM still uses8 M9Ks inside51 total; no fictitious3-block recovery','Existing full reset/CDC/IO and full ARM stack/IRQ approval remain open'],
 'preserved_failures':['candidate01 copied old digest accidentally; corrected before ARM build','client02 zero literal placed in reserved FF gap; builder assertion caught; immutable header zero used in03','snes01 sandbox TEMP path missing Mesen; explicit --mesen in02+','programmer01 sandbox MinGW system DLL relocation; legitimate native rerun02 PASS','First no-bootclear prototype incurs cold VBlank penalty; current03 preclears forced-blank VRAM and includes cold-reset comparison'],
 'next':'Build fresh paired489 private installer with485/482/476/164/467 byte-preserved restores; user hardware comparison, then use actual phase costs to choose next bottleneck'}
a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'ready':True,'FIT':fit,'timing':timing,'71frame_saved_ms':comparisons[1]['saved_ms'],'Flash_tail':r['ARM']['Flash_tail_B']}))
