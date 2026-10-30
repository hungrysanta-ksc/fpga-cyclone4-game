# SPDX-License-Identifier: MIT
"""MMC502 receipt: actual whole-run costs, retained capture history, no paired-scene claim."""
import argparse,json
from pathlib import Path
from analyze_nes_supply485_hardware import analyse,sha,fields
from audit_nes499 import capture_evidence
ROOT=Path(__file__).resolve().parents[1]

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['receipt','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    receipt=json.loads((a.receipt/'receipt.json').read_text())
    for name,h in receipt.items():
        f=a.receipt/'run01'/name;assert f.stat().st_size==h['bytes'] and sha(f)==h['SHA256']
    termination=json.loads((a.receipt/'termination01/result.json').read_text());assert termination['passed']
    release=json.loads((ROOT/'analysis/capture502-release-verification.json').read_text())
    assert termination['firmware_SHA256']==release['ARM']['firmware_SHA256']
    r=analyse(a.receipt/'run01',502);n=r['display']['completed'];ops=r['driver_ops_nested']
    b=fields((a.receipt/'run01/nes-budget-mmc502.txt').read_text())
    body={k:ops[k]['bytes']-h*ops[k]['calls'] for k,h in [('D1',3),('E1',19),('E9',8)]}
    assert body['D1']==sum(v['d1_payload']for v in r['bins'])
    queryB=sum(ops[k]['bytes']for k in ['D0','E0','E8'])/n
    r.update(boot_ready_ms=int(b['boot_ticks'])*10,boot_ready_polls=int(b['boot_polls']),
             command_body_projection={k+'_B_per_display':v/n for k,v in body.items()},
             five_second_frame_start_counts=[v['frames']for v in r['bins']],
             wire_ms_per_display=r['wire_bytes']/n*8/2625,
             queries_per_display={k:ops[k]['calls']/n for k in ['D0','E0','E8']},
             status_queries=dict(B_per_display=queryB,fraction_of_wire=queryB/(r['wire_bytes']/n),wire_ms_per_display=queryB*8/2625,driver_ms_per_display=sum(ops[k]['ms_per_completed_display']for k in ['D0','E0','E8'])),
             nonquery_wire_projection_ms=(r['wire_bytes']/n-queryB)*8/2625,
             command_body_wire_ms=sum(body.values())/n*8/2625,
             mean_gap_to_60Hz_ms=r['display']['mean_ms']-1000/60)
    oldfile=ROOT/'analysis/hardware494-mmc493.json';old=json.loads(oldfile.read_text())['runs'][0]
    comparison=dict(baseline='MMC493',evidence='analysis/hardware494-mmc493.json',SHA256=sha(oldfile),
                    matched_scene_or_inputs=False,causal_speedup_percent_proven=False,old_display=old['display'],
                    observed_fps_delta_percent=(r['display']['fps']/old['display']['fps']-1)*100,
                    observed_mean_ms_delta=r['display']['mean_ms']-old['display']['mean_ms'],
                    phase_ms_delta={k:v['ms_per_completed_display']-old['DWT_phases_nested'][k]['ms_per_completed_display']for k,v in r['DWT_phases_nested'].items()},
                    D0_calls_old=old['driver_ops_nested']['D0']['calls'],D0_calls_new=ops['D0']['calls'],
                    D0_calls_per_display_old=old['queries_per_display']['D0'],D0_calls_per_display_new=ops['D0']['calls']/n)
    capture=capture_evidence((a.receipt/'run01/nes-game-last-mmc502.txt').read_text())
    result=dict(schema_version=1,trial=502,trial_family='MMC',hardware_run_passed=True,
                selected_rate_scope='One60.07s mixed-input run;no supplied scene timing or video;not level-only FPS',runs=[r],source_files=receipt,
                user_report=dict(load_normal=True,menu_return_normal=True,subjective_improvement_clear=True,omit_RESTORE_from_future_trials=True),
                selected_package='analysis/capture502-package.json',selected_implementation_commit='485a946fba53eb0c70b72c5147dcaf4a1f70629c',
                capture_evidence=capture,comparison=comparison,termination_test=termination,
                hardware_labels_profile_match=True,firmware_hash_in_received_logs=False,
                whole_FPGA_cost_evidence='analysis/capture502-verification.json',new_firmware_or_Quartus=False,
                **{'60Hz_achieved':False},
                decision='Select502 functional hardware baseline. Retained history no longer has fetch01/04/06;no proof of all-frame capture health. Proceed to A2 byte and late-DMA schedule budget;keep independent checks/STOP/finalACK/VBlank/menu.',
                limits=['493/502 runs have different unsynchronized inputs;10.61% is observed whole-run rate difference,not isolated causal speedup.',
                        'History contains4reject/4recovery episodes,all error fields zero;reject candidate mask0/recovery24. Candidate mask is not error-time mask;no proof of entire rejection cause,rate or duration.',
                        'DWT phases include actual IRQ/guard/wait;SPI operations and quiet are nested and must not be added to phase totals.',
                        'Last637th input is incomplete and excluded from636 displays. Linked guard reproduction is modeled clock/SPI,not physical final-instant replay.',
                        'No level-only FPS,p95,continuous capture no-loss,NES real-time speed,whole reset/CDC/IO/IRQ stack or MMC4/5 approval.',
                        'Existing ZIP/verification snapshots and local user backups remain unchanged;future installers omit RESTORE folders.'])
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(display=r['display'],phases={k:v['ms_per_completed_display']for k,v in r['DWT_phases_nested'].items()},wire=r['wire_ms_per_display'],nonquery=r['nonquery_wire_projection_ms'],body=r['command_body_wire_ms'],queries=r['status_queries'],comparison=comparison,quiet={k:v['ms_per_completed_display']for k,v in r['quiet_nested'].items()},bins=r['five_second_frame_start_counts'])))
