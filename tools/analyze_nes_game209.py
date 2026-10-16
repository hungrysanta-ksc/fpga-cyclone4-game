# SPDX-License-Identifier: MIT
"""Record original209 hardware logs and bounded whole-run comparison to186.
No instantaneous/scroll FPS, poll split or controlled speedup inference.
"""
from pathlib import Path
import argparse,json,re,shutil
from nes_board204 import ROOT,BASE,sha
from decode_nes_minreject180 import decode

def main():
 p=argparse.ArgumentParser();p.add_argument('--inputs',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 raw=a.out/'raw';raw.mkdir();hashes={}
 for n in ['nes-progress-209.txt','nes-game-last-209.txt']:
  shutil.copyfile(a.inputs/n,raw/n);assert sha(a.inputs/n)==sha(raw/n);hashes[n]=dict(bytes=(raw/n).stat().st_size,sha256=sha(raw/n))
 text=(raw/'nes-game-last-209.txt').read_text();lines=[x for x in text.splitlines() if x];fields=dict(x.split('=',1) for x in lines);assert len(fields)==len(lines)
 stages=[dict(re.findall(r'(\w+)=(\S+)',x)) for x in (raw/'nes-progress-209.txt').read_text().splitlines() if x.strip()]
 assert [int(x['seq']) for x in stages]==list(range(100));by={x['stage']:x for x in stages}
 assert fields['candidate']=='NES-GAME-209'
 assert all(fields[n]=='0' for n in ['verify_error','run_error','run_rom_error','run_first_error','run_stop_error','native_sink_error','native_video_error','sink_window_error','plan_error','trace_aborts'])
 assert all(fields[n]=='1' for n in ['verified','run_passed','stop_ok','base_restored','safe_to_reload','spc_unmute_confirmed','native_result'])
 assert fields['native_receiver_error']=='23' and fields['trace_begins']=='206'
 assert fields['trace_ends']==fields['trace_commits']==fields['native_frames']=='205'
 assert fields['sink_window_sent']==fields['sink_window_retired']=='7911' and fields['sink_window_flags']=='2' and fields['sink_window_ack']=='1'
 assert fields['plan_sent']==fields['plan_end']=='0'
 ms=int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms']);assert ms==60060
 tick=int(fields['profile_tick_ms']);n=int(fields['native_frames'])
 now=dict(duration_ms=ms,display_completed=n,display_completed_per_s=n*1000/ms,amortized_display_ms=ms/n,
  receive_ms=int(fields['profile_receive_ticks'])*tick,build_stage_ms=int(fields['profile_build_stage_ticks'])*tick,seal_ack_ms=int(fields['profile_seal_ack_ticks'])*tick,
  transactions=int(fields['native_transactions']),clocked_bytes=int(fields['native_wire_bytes']),window_packets=int(fields['sink_window_sent']))
 now['accounted_ms']=sum(now[k] for k in ['receive_ms','build_stage_ms','seal_ack_ms']);now['unattributed_ms']=ms-now['accounted_ms']
 old=ROOT/'analysis/game186-hardware01-verification.json';before=json.loads(old.read_bytes())['comparison']['current186']
 pct={k:(now[k]/before[k]-1)*100 for k in ['display_completed_per_s','receive_ms','build_stage_ms','seal_ack_ms','transactions','clocked_bytes','window_packets']}
 src=BASE/'probes/nes-binding209/arm01/src';names=['nes_native_runtime165.c','nes_native_runtime165.h','nes_native165.c','nes_plan_service200.c','nes_sink_window184.c','nes_native_sink165.c']
 sources={k:sha(src/k) for k in names};prep=json.loads((src.parent/'preparation-paired209.json').read_bytes());pins=prep['copied']|prep['changed']|prep['added']
 for k,h in sources.items():assert pins['src/'+k]==h,k
 runtime=(src/names[0]).read_text();receiver=(src/'nes_native165.c').read_text();plan=(src/'nes_plan_service200.c').read_text()
 assert 'if(!s->result)s->result=(uint8_t)reason' in runtime and 'return fail(s,NES_RUNTIME165_DEADLINE)' in runtime
 assert 'if(!fn(ctx,tx,rx,n+3)||crc16(rx+1,n)!=(uint16_t)((rx[n+1]<<8)|rx[n+2]))return fail(s,23)' in receiver
 assert 'p->sent=0;p->finished=false;p->started=false;p->generation=0;return true;' in plan
 result=dict(candidate=209,fields=fields,stages=stages,raw_inputs=hashes,source_pins=sources,episodes=decode(text),
  baseline_sha256=sha(old),comparison=dict(before186=before,current209=now,change_percent=pct,
   scope='Different game inputs/scenes and changed stage contents. Whole-run completion rate is not scroll FPS or CRT refresh; no controlled speedup/CPU-only timings. Clocked bytes include headers/status/polls and exclude direct SNES aperture payload.'),
  hardware=dict(user_report='프레임이 나아진게 느껴졌지만 여전히 스크롤 화면에서의 개선은 미흡했어. 사운드나 컨트롤은 다 정상이였어.',frame_improvement_user_confirmed=True,scroll_stutter=True,sound_user_confirmed=True,control_user_confirmed=True,visible_menu='not explicitly reported; MENU_PREPARED only',video_provided=False,fps60=False,qualitative_scroll_observation=True,paired_scene_measurement=False),
  terminal=dict(primary_result=1,meaning='deadline',duration_ms=ms,receiver_error=23,receiver_error_meaning='D1 transfer callback failure OR payload CRC failure; first runtime deadline pre/post transfer is retained, not independent CRC proof',
   last_display_ms=int(fields['profile_last_display_tick'])*tick,last_display_generation=int(fields['native_generation']),producer_begins=206,producer_commits=205,display_acks=205,
   queue_pending=0,plan_reset_after_retire=True,menu_prepared_ms=int(by['MENU_PREPARED']['elapsed_ms']),initial_display_next_ms=int(by['DISPLAY_NEXT']['elapsed_ms']),
   explanation='Deadline1 with60.06s and next receive attempt23. Queue sent==retired, last sampled ACK1, no plan/sink/window/ROM errors. Does not prove zero historical physical faults; plan_end0/sent0 are cleared after successful retire, not absent END. Screen frames0 is explicitly untrusted telemetry.'),
  interpretation=['Direct tile path sustained205 actual display completions; sound/control preserved by user observation.',
   'Receive stage27.71->12.36s decreases; build now includes plan encode/SPI credit/physical source preparation/chunk sink waits, unlike186 converter/CHR work. Do not label20.88s as CPU compute.',
   'Seal26.48s includes remaining palette/map/raw/window/VRAM/display wait; not26.48s of pure VBlank waiting.',
   '278289 SPI calls but7911 sink packets; no command histogram, so E8/E0/D0 polling share cannot be quantified.',
   'Dynamic slot numbering and same-offset map reuse remain candidates under scrolling; no content/tag cache or per-scene counters in these TXT to prove causality.'],
  next='Use actual scrolling workload to separate E8 plan/source/chunk wait from E0/window/SEAL and map/raw payload/slot churn. Reuse existing capture/replay first; if absent add bounded command/phase counters within existing post-STOP log budget together with next performance change, not generic observer or new FIT loops. Preserve final display ACK, immutable lease, source/core priority, ROM/CHR-RAM validity and memory budgets. No repeat209/044 or pad-only trial requested.',
  new_package=False,new_fit=False,public_source_sha256=sha(Path(__file__)))
 out=json.dumps(result,ensure_ascii=False,indent=2)+'\n';(a.out/'analysis.json').write_text(out,encoding='utf8',newline='\n');(ROOT/'analysis/game209-hardware01-verification.json').write_text(out,encoding='utf8',newline='\n')
 (a.out/'progress.json').write_text(json.dumps(dict(status='hardware_result_recorded',next=result['next'],fps60=False,new_package=False),indent=2)+'\n',encoding='utf8')
 print(json.dumps(dict(now=now,change_percent=pct,episodes=result['episodes']),ensure_ascii=False))
if __name__=='__main__':main()
