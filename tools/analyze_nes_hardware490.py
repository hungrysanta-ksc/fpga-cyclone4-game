# SPDX-License-Identifier: MIT
"""Analyse received489 physical logs; compare different485 workloads descriptively.

No new firmware, synthesis, identical-scene causal speedup, or level-only FPS.
Phase/op/quiet counters are nested. Five-second bins follow frame starts.
"""
import argparse,json
from pathlib import Path
from analyze_nes_supply485_hardware import analyse,sha

ROOT=Path(__file__).resolve().parents[1]
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();d=a.receipt
    termination=json.loads((d/'termination03/result.json').read_text());assert termination['passed']
    receipt=json.loads((d/'receipt.json').read_text())
    for name,v in receipt.items():
        q=d/'run01'/name;assert sha(q)==v['SHA256'] and q.stat().st_size==v['bytes']
    r=analyse(d/'run01',489);n=r['display']['completed'];ops=r['driver_ops_nested']
    totals={k:sum(v[k] for v in r['bins']) for k in r['bins'][0] if k not in ['index','maxgap']}
    body={k:ops[k]['bytes']-overhead*ops[k]['calls'] for k,overhead in [('D1',3),('E1',19),('E9',8)]}
    assert body['D1']==totals['d1_payload']
    bodyB=sum(body.values())/n;queryB=sum(ops[k]['bytes'] for k in ['D0','E0','E8'])/n
    hz=2625000;budget=hz/8/60
    r.update(run_id='run01',condition='User entered first level; exact entry/exit and input timeline unknown',
             user_confirmed_load_and_menu_return=True,user_reported_first_level_change_small=True,
             source_files=receipt,mean_gap_to_60Hz_ms=r['display']['mean_ms']-1000/60,
             coarse_ms_per_display={'planner_minus_callbacks':(totals['planner_ticks']-totals['callback_ticks'])*10/n,
                                   'begin':totals['begin_ticks']*10/n,'finish':totals['finish_ticks']*10/n,
                                   'note':'10ms frame-start buckets, includes unfinished attempt; not exact CPU cycles'},
             command_body_projection={'source_D1_B_per_display':body['D1']/n,
                                      'output_E1_B_per_display':body['E1']/n,
                                      'plan_E9_B_per_display':body['E9']/n,'total_B_per_display':bodyB,
                                      'wire_ms_at_current_clock':bodyB*8/hz*1000,'60Hz_body_budget_B':budget,
                                      'scope':'D1 minus3B, E1 minus19B, E9 minus8B per call. Excludes framing/status/quiet/CPU/ROM/VBlank; includes unfinished last capture. Below wire-only budget is not60Hz proof.'},
             wire_ms_per_display=r['wire_bytes']/n*8/hz*1000,
             status_queries={'D0_E0_E8_B_per_display':queryB,'fraction_all_driver_wire':queryB/(r['wire_bytes']/n),
                             'wire_ms_per_display':queryB*8/hz*1000,
                             'driver_ms_per_display':sum(ops[k]['ms_per_completed_display'] for k in ['D0','E0','E8']),
                             'note':'Polling overhead observed; current ownership/credit/ACK checks are required, so this is not removable time.'},
             queries_per_display={k:ops[k]['calls']/n for k in ['D0','E0','E8']},
             five_second_bins={'frame_start_counts':[v['frames'] for v in r['bins']],
                               'rates_divided_by_5s':[v['frames']/5 for v in r['bins']],
                               'phase_ms_per_bucket_display':[{k:v[k]*10/v['frames'] for k in ['recv','plan','seal']} for v in r['bins']],
                               'note':'Not scene-aligned FPS, frame p95 or exact completion timestamps'},
             termination_test=termination)
    old=json.loads((ROOT/'analysis/hardware486-gameplay485.json').read_text())
    baseline=old['runs'][0]
    comparison={'baseline_evidence':'analysis/hardware486-gameplay485.json','baseline_SHA256':sha(ROOT/'analysis/hardware486-gameplay485.json'),
                'baseline485':{'display':baseline['display'],'phases':baseline['DWT_phases_nested'],
                               'E1_wire_B_per_display':baseline['driver_ops_nested']['E1']['bytes']/baseline['display']['completed']},
                'idle485_reference':old['other_runs'][0]['display'],
                'same_scene_and_input':False,'causal_speedup_claim':False,
                'reason':'Same ROM and both gameplay-inclusive, but no synchronized input/scene capture. Do not multiply model -7.83% into physical FPS.'}
    result={'schema_version':1,'trial':489,'trial_family':'MMC','hardware_run_passed':True,'scope':__doc__,
            'selected_rate_scope':'One60.08s run including first-level play; not first-level-only FPS',
            'runs':[r],'other_runs':[],'selected_package':'analysis/output489-package.json',
            'selected_implementation_commit':'dc61756153cbaa78159be15860084260530dd3ed',
            'hardware_labels_profile_match':True,'firmware_hash_in_received_logs':False,
            'user_report':{'load_normal':True,'menu_return_normal':True,'subjective_improvement_small':True,'first_level_difference_small':True},
            'comparison':comparison,'termination_test':termination,
            '60Hz_achieved':False,'new_firmware_or_Quartus':False,
            'unchanged_candidate_cost_evidence':'analysis/output489-verification.json',
            'performance_decision':'489 functional hardware success; whole interval9.60fps, first-level improvement not established. Prioritize repeated E0/E8 progress/credit queries and packet consume-validation schedule, then source D0 readiness/ROM overlap.',
            'next_order':[
                'Keep489 paired hardware baseline and485 restores. No new installer for measurement alone.',
                'Trace actual E8 descriptor/E0 consume-credit/ACK owners and65816 packet-read/CRC/manifest/VBlank schedule on fixed input. Compare joint changes with common-start final display, not raw-only time.',
                'Implement only a justified query/progress/consumer scheduling change retaining independent checks, immediate ready handling, guarded STOP/deadline, credit and final ACK. Flash124B and136LE remain hard constraints.',
                'Then inspect D0 source polling versus actual source completion/ROM grants; deployed MCU_RDY means external_memory_ready, not source-ready IRQ.',
                'One matching-source whole Lite compile if RTL changes; new numbered paired trial after meaningful full-path gain, controlled same-scene physical comparison.'
            ],
            'limits':['Different inputs/scenes; no causal485->489 percentage or level-only FPS',
                      'Nested DWT/op/quiet intervals cannot be summed as independent costs or CPU-only time',
                      'screen_frames is explicitly untrusted; completed count is native final-ACK progress',
                      'video14 alone is not benign; exact runtime deadline/plan2/zero errors/one unfinished commit signature checked and actual linked propagation executed',
                      'No frame p95/capture no-loss/NES real-time-speed/full reset CDC IO/full stack IRQ proof',
                      'Original package/functional/timing snapshots remain unchanged; this is received physical evidence']}
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'display':r['display'],'phases_ms':{k:v['ms_per_completed_display'] for k,v in r['DWT_phases_nested'].items()},
                      'command_body_ms':r['command_body_projection']['wire_ms_at_current_clock'],
                      'all_driver_wire_ms':r['wire_ms_per_display'],'causal_speedup':False}))
