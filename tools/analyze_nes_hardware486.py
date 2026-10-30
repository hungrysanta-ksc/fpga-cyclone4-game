# SPDX-License-Identifier: MIT
"""Two485 physical workloads; keep idle and gameplay-inclusive rates separate.

Current-format command-body wire projection excludes polling/framing, but
includes the final unfinished capture. It is not a universal60Hz impossibility
proof. Video observations are manual sampled-frame review, not pixel/FPS proof.
"""
import argparse
import json
from pathlib import Path
from analyze_nes_supply485_hardware import analyse,sha

ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--receipt',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
a=p.parse_args();d=a.receipt
termination=json.loads((d/'termination01/result.json').read_text(encoding='utf8'));assert termination['passed']
video=json.loads((d/'video/metadata.json').read_text(encoding='utf8'))
receipt=json.loads((d/'receipt.json').read_text(encoding='utf8'))
rows=[]
for i,condition in [(1,'user: no stage entry, left running'),(2,'user: entered first level and played; includes initial title/world map')]:
    r=analyse(d/f'run0{i}',485);n=r['display']['completed'];op=r['driver_ops_nested']
    totals={k:sum(v[k] for v in r['bins']) for k in r['bins'][0] if k!='index' and k!='maxgap'}
    source=op['D1']['bytes']-3*op['D1']['calls']
    output=op['E1']['bytes']-19*op['E1']['calls']
    plan=op['E9']['bytes']-8*op['E9']['calls']
    body=(source+output+plan)/n;budget=2625000/8/60
    assert totals['d1_payload']==source
    r.update(run_id=f'run0{i}',condition=condition,user_confirmed_load_and_menu_return=True,
             mean_gap_to_60Hz_ms=r['display']['mean_ms']-1000/60,
             source_files={name:v for name,v in receipt.items() if name.endswith(f'-{i}차.txt')},
             coarse_ms_per_display={'planner_minus_callbacks':(totals['planner_ticks']-totals['callback_ticks'])*10/n,
                                   'begin':totals['begin_ticks']*10/n,'finish':totals['finish_ticks']*10/n,
                                   'note':'10ms ticks and unfinished attempt; not exact per-frame CPU cycles'},
             command_body_projection={'source_D1_B_per_display':source/n,'output_E1_B_per_display':output/n,
                                      'plan_E9_B_per_display':plan/n,'total_B_per_display':body,
                                      'wire_ms_at_current_clock':body*8/2625000*1000,'60Hz_body_budget_B':budget,
                                      'reduction_fraction_to_wire_only_60Hz':max(0,1-budget/body),
                                      'scope':'D1 minus3B/call, E1 minus19B/call, E9 minus8B/call; excludes polling/framing; finite-run total includes unfinished final capture. Encoding and workload may change.'},
             wire_ms_per_display=r['wire_bytes']/n*8/2625000*1000,
             queries_per_display={k:op[k]['calls']/n for k in ['D0','E0','E8']},
             changed_map_granules_per_display=totals['mapdirty']/n,
             five_second_bins={'frame_start_counts':[v['frames'] for v in r['bins']],
                               'seal_ms_per_completed_display':[v['seal']*10/v['frames'] if v['frames'] else None for v in r['bins']],
                               'note':'Frame-start buckets, not precise scene FPS/p95 or exact video alignment'})
    rows.append(r)
result={'schema_version':1,'trial':485,'trial_family':'MMC','hardware_run_passed':True,
        'scope':__doc__,'selected_rate_scope':'run02 whole60.07s including title/world-map and first-level gameplay; not level-only FPS',
        'runs':[rows[1]],'other_runs':[rows[0]],'do_not_pool_different_workloads':True,
        'selected_package':'analysis/supply485-package.json','selected_implementation_commit':'3188344f37568eef56e514c27a586d82dc45734f',
        'hardware_labels_profile_match':True,'firmware_hash_in_received_logs':False,
        'video':{'source_name':video['source_name'],'source_SHA256':video['source_SHA256'],'bytes':video['bytes'],
                 'duration_s':video['metadata']['duration'],'camera_fps':video['metadata']['fps'],
                 'sample_times_seconds':video['sample_times_seconds'],'sample_frame_SHA256':video['frame_SHA256'],
                 'manual_review_observed':['title','world map','first level','Mario position changes/jumps','scrolling','dark transition near clip end'],
                 'menu_frame_confirmed_by_video_samples':False,'menu_return_confirmed_by_user':True,
                 'pixel_accuracy_proven':False,'display_FPS_measured_from_video':False,'audio_reviewed':False},
        'termination_test':termination,
        'prior482':{'evidence':'analysis/mmc483-hardware482.json','fps':14.602064602064602,
                    'mean_ms':68.48346636259977,'same_scene_and_input':False,'causal_speedup_claim':False,
                    'source_SHA256':sha(ROOT/'analysis/mmc483-hardware482.json')},
        'performance_decision':'485 whole-path acceleration not established; first-level workload exposes output/SEAL and input/ROM-wait bottlenecks',
        'production_ready_pin':{'MCU_RDY':'external_memory_ready, not native source-packet-ready/progress IRQ',
                                'evidence':'482 fxpak_nes_screen137_top.sv maps out_observe_ready to MCU_RDY; nes_live_joint.sv assigns out_observe_ready=external_memory_ready',
                                'scope':'Do not treat historical367 source-ready IRQ wiring as deployed485 behavior'},
        '60Hz_achieved':False,'new_firmware_or_Quartus':False,
        'next_order':['Separate output command-body/map/HDMA/OAM/manifest byte causes on fixed inputs; retain independent checks',
                      'Compare whole serialized output/65816 consume-validation/VBlank schedule, not only tile planner',
                      'Trace D0 source-ready wait and actual MCU_RDY ownership; no blind wait/CRC bypass',
                      'Controlled same-workload482/485 or next candidate comparison before attributing speedup'],
        'limits':['Different scenes and inputs; no direct482-to485 regression percentage',
                  'Plan/SEAL include waits; op/quiet counters are nested and cannot be subtracted wholesale',
                  'Only averages/buckets, no frame-level p95, capture no-loss or NES real-time-speed proof',
                  'Video sampled manually; camera artifacts and missing frames are not pixel proof',
                  'OBJ error13 accompanied exact deadline/plan-guard signature; standalone capacity failure remains a separate condition']}
a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps({'run01':rows[0]['display'],'run02':rows[1]['display'],'run02_body_wire_ms':rows[1]['command_body_projection']['wire_ms_at_current_clock'],'termination':rows[1]['termination_class']}))
