# SPDX-License-Identifier: MIT
"""Audit mapper portability gates and the measured375 ROM-window critical path."""
import argparse,csv,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from nes_bg295 import unbatch

def main():
 p=argparse.ArgumentParser();p.add_argument('--guards',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 d=BASE/'probes/nes-context375/joint01';board=BASE/'probes/nes-context375/map03';pins={}
 def read(f):pins[str(f)]=sha(f);return f.read_text(encoding='utf-8')
 prev=json.loads(read(ROOT/'analysis/context375-verification.json'));ev=list(csv.reader(read(d/'joint-events.csv').splitlines()));g=json.loads(read(a.guards/'result.json'))
 assert g['passed'] and len(g['cases'])==6
 for n,h in g['actual_inputs'].items():
  if n!='test.sv':assert sha(board/n)==h
  read(a.guards/n)
 for c in g['cases']:
  raw=read(a.guards/f"case{c['case']}.log");assert c['raw_log']==sha(a.guards/f"case{c['case']}.log") and 'Errors: 0, Warnings: 0' in raw
 assert 'valid=0 errors=04' in read(a.guards/'case3.log')
 markers={
  'cart_nrom.sv':['MMC3 mapper(','.flags(32\'d4)'],
  'nes_native_planes165.sv':["physical_address[21:17]==5'h10",'physical_address[16:4]'],
  'nes_native_compact181.sv':['wire [14:0] cell_value={attribute[1:0],tile}','exception_count==128','selected_group>=32'],
  'nes_plan_batch206.sv':['output reg [12:0] plan_tag','if(data[7:5]!=0)bad<=1'],
  'nes_rom_service.sv':["cpumem_addr<25'h40000","ppumem_addr<22'h220000",'cpu_valid&&cpu_address_valid'],
  'nes_rom_loader.sv':["wire [18:0] total=19'h60000"],
  'rtl/nes.v':['scanline_ppu>=242 && scanline_ppu<260','cpu_rnw && cpu_addr[15]']}
 for n,terms in markers.items():
  raw=read(board/n)
  for x in terms:assert x in raw,(n,x)
 bench=read(d/'joint266_tb.sv');assert '.core_safe(1\'b1)' in bench and 'romcycle267%357368>=330088' in bench and 'romcycle267%357368<354640' in bench
 times=[]
 for row in prev['candidate']['rows'][2:]:
  f=row['frame'];origin=row['start_ps'];k=row['start_ROM_cycle'];period=357368;window=330088;close=354640
  first=lambda name,kind=None:next((x for x in ev if x[:2]==[name,str(f)] and (kind is None or x[2]==str(kind))),None)
  req=first('firstreq305',0);miss=first('firstmiss305',0);tile=first('romtile305',0);records=unbatch((d/f'actual-plans293-{f}.bin').read_bytes());pins[str(d/f'actual-plans293-{f}.bin')]=sha(d/f'actual-plans293-{f}.bin')
  record=next((x for x in records if x[0]&3==0),None);tag=int.from_bytes(record[5:7] if record[0]&128 else record[6:8],'little') if record else None
  tags=row['hints'][0]['tags'] if row['hints'] else []
  cycle_base=k//period*period
  if cycle_base+close<=k:cycle_base+=period
  times.append(dict(frame=f,processing_ms=row['processing_ms'],source_ROM_phase=k%period,first_window_open_approx_ms=(cycle_base+window-k)*45454/1e9,
   first_window_close_approx_ms=(cycle_base+close-k)*45454/1e9,first_BG_plan_request_ms=(int(req[-1])-origin)/1e9 if req else None,
   first_BG_back_request_ms=(int(miss[-1])-origin)/1e9 if miss else None,first_BG_tile_ms=(int(tile[-1])-origin)/1e9 if tile else None,
   first_BG_tag=tag,first_hint_tags=tags,first_BG_in_hint=tag in tags if tag is not None else None,
   first_back_request_to_tile_ms=(int(tile[-1])-int(miss[-1]))/1e9 if tile and miss else None))
 row=next(x for x in times if x['frame']==914);assert row['first_BG_tag']==6136 and not row['first_BG_in_hint'] and abs(row['first_back_request_to_tile_ms']-8.322855)<1e-8
 budget=1e3/60;max_gap=max(x['interval_ms'] for x in prev['completion_intervals'] if x['frame']>907)
 result=dict(stage=376,passed=True,kind='Portability/critical-path audit plus unchanged375 RTL boundary tests;no mapper implemented',
  baseline=375,guards=g,critical_path=times,frame914=dict(processing_ms=21.501082,gap_to60Hz_ms=21.501082-budget,measured_first_ROM_wait_ms=row['first_back_request_to_tile_ms']),
  maximum_warm_completion_interval_ms=max_gap,maximum_interval_minus60Hz_ms=max_gap-budget,
  mapper4_MMC3_only_board=True,MMC4=dict(mapper_number=10,ROM_capacity_profile_compatible=True,resolved_fetch_replay_passed=True,live_latch_timing_implemented=False,admission=False),
  MMC5=dict(mapper_number=5,full_CHR_capacity_bytes=1048576,required_physical_tile_tag_bits=16,current_tag_bits=13,full_profile_supported=False,
   per8pixel_palette_replay=True,nonaligned_split_stress=dict(rows=224,affected_cells_per_row=17,exceptions_required=224*17,current_capacity=128,rejected=True),
   mapper_ExRAM_IRQ_audio_implemented=False,whole_incremental_area=None,full_schedule_extra_ms=None,admission=False),
  profile=dict(current_CHR_bytes=131072,current_PRG_bytes=262144,loader_total_bytes=393216,cell_tile_bits=13,palette_bits=2,full_MMC5_minimum_cell_bits=18,
   current_1056_cell_bits=1056*15,full_MMC5_minimum_1056_cell_bits=1056*18,physical_M9K_delta=None,
   current_target_membership_bytes=1024,full65536_tag_bitmap_bytes=8192,bitmap_extra_bytes=7168),
  alternatives=dict(legacy_semantic='Keep compact fast profile and shared ownership/independent checks;MMC4 needs actual latch/loader/core/ROM tests.',
   extended_semantic='Version profile with wider physical tags and per-fetch mapper data;represent split segments instead of exhausting per-cell exceptions. Measure planner/ROM/SPI/DMA/control/ExRAM/audio together.',
   ARM_full_4bpp_retransmission=dict(bytes=28672,SPI_hz=2625000,wire_only_ms=28672*8/2625000*1000,selected=False,scope='Conditional full256x224x4bpp ARM-to-FPGA retransmission;not a lower bound for direct FPGA rendering or delta tiles.')),
  joint_gates=dict(time_equation='Tbase + measured mapper/core/render delta + actual IRQ/SPI/DMA/VBlank/WCET margin <= presentation deadline;also no capture loss/backlog.',
   area_equation='additional net deletion >=2255 + same-boundary incremental mapper/render/IO comb + chosen placement/timing reserve;155 alone is not an MMC5 allowance.',
   current_comb_deficit=2255,current_required_with155reserve=2410,mapper_incremental_comb=None,
   board_ROM_eligibility='Actual native_fill_slot AND native_core_safe;375 stress bench fixes core_safe=1 and uses synthetic core demand,not a mapper worst-case bound.'),
  reusable=['Input/display ownership and epoch/serial/credit lifetimes','Independent expected/read CRC/coverage,STOP/finalACK','Actual M4/SPI/IRQ accounting and matched simulation/wholeMAP hashes','Physical ROM cache only when full address/content epoch is preserved'],
  time_credit_ms=0,new_RTL=False,new_MAP=False,FIT=False,STA=False,physical=False,sustained60fps=False,
  sources=[dict(url='https://www.nesdev.org/wiki/MMC4',purpose='PPU-read-driven latch bank changes;mapper10'),dict(url='https://www.nesdev.org/wiki/MMC5',purpose='Larger CHR namespace,ExRAM/extended attributes/split/IRQ/audio'),dict(url='https://github.com/mist-devel/nes/blob/master/src/mappers/MMC5.sv',purpose='Primary implementation comparison;not imported or treated as passing local support')],pins=pins)
 for f in ROOT.joinpath('tools').glob('*376*'):pins[str(f)]=sha(f)
 a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n');print(json.dumps(dict(passed=True,first914=row,tests=len(g['cases']),full_MMC5_supported=False,wire_only_full4bpp_ms=result['alternatives']['ARM_full_4bpp_retransmission']['wire_only_ms']),indent=2))
if __name__=='__main__':main()
