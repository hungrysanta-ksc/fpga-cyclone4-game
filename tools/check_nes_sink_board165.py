# SPDX-License-Identifier: MIT
"""Inspect saved actual-board synthesis/fit evidence without rerunning tools."""
from pathlib import Path
import argparse,json,re
from nes_game147 import sha,ROOT

def inspect(board,verified):
 prep=json.loads((board/'preparation.json').read_bytes())
 test=json.loads((verified/'result.json').read_bytes());assert test['passed']
 for n,h in prep['sources'].items():assert sha(board/n)==h,n
 for n,h in test['prepared_sources'].items():assert sha(board/n)==h,n
 for n,h in {**prep['public_sources'],**test['public_sources']}.items():assert sha(ROOT/n)==h,n
 log=(board/'map.log').read_text(errors='replace')
 report=(board/'output_files/board.map.rpt').read_text(errors='replace')
 fit=(board/'fit.log').read_text(errors='replace')
 assert 'Analysis & Synthesis was successful' in log
 def value(label):
  m=re.search(r'^; '+re.escape(label)+r'\s*; ([\d,]+)',report,re.M);assert m,label
  return int(m[1].replace(',',''))
 resources={n:value(label) for n,label in [('estimated_le','Estimated Total logic elements'),('combinational','Total combinational functions'),('registers','Total registers'),('memory_bits','Total memory bits'),('pins','Total pins'),('virtual_pins','Total virtual pins')]}
 assert resources['pins']==122 and resources['virtual_pins']==0
 # AUTO raster RAM is inferred altsyncram, not yet a fitted M9K allocation.
 memories=[('fetch','required_tiles'),('compact','rows'),('compact','exceptions'),('compact','objects'),('compact','maps'),('raster','rows'),('raster','colors'),('native_spi','buffer')]
 inferred=[]
 for instance,n in memories:
  m=re.search(r'^; .*:'+instance+r'\|altsyncram:'+n+r'_rtl_\d.*; (M9K|AUTO)\s*; Simple Dual Port.*$',report,re.M)
  assert m,(instance,n)
  inferred.append(dict(instance=instance,array=n,requested_type=m[1]))
 assert re.search(r'program_rom_rtl_0.*M9K\s*; ROM\s*; 4096\s*; 8',report)
 rows=[]
 for line in report.splitlines():
  c=[s.strip() for s in line.split(';')]
  if len(c)>12 and re.fullmatch(r'\d+ \(\d+\)',c[2]):
   rows.append(dict(hierarchy=c[10],local_combinational=int(c[2].split('(')[1][:-1]),local_registers=int(c[3].split('(')[1][:-1]),hierarchy_memory_bits=int(c[4])))
 rows.sort(key=lambda r:r['local_combinational'],reverse=True)
 errors=re.findall(r'^Error \(\d+\):.*',fit,re.M)
 fit_pass='Fitter was successful' in fit and not errors
 assert fit_pass or (any('Error (170011)' in x for x in errors) and 'Error (171000)' in fit),errors
 assert not (board/'result.json').exists(),'Preserve completed evidence; use a fresh board directory'
 result=dict(synthesis_pass=True,fit_pass=fit_pass,hardware_ready=False,resources=resources,device_le_limit=15408,
  fit_errors=errors,largest_local_entities=rows[:12],changed_ram_inference=inferred,physical_pins_unchanged=prep['physical_pins_unchanged'],save_sram_reserved=prep['save_sram_reserved'],
  client_identity='E6/2',observer_identity='E5',sink_identity='F6',
  public_sources={**test['public_sources'],'tools/check_nes_sink_board165.py':sha(Path(__file__))},
  logs={n:sha(board/n) for n in ['map.log','fit.log','output_files/board.map.rpt','output_files/board.fit.rpt']},
  scope='Actual CPU/PPU/MMC3/APU/loader/native producer/sink physical top; synthesis estimates are not fitted utilization. Test core lifecycle is separately stubbed. No bitstream/STA/MCU loop/physical gameplay.')
 (board/'result.json').write_text(json.dumps(result,indent=2)+'\n');return result

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--verified',type=Path,required=True)
 a=p.parse_args();r=inspect(a.board,a.verified);print(json.dumps({k:r[k] for k in ['synthesis_pass','fit_pass','resources','fit_errors']}))
