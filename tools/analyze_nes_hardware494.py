# SPDX-License-Identifier: MIT
"""Received493 physical boot recovery and costs; no matched-scene speedup claim."""
import argparse,json
from pathlib import Path
from analyze_nes_supply485_hardware import analyse,sha,fields
from audit_nes499 import capture_evidence

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['receipt','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    receipt=json.loads((a.receipt/'receipt.json').read_text());termination=json.loads((a.receipt/'termination02/result.json').read_text());assert termination['passed']
    package=json.loads((ROOT/'analysis/boot493-package.json').read_text());assert termination['firmware_SHA256']==package['firmware_SHA256']
    for name,rec in receipt.items():
        q=a.receipt/'run01'/name;assert q.stat().st_size==rec['bytes'] and sha(q)==rec['SHA256']
    r=analyse(a.receipt/'run01',493);n=r['display']['completed'];ops=r['driver_ops_nested']
    b=fields((a.receipt/'run01/nes-budget-mmc493.txt').read_text())
    assert b['boot_reason']=='1' and b['failed_transfers']==b['cost_crc_errors']=='0'
    body={k:ops[k]['bytes']-overhead*ops[k]['calls'] for k,overhead in [('D1',3),('E1',19),('E9',8)]}
    assert body['D1']==sum(v['d1_payload']for v in r['bins'])
    hz=2625000;queryB=sum(ops[k]['bytes']for k in ['D0','E0','E8'])/n
    r.update(user_confirmed_load_and_menu_return=True,condition='First-level play included; exact scene/input timeline unknown',
             boot_ready_ms=int(b['boot_ticks'])*int(b['tick_ms']),boot_ready_polls=int(b['boot_polls']),
             command_body_projection={k+'_B_per_display':v/n for k,v in body.items()},
             five_second_frame_start_counts=[v['frames']for v in r['bins']],
             five_second_rates_not_scene_FPS=[v['frames']/5 for v in r['bins']],
             wire_ms_per_display=r['wire_bytes']/n*8/hz*1000,
             queries_per_display={k:ops[k]['calls']/n for k in ['D0','E0','E8']},
             status_queries={'B_per_display':queryB,'fraction_of_wire':queryB/(r['wire_bytes']/n),
                             'wire_ms_per_display':queryB*8/hz*1000,
                             'driver_ms_per_display':sum(ops[k]['ms_per_completed_display']for k in ['D0','E0','E8'])},
             command_body_wire_ms=sum(body.values())/n*8/hz*1000,
             nonquery_wire_projection_ms=(r['wire_bytes']/n-queryB)*8/hz*1000,
             mean_gap_to_60Hz_ms=r['display']['mean_ms']-1000/60,
             strict_termination_test=termination)
    old=json.loads((ROOT/'analysis/hardware490-mmc489.json').read_text())['runs'][0]
    comparison={'baseline_evidence':'analysis/hardware490-mmc489.json','baseline_SHA256':sha(ROOT/'analysis/hardware490-mmc489.json'),'same_scene_and_input':False,
                'causal_speedup_claim':False,'level_only_rate_measured':False,
                'old489':{'display':old['display'],'DWT_phases_nested':old['DWT_phases_nested']},
                'observed_mean_ms_delta':r['display']['mean_ms']-old['display']['mean_ms'],
                'phase_ms_delta':{k:v['ms_per_completed_display']-old['DWT_phases_nested'][k]['ms_per_completed_display']for k,v in r['DWT_phases_nested'].items()},
                'interpretation':'Whole-run rate essentially unchanged. Input/scenes differ; lower receive/plan and higher SEAL costs cannot be causally assigned to query removal.'}
    # Functional RUN/menu success does not establish healthy PPU capture.
    # Keep the original494 receipt immutable; regenerated reports include499.
    capture=capture_evidence((a.receipt/'run01/nes-game-last-mmc493.txt').read_text(encoding='utf8'))
    result={'schema_version':2,'trial':493,'trial_family':'MMC','hardware_run_passed':True,
            'capture_evidence':capture,'current_plan':'docs/nes-audit499-plan.json',
            'selected_rate_scope':'One60.07s run including first-level play; not first-level-only FPS',
            'runs':[r],'other_runs':[],'selected_package':'analysis/boot493-package.json',
            'selected_implementation_commit':'54bdc1fe8521b742944d59bda20294d59716ad90',
            'hardware_labels_profile_match':True,'firmware_hash_in_received_logs':False,
            'user_report':{'load_normal':True,'menu_return_normal':True,'subjective_improvement_slight':True,'first_level_difference_small':True},
            'source_files':receipt,'comparison':comparison,'termination_test':termination,
            'physical_boot_recovered':True,'root_cause_of492_proven':False,'60Hz_achieved':False,
            'new_firmware_or_Quartus':False,'unchanged_candidate_cost_evidence':'analysis/boot493-verification.json',
            'performance_decision':'Keep493 functional baseline;9.57fps is not an established improvement. Capture fetch rejection01/04/06 remains unresolved. Diagnose that boundary before structural transfer/DMA work;menu/CRC success is not capture-health proof.',
            'next_order':['Keep493 working pair/restores;no new installer or unchanged Quartus/Questa runs for this measurement.',
                          'A1:reproduce low/high fetch rejection with PPU render-stop/restart and address/load timing;do not suppress independent checks or infer rejection duration from episode history.',
                          'Trace E0 credit/SEAL ACK quiet and65816 consume-validation alongside E8/D0 supply on fixed inputs;do not add nested times.',
                          'Evaluate joint status/packet round-trip and framing reduction with actual ARM/SPI/IRQ/ROM/65816 cost and136LE/148FlashB budget. Removing all observed status-query wire alone still leaves nonquery projection over16.67ms.',
                          'Require same-start whole-path improvement and boot boundary proof before another paired physical trial;retain independent CRC/STOP/finalACK/VBlank/menu.'],
            'limits':['No identical-scene causal speedup,level-only FPS,frame p95,capture no-loss or NES real-time speed proof',
                      'DWT phases contain IRQ/guard/wait;op and quiet are nested,not removable CPU time',
                      'Counters include unfinished final attempt;projections are observations,not wire impossibility proof',
                      'All driver wire includes shared ancillary70/73 ops;native wire/transactions cover the runtime wrapper and are a different boundary',
                      'Terminal sink2/window3 accepted only with exact deadline/SEAL/one-pending/zero failed-transfer signature and linked execution;not every transport error is benign',
                      'Physical last instant not replayed;new492 FPGA/SNES boot cause unresolved;full reset/CDC/IO/full stack/IRQ not signed off',
                      'Package and old failure/model snapshots remain immutable;new received493 evidence is recorded separately']}
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'display':r['display'],'phases_ms':{k:v['ms_per_completed_display']for k,v in r['DWT_phases_nested'].items()},'queries':r['status_queries'],'wire_ms':r['wire_ms_per_display'],'nonquery_wire_ms':r['nonquery_wire_projection_ms'],'body_wire_ms':r['command_body_wire_ms'],'queries_per_display':r['queries_per_display'],'quiet_ms':{k:v['ms_per_completed_display']for k,v in r['quiet_nested'].items()},'phase_delta':comparison['phase_ms_delta'],'bins':r['five_second_frame_start_counts']}))
