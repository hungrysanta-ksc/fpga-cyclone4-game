# SPDX-License-Identifier: MIT
"""Preserve hardware214: successful boot, incomplete51st plan transaction."""
from pathlib import Path
import argparse,json,re,shutil
from analyze_nes_game213 import ROOT,BASE,sha,fields
from decode_nes_minreject180 import decode

def main():
    p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);raw=a.out/'raw';raw.mkdir();pins={}
    for kind in ['progress','game-last','budget']:
        n=f'nes-{kind}-214.txt';shutil.copyfile(a.inputs/n,raw/n)
        assert sha(a.inputs/n)==sha(raw/n)
        pins[n]=dict(bytes=(raw/n).stat().st_size,sha256=sha(raw/n))
    f=fields(raw/'nes-game-last-214.txt');b=fields(raw/'nes-budget-214.txt')
    stages=[dict(re.findall(r'(\w+)=(\S+)',s)) for s in (raw/'nes-progress-214.txt').read_text().splitlines() if s.strip()]
    assert [int(s['seq']) for s in stages]==list(range(100))
    by={s['stage']:s for s in stages};duration=int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
    assert duration==9090 and f['candidate']=='NES-GAME-214'
    assert f['loaded_bytes']==f['compared_bytes']=='393216'
    for k in ['verified','stop_ok','base_restored','safe_to_reload','spc_unmute_confirmed']:assert f[k]=='1',k
    for k in ['verify_error','run_rom_error','run_stop_error','native_receiver_error','native_video_error','native_sink_error','sink_window_error','trace_aborts']:assert f[k]=='0',k
    assert f['run_first_error']==f['run_error']=='4' and f['native_result']=='5'
    assert f['plan_error']=='4' and f['plan_sent']=='1' and f['plan_end']=='0'
    assert f['trace_begins']==f['trace_ends']==f['trace_commits']=='51'
    assert f['native_frames']=='50' and f['native_generation']=='68' and f['trace_generation']=='69'
    assert f['sink_window_sent']==f['sink_window_retired']=='912'
    assert b['boot_reason']=='1' and b['boot_ticks']=='5' and b['boot_polls']=='430'
    assert b['boot_first_hex']=='01000000' and b['boot_last_hex']=='0104a903' and b['boot_signals_hex']=='00000606'
    names='frames recv plan seal maxgap ingress e8 e9 e0 e1 other plans out slot_hits reserved0 reserved1 bg obj mapdirty'.split()
    assert b['budget_schema']==b['boot_schema']=='214' and b['columns']==','.join(names)
    bins=[]
    for i in range(12):
        parts=b[f'b{i:02}'].split(',');assert len(parts)==len(names) and all(len(v)==8 for v in parts)
        row=dict(zip(names,(int(v,16) for v in parts)));row['scene']='UNCLASSIFIED';bins.append(row)
    totals={k:sum(x[k] for x in bins) for k in names if k!='maxgap'}
    clocked=sum(totals[k] for k in ['ingress','e8','e9','e0','e1','other'])
    assert totals['frames']==50 and clocked==int(f['native_wire_bytes'])==808805
    assert totals['recv']==255 and totals['plan']==483 and totals['seal']==149
    assert b['open']=='1' and b['failed_transfers']=='0'
    src=BASE/'probes/nes-startup214/arm02/src'
    source_names=['nes_boot214.inc','nes_native_runtime165.c','nes_plan_service200.c','nes_plan_service200.h','nes_planner211.c']
    release=json.loads((BASE/'probes/nes-startup214/release01/result.json').read_bytes())
    r=dict(candidate=214,analysis_checks_passed=True,raw_inputs=pins,fields=f,budget=b,bins=bins,totals=totals,stages=stages,
        episodes=decode((raw/'nes-game-last-214.txt').read_text()),source_pins={n:sha(src/n) for n in source_names},
        package=release['zip_sha256'],
        hardware=dict(user_report='이번에는 실행은 성공했는데 60초 플레이는 되지 않고 스테이지 선택 화면으로 진입시에 팅겼어. 메뉴로 복귀는 정상이야.',
            startup_succeeded=True,visible_menu_restored=True,early_exit=True,audible_sound_confirmed=False,scene_timestamps_known=False),
        boot=dict(reason='READY',polls=430,ticks=5,approximate_ms=50,first_status='01000000',last_status='0104a903',signals='00000606',
            reset_asserted=False,fpga_done=True,mcu_ready=True,spc_ack='a9',observed_read_flags=4,
            prior213_fixed=False,note='Successful physical boot has program-read flag4 without vector bits; do not require flags7 or equate missing vector flags with CPU inactivity.'),
        terminal=dict(display_phase_including_boot_and_stop_ms=duration,last_display_elapsed_ms=8850,
            displayed=50,displayed_generation=68,received_committed_generation=69,received_commits=51,
            native_reason='DISPLAY',run_error=4,plan_error=4,locally_sent_batches=1,plan_finished=False,
            phase='51st frame before display: plan finish/flush/status validation; not final frame retirement or60s deadline',
            failed_transfer_callbacks=0,raw_e8_response_present=False,exact_root_cause_known=False,
            possibilities=['E8 header/version/reserved-field or CRC mismatch','fault/retiring/reserved status bits',
                'accepted-batch count mismatch','invalid descriptor marker or unexpected descriptor bytes when absent',
                'unexpected END observed while flushing pending plans'],
            not_proven=['sound-triggered game fault','ROM fault','SNES final display-ACK mismatch','SPI electrical corruption','specific mapper bug','insufficient throughput']),
        metrics=dict(completed_receive_ms=2550,completed_plan_ms=4830,completed_seal_ms=1490,
            last_display_ms=8850,clocked_bytes=clocked,slot_hit_count=totals['slot_hits'],
            emitted_plan_count=totals['plans'],planned_output_bytes=totals['out'],
            max_completed_display_gap_ms=max(x['maxgap'] for x in bins)*10,fps60_proven=False,
            caveat='Includes partial51st frame bytes; completed phase timers omit failed plan finish. slot hits are counts, not bytes. Different short scenes from210: no controlled speedup/FPS comparison.'),
        next='Preserve first failing E8 reply20B + failure predicate and finish/flush phase in existing budget log; reproduce short/sparse one-batch frames and generation/END/accepted transitions using actual213 C plus selected207 RTL before next paired trial. Keep existing CRC/count/lease/display checks and STOP; no blind retries/timeouts/cache disable/newFIT or repeat214/044.',
        new_package=False,new_fit=False,public_source_sha256=sha(Path(__file__)))
    text=json.dumps(r,ensure_ascii=False,indent=2)+'\n';(a.out/'analysis.json').write_text(text,encoding='utf8')
    (ROOT/'analysis/game214-hardware01-verification.json').write_text(text,encoding='utf8')
    (a.out/'progress.json').write_text(json.dumps(dict(status='boot_passed_runtime_plan_status_failed',root_cause_known=False,next=r['next']),indent=2)+'\n')
    print(json.dumps(dict(boot=r['boot'],terminal=r['terminal'],metrics=r['metrics']),ensure_ascii=False))
if __name__=='__main__':main()
