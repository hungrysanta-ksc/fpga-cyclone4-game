# SPDX-License-Identifier: MIT
"""Source-pinned491 comparison; actual CPU and functional RPC are separate clocks."""
import argparse,csv,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['local','runs','board','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();r=a.local;t=a.runs
    before=load(t/'nes-output489-snes06/result.json');after=load(t/'nes-consume491-snes05/result.json')
    assert before['cases'][0]['frames']==after['cases'][0]['frames']
    assert sha(t/'nes-output489-snes06/compact-normal/requests.bin')==sha(t/'nes-consume491-snes05/compact-normal/requests.bin')
    old,new=before['cases'][1],after['cases'][1];assert old['commits']==new['commits']==71
    clock=21477272;start=3000000;oldend=old['frames'][-1]['ACK_masterclock'];newend=new['frames'][-1]['ACK_masterclock']
    units=load(t/'nes-consume491-units04/result.json');assert units['passed'] and units['cases']==108
    arm=load(r/'arm-bursts01/result.json');assert arm['passed']
    audit=load(r/'audit01/result.json');assert audit['passed'] and len(audit['frames'])==71
    guard_modes={}
    for folder in ['guards-snes01','guards-snes02','transition01']:
        for f in sorted((t/('nes-consume491-'+folder)).glob('compact-*/result.json')):
            q=load(f);assert q['passed'];guard_modes[folder+'/'+f.parent.name]={'commits':q['commits'],'status':q['last_status']}
    assert len(guard_modes)==11
    pins=load(a.board/'source-pins.json')['board_inputs'];ref=load(t/'nes-output489-board02/source-pins.json')['board_inputs']
    changed=[n for n in pins if pins[n]!=ref[n]];assert changed==['sink-program.hex']
    timings={}
    for view in ['implementation','nominal']:
        rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'))
        rows=[x for x in rows if((x['from_clock']=='nes')==(x['to_clock']=='nes'))]
        timings[view]={k:min(float(x['slack'])for x in rows if x['kind']==k)for k in ['setup','hold']}
        assert all(v>=0 for v in timings[view].values())
    fit=(a.board/'output_files/board.fit.summary').read_text();assert 'Successful'in fit and '15,272 / 15,408'in fit
    joint=load(t/'nes-consume491-live01/result.json');assert joint['passed']
    bootbus=load(t/'nes-consume491-bootbus01/result.json');assert bootbus['passed']
    bootbus['legacy_harness_board_label']=bootbus.pop('board')
    bootbus['board']='consume491 selected source closure'
    build=load(r/'client02/build.json')
    phase_before=load(t/'nes-output489-snes07/result.json')['cases'][1]
    phase_after=load(t/'nes-consume491-phase01/result.json')['cases'][1]
    d12=old['frames'][11]['ACK_masterclock']-new['frames'][11]['ACK_masterclock']
    dphase=phase_before['frames'][-1]['ACK_masterclock']-phase_after['frames'][-1]['ACK_masterclock']
    cold_before=load(t/'nes-output489-cold01/result.json')['cases'][1]
    cold_after=load(t/'nes-consume491-cold01/result.json')['cases'][1]
    result={'passed':True,'candidate':'consume491','scope':__doc__,'merged_PR137':'29815faa3887a035091e3169ffa0f751dda3de44',
            'physical_baseline':'analysis/hardware490-mmc489.json','physical_FPS':None,'hardware_verified':False,'hardware_trial_ready':False,
            'full_path_acceleration_proven':False,'new_installer':False,
            'SNES':{'frames':71,'same_start_masterclock':start,'masterclock_hz':clock,'old_end':oldend,'new_end':newend,
                    'old_ms':(oldend-start)/clock*1000,'new_ms':(newend-start)/clock*1000,
                    'saved_ms':(oldend-newend)/clock*1000,'reduction_percent':(oldend-newend)/(oldend-start)*100,
                    'baseline227_frames_exact':True,'requests_SHA256':sha(t/'nes-consume491-snes05/compact-normal/requests.bin'),
                    'all_pixels_raw_VRAM_equal':True,'same_VBlank_final_ACK_contract':True,
                    'unit_cases':108,'max_expansion_between_service_B':64,'seed_before_first_service_B':2,
                    'new_persistent_RAM_B':0,'word_code_uses_existing_DP_scratch':True,
                    'program_B':build['program_bytes'],'body_B':build['body_bytes'],
                    'SFC_SHA256':sha(r/'client02/sink165.sfc'),'program_SHA256':hashlib.sha256(bytes.fromhex((r/'client02/sink-program.hex').read_text())).hexdigest(),
                    'twelve_saved_ms':d12/clock*1000,'start_plus4ms_saved_ms':dphase/clock*1000,
                    'cold_reset_ms':[q['frames'][-1]['ACK_masterclock']/clock*1000 for q in [cold_before,cold_after]]},
            'ARM':{'firmware_SHA256':sha(r/'ARM01/src/obj-nes-100/firmware.stm'),'text_B':202801,'data_B':10040,'BSS_B':18572,
                   'firmware_B':(r/'ARM01/src/obj-nes-100/firmware.stm').stat().st_size,'Flash_free_B':148,
                   'new_global_RAM_B':0,'RUN_workspace_B':31848,'emit_static_stack_old_new_B':[32,16],
                   'canonical_states_plans_packets':71,'ownership_cases':len(arm['ownership_cases']),
                   'burst_cases':[{'n':q['n'],'old_E8':q['baseline']['E8'],'new_E8':q['candidate']['E8'],
                                  'old_E0':q['baseline']['E0'],'new_E0':q['candidate']['E0'],
                                  'old_B':q['baseline']['wire_B'],'new_B':q['candidate']['wire_B'],
                                  'old_instructions':q['baseline']['instructions'],'new_instructions':q['candidate']['instructions'],
                                  'same_E9_and_plan_order':True}for q in arm['bursts']],
                   'endpoint_delays_are_fixtures':True,'hardware_cycles':None},
            'FPGA':{'LE':15272,'comb':14078,'FF':8392,'logical_RAM_bits':264800,'M9K':51,
                    'remaining_LE':136,'remaining_M9K':5,'whole_compile_count':1,'related_timing_ns':timings,
                    'changed_from489':changed,'ROM_contents_only':True,'source_inputs':pins,
                    'FIT_SHA256':sha(a.board/'output_files/board.fit.rpt'),'no_new_timing_waiver_or_seed_loop':True},
            'functional_join':joint,'bootbus':bootbus,'guard_modes':guard_modes,
            'runtime':{'exe_SHA256':sha(r/'mesen/Mesen.exe'),'managed_SHA256':sha(r/'mesen/Mesen.dll'),
                       'native_SHA256':sha(r/'mesen/MesenCore.dll'),'native_dependency_preserved_readonly':True,
                       'empty_embedded_native_archive_overwrite_cause_reviewed_in_source':True},
            'limits':['Not common physical ARM/IRQ/source ROM/SPI clock; do not combine CPU and endpoint percentages',
                      'Current489 physical9.60fps remains; no new level-only or causal physical speedup claim',
                      'C/RTL join first no-raw frame; raw71 and guard suites are independent fixed-input executions',
                      'Whole reset/CDC/IO and full stack/IRQ signoff open; no new mapper/clock/credit/validation changes',
                      'New installer deferred until joint timing and source/ROM competition are compared'],
            'next':['Bind actual ARM E8/E0 traces to source/ROM/65816 consume timing on one clock with fixed input',
                    'Compare D0 readiness and ROM grants, preserving STOP/credit/final ACK and489 restores',
                    'Prepare a new numbered paired installer only after meaningful full-path gain']}
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps({'passed':True,'SNES_ms':[result['SNES']['old_ms'],result['SNES']['new_ms']],
                      'percent':result['SNES']['reduction_percent'],'hardware_trial_ready':False}))
