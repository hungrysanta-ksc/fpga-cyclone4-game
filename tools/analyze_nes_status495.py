# SPDX-License-Identifier: MIT
"""495 structural/functional/cost ledger. No physical gain or rollout approval."""
import argparse,json,csv,re,collections
from pathlib import Path
from nes_status495 import ROOT,sha
def load(p):return json.loads(p.read_text())
def timing(board):
    result={}
    for view in ['implementation','nominal']:
        rows=list(csv.DictReader((board/(view+'-paths204.tsv')).open(),delimiter='\t'))
        rows=[r for r in rows if(r['from_clock']=='nes')==(r['to_clock']=='nes')]
        result[view]={k:min(float(r['slack'])for r in rows if r['kind']==k)for k in ['setup','hold']}
    return result
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['local','runs','board','arm','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();q=a.local;t=a.runs
    arm=load(q/'arm-test02/result.json');rtl=load(t/'nes-status495-rtl02/result.json');boot=load(t/'nes-status495-boot01/result.json');live=load(t/'nes-status495-live03/result.json');schedule=load(t/'nes-status495-schedule01/result.json')
    assert all(x['passed']for x in [arm,rtl,boot,live,schedule])
    pins=load(q/'candidate03/result.json');old=load(ROOT/'analysis/output489-verification.json')['FPGA']['whole_board_inputs']
    for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
    assert sha(a.board/'sink-program.hex')==old['sink-program.hex']
    assert sha(a.arm/'obj-nes-100/firmware.stm')==arm['firmware_SHA256']
    assert sha(a.arm/'nes_sink_window184.c')==sha(t/'nes-status495-live03/nes_sink_window184.c')
    assert sha(a.board/'nes_sink_spi165.sv')==rtl['SPI_SHA256']
    assert sha(a.board/'nes_rom_boot.sv')==boot['new_SHA256']
    summary=(a.board/'output_files/board.fit.summary').read_text();assert 'Fitter Status : Successful'in summary
    LE=int(re.search(r'Total logic elements : ([\d,]+)',summary)[1].replace(',',''));comb=int(re.search(r'Total combinational functions : ([\d,]+)',summary)[1].replace(',',''));ff=int(re.search(r'Dedicated logic registers : ([\d,]+)',summary)[1].replace(',',''))
    memory=int(re.search(r'Total memory bits : ([\d,]+)',summary)[1].replace(',',''))
    m9k=int(re.search(r'; M9Ks\s*; (\d+) /',(a.board/'output_files/board.fit.rpt').read_bytes().decode('latin-1'))[1]);assert memory==264800 and m9k==51
    ts=timing(a.board);assert all(v>=0 for x in ts.values()for v in x.values())
    diffs=[]
    for i in [0,2]:
        b,c=schedule['rows'][i:i+2];assert b['requests_SHA256']==c['requests_SHA256']
        diffs.append({'phase_masterclocks':b['phase_masterclocks'],'before_ms':b['elapsed_ms'],'after_ms':c['elapsed_ms'],'saved_ms':b['elapsed_ms']-c['elapsed_ms']})
    totals=collections.Counter();calls=collections.Counter()
    for row in csv.DictReader((t/'nes-status495-profile02/compact-normal/profile495.csv').open()):totals[row['name']]+=int(row['inclusive_master_clocks']);calls[row['name']]+=1
    fixture=[]
    for x in arm['pairs']:
        fixture.append({'busy_polls':x['delay_polls'],'wire_saved_B':x['wire_saved_B'],'before_instructions':x['baseline']['instructions'],'after_instructions':x['candidate']['instructions']})
    size=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
    r={'passed':True,'scope':__doc__,'candidate':'status495 experimental','physical_baseline':'analysis/hardware494-mmc493.json',
       'selected_for_hardware':False,'physical_FPS':None,'full_path_acceleration_proven':False,'new_installer':False,
       'ABI':{'progress_command':'EB','progress_B':8,'progress_header':'F8','progress_CRC8_bytes':6,'full_ACK_command':'E0','full_ACK_B':20,'SNES_ABI':'4891','SNES_program_unchanged':True,'separate_snapshot_or_CRC_FSM_added':False},
       'ARM':{'firmware_SHA256':arm['firmware_SHA256'],'text_B':202853,'data_B':10040,'BSS_B':18572,'firmware_B':size,'Flash_free_B':212992-size,'Flash_growth_B':52,'new_global_RAM_B':0,'window_function_static_stacks_unchanged':True,'full_stack_IRQ_proof':False,'ownership_cases':len(arm['ownership']),'CRC_progress_full_ACK_negatives':len(arm['negative_cases']),'fixed_poll_fixtures':fixture,'no_pressure_no_wait_extra_wire_B':8},
       'FPGA':{'whole_board_inputs':pins['board_inputs'],'LE':LE,'comb':comb,'FF':ff,'logical_RAM_bits':memory,'M9K':m9k,'LE_remaining':15408-LE,'delta_vs493':{'LE':LE-15272,'comb':comb-14078,'FF':ff-8392,'RAM_bits':0},'LE_delta_is_packing_not_deleted_logic':True,'related_timing_ns':ts,'SDC_and_seed_unchanged':True,'full_reset_CDC_IO_signoff':False},
       'guard_proofs':{'queue_SPI_phase_wrap_cases':rtl['rows'],'boot_valid_reads_per_phase':boot['valid_reads_each_phase'],'boot_cancel_fault_per_phase':boot['cancel_fault_cases_each_phase'],'sticky_fault_cases':boot['sticky_cases'],'negative_gate_controls':boot['negative_controls'],'owned_pins_and_valid_read_edges_equal':True,'loaded_state_seeded':True,'full_384KiB_reload_repeated':False},
       'joint':{'source_ROM_SPI_hostC_65816_STOP_passed':True,'ARM_window_source_matches':True,'commits':live['consumer']['commits'],'ACKs':live['consumer']['acks'],'retired_chunks':live['consumer']['retired_chunks'],'first_pixels_SHA256':live['frame_sha256'],'physical_common_clock':False},
       'conditional_SNES_wire_schedule':{'frames':12,'same_payload_pixels_and_SNES':True,'comparisons':diffs,'busy_polls_ARM_IRQ_ROM_not_included':True,'one_bulk_packet_per_recorded_plan_fixture':True},
       'unchanged_SNES_profile':{'frames':12,'inclusive_ms':{k:v/21477.272 for k,v in totals.items()},'calls':dict(calls),'nested_do_not_sum':True},
       'earlier_failed_fit':{'source':'compact progress only,no direct-check boundary','related_timing_ns':timing(t/'nes-status495-board01'),'selection':'rejected,not seed retried'},
       'decision':'Keep physical493. Compact progress functional and fits,but measured conditional display schedule is unchanged/slightly phase-dependent. No new hardware trial until actual ARM busy-poll +real chunk ownership/65816 schedule is connected.',
       'next':['Bind actual ARM progress/credit polling and real193 coalesced chunks to the consumer timeline;the current CPU fixture emits one bulk packet per plan.','Separate immutable packet/header/ACK service from SEAL upload/VBlank using same input;use whole final display time,not wire reductions or nested totals.','Retain validated compact progress/direct-check as experimental inputs,not production;do not reintroduce held word image or alter CRC/STOP/finalACK/menu.']}
    profile=load(q/'profile02.json');assert profile['firmware_SHA256']==arm['baseline_SHA256']
    r['baseline_ARM_instruction_profile']={'scope':profile['scope'],'input_SHA256':profile['input_SHA256'],'rows':[]}
    for row in profile['rows']:
        r['baseline_ARM_instruction_profile']['rows'].append({'frame':row['frame'],'receive_instructions':row['receive_instructions'],'planner_instructions':row['planner_instructions'],'top_functions':{k:sorted(v.items(),key=lambda x:-x[1])[:5]for k,v in row['counts'].items()}})
    observed=load(ROOT/'analysis/hardware494-mmc493.json')['runs'][0];count=observed['quiet_nested']['FINAL_ACK']['calls'];n=observed['display']['completed']
    r['counter_frozen_sensitivity_only']={'assumption':'Same FINAL_ACK wait-call count,8B progress plus one20B full ACK per completed frame;not a prediction after polling cadence changes','wire_saved_B_per_display':(12*count-20*n)/n,'wire_saved_ms_per_display':(12*count-20*n)/n*8/2625000*1000,'not_full_path_gain':True}
    a.out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps({'passed':True,'cost':r['FPGA']['delta_vs493'],'Flash_free':212992-size,'schedule':diffs,'hardware_selected':False}))
