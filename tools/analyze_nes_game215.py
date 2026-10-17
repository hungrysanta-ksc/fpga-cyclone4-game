# SPDX-License-Identifier: MIT
"""Two physical215 failures: identical CRC-valid FPGA fault; video review separate."""
from pathlib import Path
import argparse,json,re
from analyze_nes_game213 import ROOT,BASE,sha,fields
from decode_nes_minreject180 import decode
def crc8(b):
 c=0
 for v in b:
  c^=v
  for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
 return c
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args();runs=[]
 for i in (1,2):
  d=a.archive/f'run{i}';raw=d/'raw';pins=json.loads((d/'inputs.json').read_bytes())
  for n,v in pins.items():assert (raw/n).stat().st_size==v['bytes'] and sha(raw/n)==v['sha256']
  f=fields(raw/'nes-game-last-215.txt');b=fields(raw/'nes-budget-215.txt');rx=bytes.fromhex(b['plan_reply_hex'])
  assert len(rx)==20 and rx.hex()=='00d704800001000000000000000000000000007f'
  assert crc8(rx[1:19])==rx[19] and rx[1:3]==b'\xd7\x04' and rx[3]==128
  assert int.from_bytes(rx[4:6],'big')==int(b['plan_expected_sent'])==int(f['plan_sent'])==1
  assert all(v==0 for v in rx[6:19])
  assert b['plan_valid']==b['plan_phase']=='1' and b['plan_reason']=='4'
  assert f['plan_error']==f['run_first_error']=='4' and f['native_result']=='5' and f['plan_end']=='0'
  for k in ['run_rom_error','run_stop_error','native_receiver_error','native_sink_error','sink_window_error','trace_aborts']:assert f[k]=='0',k
  assert f['loaded_bytes']==f['compared_bytes']=='393216' and f['verified']=='1'
  assert f['stop_ok']==f['base_restored']==f['safe_to_reload']=='1'
  assert f['sink_window_sent']==f['sink_window_retired']
  assert b['boot_reason']=='1' and b['boot_ticks']=='5' and b['boot_polls']=='429'
  assert b['boot_last_hex']=='0104a903' and b['failed_transfers']=='0'
  frames=int(f['native_frames']);assert frames==(60 if i==1 else 97)
  assert int(f['trace_commits'])==frames+1 and int(f['native_generation'])+1==int(b['plan_generation'])==int(f['trace_generation'])
  names=b['columns'].split(',');bins=[dict(zip(names,(int(v,16) for v in b[f'b{j:02}'].split(',')))) for j in range(12)]
  assert sum(x['frames'] for x in bins)==frames
  assert sum(x[k] for x in bins for k in ['ingress','e8','e9','e0','e1','other'])==int(f['native_wire_bytes'])
  stages=[dict(re.findall(r'(\w+)=(\S+)',s)) for s in (raw/'nes-progress-215.txt').read_text().splitlines() if s.strip()]
  assert [int(s['seq']) for s in stages]==list(range(100));by={s['stage']:s for s in stages}
  elapsed=int(by['DISPLAY_STOPPED']['elapsed_ms'])-int(by['DISPLAY_NEXT']['elapsed_ms'])
  assert elapsed<20000
  video=dict(method='ffmpeg2fps contact sheets visually inspected; approximate video timestamps, not aligned to MCU ticks',
   title_player_selection_s=3.5 if i==1 else 12.0,worldmap_dialog_first_s=7.0 if i==1 else 14.5,
   held_worldmap_until_s=12.5 if i==1 else 20.0,visible_menu_by_s=13.0 if i==1 else 20.5,
   first_level_gameplay_seen=False,audio_not_assessed=True,crt_color_not_diagnosed=True)
  runs.append(dict(run=i,raw_inputs=pins,game=f,budget=b,bins=bins,stages=stages,episodes=decode((raw/'nes-game-last-215.txt').read_text()),
   decoded=dict(phase='FLUSH',reason='FLAGS',raw=rx.hex(),crc_valid=True,fpga_fault=True,accepted=1,expected=1,descriptor_ready=False,end=False,retiring=False,
    generation=int(b['plan_generation']),pending_bytes=int(b['plan_buffer_bytes']),pending_plans=int(b['plan_buffer_count']),displayed=frames,
    display_phase_ms=elapsed,last_display_ms=int(f['profile_last_display_tick'])*10,video_error=int(f['native_video_error'])),video=video))
 sources=[BASE/'probes/nes-plan215/arm01/src'/n for n in ['nes_plan_service200.c','nes_planner211.c','nes_resident211.c']]
 sources += [BASE/'probes/nes-board207/source02'/n for n in ['nes_plan_spi200.sv','nes_direct206.sv','nes_source_tile192.sv','nes_tile205.sv']]
 result=dict(passed=True,runs=runs,user_correction='Both215 attempts fail at stage selection; discard prior assumption of intermittent60s success.',
  interpretation='Same CRC-valid FPGA fault report after first accepted batch, before next batch; not CRC/count mismatch/60s deadline. Different elapsed times and generations, same scene-associated failure class.',
  limits=['No internal FPGA first-fault module/transaction is recorded','Valid E8 CRC does not rule out earlier E9 payload/framing faults; accepted counts framing, not full tile execution','Cannot establish sound/button/MMC3 capacity or physical root cause','run2 video13 can propagate OBJ emit failure; not proof of128-slot exhaustion','Two trials show repeated failure, not universal determinism'],
  hypothesis='Investigate producer waiting for downstream drain/qualified ROM slots while global tile busy timer runs; actual selected source passes MAX_CYCLES1048576, not tile module default4096. Real core and SNES consumer delays were modeled away in215 fixture. Hypothesis only.',
  next='Target actual selected207 C/SPI/lease/READ16/bulk with realistic qualified-slot and SNES-consume stalls; capture first internal fault, compare against identical215 E8. Do not disablechecks/raiseproducttimeout or request anotherunchanged215 trial.',
  source_pins={p.relative_to(BASE).as_posix():sha(p) for p in sources},public_sha=sha(Path(__file__)),new_firmware=False,new_fit=False)
 text=json.dumps(result,ensure_ascii=False,indent=2)+'\n';(a.archive/'analysis.json').write_text(text,encoding='utf8');(ROOT/'analysis/game215-hardware01-verification.json').write_text(text,encoding='utf8')
 (a.archive/'progress.json').write_text(json.dumps(dict(status='two_repeated_fpga_faults',root_cause_known=False,next=result['next']),indent=2)+'\n')
 print(json.dumps([x['decoded'] for x in runs],ensure_ascii=False))
if __name__=='__main__':main()
