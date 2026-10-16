# SPDX-License-Identifier: MIT
"""Read-only architecture budget audit. Bounds/scenarios are NOT hardware FPS."""
from pathlib import Path
import argparse, hashlib, json, math
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 a.out.mkdir(parents=True,exist_ok=False)
 arm=BASE/'probes/nes-binding209/arm01/src'
 rtl=BASE/'probes/nes-board207/source02'
 anchors={
  arm/'nes_native_runtime165.c':['nes_native_video191_plan','nes_sink165_seal','nes_plan200_retire','nes_native165_consumed'],
  arm/'nes_plan191.c':['memset(p,0,offsetof','p->bg_count=1','p->bg_keys[p->bg_count]=key','Borrow448'],
  arm/'nes_native_video165.h':['uint64_t bg_keys[1024]','uint8_t map[4096]'],
  arm/'nes_native165.c':['0x2031','s->counts[0]=(uint16_t)(g*33)','const unsigned widths[8]={2,1,7,4,7,1,2,8}'],
  arm/'nes_plan_wire199.h':['NOT a cross-frame cache','return 7'],
  arm/'nes_sink_bulk195.inc':['packet_wire deliberately keeps op7 off the async enqueue path'],
  arm/'nes_native_sink165.c':['if(!map185(s,p))return false','for(unsigned k=3;k<6;k++)','0x1941'],
  rtl/'rtl/nes.v':['native_fill_slot=div_cpu==3 && scanline_ppu>=242 && scanline_ppu<260'],
  rtl/'nes_chr_cache192.sv':['reg [7:0] bytes[0:15]'],
  ROOT/'tools/nes_native_local165.py':["label('word_loop')","label('fast_words')","c.emit(0xc9,32,0)","0x69,96,0"],
  ROOT/'tools/nes_banked169.py':["imm(4096)","call('wait169')"],
  ROOT/'tools/nes_rawsteady181.py':['all sections and raw CHR are compared below'],
  ROOT/'tools/nes_bulk195.py':['import nes_rawsteady181 as steady','import nes_client181 as client'],
 }
 pins={}
 for path,words in anchors.items():
  s=path.read_text(encoding='utf8')
  for word in words:assert word in s,(str(path),word)
  pins[path.relative_to(BASE).as_posix()]=dict(sha256=sha(path),anchors=words)
 h=ROOT/'analysis/game209-hardware01-verification.json'
 measured=json.loads(h.read_bytes())['comparison']['current209']
 fps=60;spi=2625000;master=21477272.727272727
 frame_ms=1000/fps;spi_B=spi/8/fps
 budget=dict(target_fps_approx=fps,target_frame_ms=frame_ms,spi_hz=spi,
  spi_clocked_bytes_per_frame_ideal=spi_B,
  snes_ntsc224_vblank_payload_upper_B=math.floor(37*(1364-40)/8),
  current_snes_charged_dma_budget=5000,current_snes_command_capacity=32,
  current_snes_setup_charge_B_per_command=96,
  qualified_cold_source_reads_per_frame_optimistic=(260-242)*341*4//12,
  full8bpp_bytes=256*224,full8bpp_dma_ms_without_refresh=256*224*8/master*1000,
  full512BG_plan_plus_END_B=512*7+3,
  full512BG_plan_plus_END_spi_ms=(512*7+3)*8/spi*1000,
  full4096map_spi_ms=4096*8/spi*1000,
  full512BG_plan_and_fullmap_spi_ms=(512*7+3+4096)*8/spi*1000,
  full512BG_source_B=512*16,full512BG_source_min_windows=math.ceil(8192/2046),
  full512BG_map_palette_OAM_upload_B=8192+4096+512+544,
  full512BG_map_palette_OAM_min_vblanks=math.ceil((8192+4096+512+544)/6123),
  nonrepeat29group_map_ingress_B=29*33*6,
  nonrepeat29group_map_ingress_spi_ms=29*33*6*8/spi*1000,
  current_average_completion_ms=measured['amortized_display_ms'],
  current_average_rate_to_target_factor=fps/measured['display_completed_per_s'],
  counterfactual_remove_entire_receive_ms=(measured['duration_ms']-measured['receive_ms'])/measured['display_completed'],
  counterfactual_remove_entire_receive_rate=measured['display_completed']*1000/(measured['duration_ms']-measured['receive_ms']),
  ARM_remaining_B=9260,ARM_minimum_margin_B=1024,naive1024_BG_keys_B=1024*8,
  naive_BG_keys_margin_B=9260-8192,naive_BG_keys_room_above_gate_B=9260-8192-1024,
  fitted_free_LE=148,fitted_free_LAB=1,fitted_free_M9K=9,SNES_client_body_free_B=1)
 assert budget['full512BG_plan_and_fullmap_spi_ms']>frame_ms
 assert budget['full8bpp_dma_ms_without_refresh']>frame_ms
 assert budget['naive_BG_keys_room_above_gate_B']==44
 result=dict(kind='architecture_retrospective_not_firmware',hardware_input_sha256=sha(h),source_pins=pins,budget=budget,
  limits=['SPI is clocked bytes, not TX+RX counted twice; all commands share this budget.',
   'Full-map/512-tile/nonrepeat cases are conditional examples, NOT measured209 scroll distributions.',
   '6123B is theoreticalNTSC224 cap excluding software/setup; do not raise5000 without timing proof.',
   '2046 source reads is optimistic existing qualified-slot bound; real core priority lowers it.',
   'Subtracting receive is an Amdahl thought experiment with other work fixed, not a forecast.',
   'Complete-frame latency may exceed16.67ms in a pipeline; each shared resource and buffer turnover must sustain60/s.',
   'No source changes/build/FIT/newhardware/wholegame FPS claims.'],
  decision='SMB3/MMC3 near60fps remains a conditional target worth a bounded feasibility gate. Current209 all-frame rebuild/serialized transport is not an approved60fps architecture. General MMC4/MMC5/CHR-RAM worstcase60fps unproven.',
  next='One actual sustained first-level scroll window: phase costs, command bytes, source misses, dirty/output slots, SNES diff/fallback/VBlank counts. Replay current vs persistent physical-pattern slots+scroll-aware map+end-to-end dirty lists. Require all resource budgets including residual ingress/SPI/PSRAM/SNESCPU to fit before another fullFIT or broad implementation.')
 text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
 (a.out/'analysis.json').write_text(text,encoding='utf8',newline='\n')
 (ROOT/'analysis/nes-60fps-retrospective209.json').write_text(text,encoding='utf8',newline='\n')
 print(json.dumps(budget,indent=2))
if __name__=='__main__':main()
