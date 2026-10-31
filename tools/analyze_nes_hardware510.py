# SPDX-License-Identifier: MIT
"""Physical MMC509 receipt with nested costs and changed phase-boundary caveat."""
import argparse,json
from pathlib import Path
from analyze_nes_supply485_hardware import analyse,sha,fields
from audit_nes499 import capture_evidence
ROOT=Path(__file__).resolve().parents[1]
def read(p):return json.loads(p.read_text(encoding='utf8'))
def enrich(r,b):
    n=r['display']['completed'];ops=r['driver_ops_nested']
    body={k:ops[k]['bytes']-h*ops[k]['calls']for k,h in [('D1',3),('E1',19),('E9',8)]}
    assert body['D1']==sum(v['d1_payload']for v in r['bins'])
    queryB=sum(ops[k]['bytes']for k in ['D0','E0','E8'])/n
    r.update(boot_ready_ms=int(b['boot_ticks'])*10,boot_ready_polls=int(b['boot_polls']),command_body_projection={k+'_B_per_display':v/n for k,v in body.items()},five_second_frame_start_counts=[v['frames']for v in r['bins']],wire_ms_per_display=r['wire_bytes']/n*8/2625,queries_per_display={k:ops[k]['calls']/n for k in ['D0','E0','E8']},status_queries=dict(B_per_display=queryB,fraction_of_wire=queryB/(r['wire_bytes']/n),wire_ms_per_display=queryB*8/2625,driver_ms_per_display=sum(ops[k]['ms_per_completed_display']for k in ['D0','E0','E8'])),nonquery_wire_projection_ms=(r['wire_bytes']/n-queryB)*8/2625,command_body_wire_ms=sum(body.values())/n*8/2625,mean_gap_to_60Hz_ms=r['display']['mean_ms']-1000/60)
    planner=sum(v['planner_ticks']for v in r['bins']);callback=sum(v['callback_ticks']for v in r['bins'])
    r['coarse_planner_observed']=dict(planner_ticks=planner,callback_ticks=callback,exclusive_ms_per_display=(planner-callback)*10/n,tick_ms=10,not_cycle_exact=True,includes_unfinished_attempt=True,CPU_only=False)
    r['raw_group_reuse']=dict(total=int(b['cost_group_total']),reused=int(b['cost_group_reused']),fraction=int(b['cost_group_reused'])/int(b['cost_group_total']))
    return r
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['receipt','baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();receipt=read(a.receipt/'receipt.json')
    for name,h in receipt.items():f=a.receipt/'run01'/name;assert sha(f)==h['SHA256']and f.stat().st_size==h['bytes']
    termination=read(a.receipt/'termination01/result.json');release=read(ROOT/'analysis/service509-release.json')
    assert termination['passed']and termination['firmware_SHA256']==release['firmware_SHA256']
    r=enrich(analyse(a.receipt/'run01',509),fields((a.receipt/'run01/nes-budget-mmc509.txt').read_text()))
    old=read(ROOT/'analysis/hardware503-mmc502.json')['runs'][0];old_again=analyse(a.baseline,502)
    assert all(old[k]==v for k,v in old_again.items()),'502 parser regression'
    old_enriched=enrich(old_again,fields((a.baseline/'nes-budget-mmc502.txt').read_text()))
    comparison=dict(baseline='MMC502',matched_scene_or_inputs=False,causal_speedup_percent_proven=False,old_display=old['display'],observed_fps_delta_percent=(r['display']['fps']/old['display']['fps']-1)*100,observed_mean_ms_delta=r['display']['mean_ms']-old['display']['mean_ms'],phase_ms_delta={k:v['ms_per_completed_display']-old['DWT_phases_nested'][k]['ms_per_completed_display']for k,v in r['DWT_phases_nested'].items()},old_coarse_planner=old_enriched['coarse_planner_observed'],old_raw_group_reuse=old_enriched['raw_group_reuse'],old_wire_B_per_display=old['wire_bytes']/old['display']['completed'],old_body=old['command_body_projection'],old_nonquery_wire_ms=old['nonquery_wire_projection_ms'])
    capture=capture_evidence((a.receipt/'run01/nes-game-last-mmc509.txt').read_text())
    result=dict(schema_version=1,trial=509,trial_family='MMC',hardware_run_passed=True,selected_rate_scope='One60.08s unsynchronized user run;no video or scene timestamps;not first-level-only FPS',runs=[r],source_files=receipt,user_report=dict(load_normal=True,menu_return_normal=True,subjective_improvement='slight,not large'),selected_package='analysis/service509-package.json',selected_implementation_commit='672cc67f2c9a61c4760af8dde172cd29c2f51db2',capture_evidence=capture,comparison=comparison,termination_test=termination,hardware_labels_profile_match=True,firmware_hash_in_received_logs=False,whole_FPGA_cost_evidence='analysis/fault507-verification.json',new_firmware_or_Quartus=False,**{'60Hz_achieved':False},decision='Select509 as latest functional hardware baseline;keep502 rollback. Prioritize ordinary serialization/consume/DMA/final-check/VBlank within43ms SEAL phase,then remaining input payload. Freeze E8/polling/phase/seed microtuning without evidence.',limits=['21percent whole-run rate change is observed,not an isolated same-scene speedup or extrapolation of5.09percent simulation.','508 moved bulk completion wait from plan finish into SEAL progress;phase31.32->14.30ms is not pure ARM compute speedup.','DWT includes IRQ/guard/wait;driver ops and quiet overlap phase counters and must not be summed.','771st committed input was incomplete at60s;770 displays only. Linked guard reproduction uses modeled clock/SPI,not physical-instant replay.','Last12 capture transitions show6reject/6recovery with zero error fields and candidate masks0/24;not whole-run rejection rate or proof all rejects are harmless.','No level-only FPS,p95,continuous no-loss,NES realtime speed,full resetCDCIO/IRQstack or MMC4/5 approval.'])
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps(dict(display=r['display'],phases={k:v['ms_per_completed_display']for k,v in r['DWT_phases_nested'].items()},comparison=comparison,wire=r['wire_ms_per_display'],nonquery=r['nonquery_wire_projection_ms'],body=r['command_body_projection'],quiet={k:v['ms_per_completed_display']for k,v in r['quiet_nested'].items()},planner=r['coarse_planner_observed'],bins=r['five_second_frame_start_counts'])))
