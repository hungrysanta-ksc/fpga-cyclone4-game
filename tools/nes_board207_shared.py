# SPDX-License-Identifier: MIT
"""Share the actual board's NES core release for epoch sampling; no extra chain.

The serial/Gray source still uses diagnostic_reset in mem_clk. The sampling
registers may reset on STOP as well as cold reset; the content ID does not.
There is no ready feedback: memory_ready is produced by NES RAM initialization,
not by source_ready. Invalid admission remains held through the local reset.
"""
from pathlib import Path
import argparse,json,shutil
from nes_board204 import ROOT,BASE,sha,replace

def prepare(out):
 out=out.resolve();out.mkdir(parents=True,exist_ok=False)
 old=BASE/'probes/nes-board207/source01';p=json.loads((old/'preparation207.json').read_bytes())
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 f=out/'nes_source_epoch207.sv';s=f.read_text()
 s=replace(s,'input wire mem_clk,nes_clk,reset,load_begin,load_valid,','input wire mem_clk,nes_clk,reset,local_reset,load_begin,load_valid,')
 s=replace(s,''' // Cold reset may be released by the memory domain while NES is stopped.
 // Only this release chain sees that deassertion. Keep admission held while
 // the96 sampling registers are still held in their local cold reset.
 wire cold_reset;
 nes_domain_reset124 cold_release(.clk(nes_clk),.raw_reset(reset),.reset(cold_reset));''',''' // local_reset is the existing board core_release output in nes_clk.
 // It asserts for cold reset/STOP/RAM initialization and deasserts locally.
 // Only the sampling pipeline resets on STOP; serial/gray content ID persists.
 wire cold_reset=local_reset;''')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_spi_boot.sv';s=replace(f.read_text(),'input wire clk,mem_clk,reset,read_reset,','input wire clk,mem_clk,reset,read_reset,source_local_reset207,')
 s=replace(s,'nes_source_epoch207 content_lifetime(.mem_clk(mem_clk),.nes_clk(clk),.reset(reset),','nes_source_epoch207 content_lifetime(.mem_clk(mem_clk),.nes_clk(clk),.reset(reset),.local_reset(source_local_reset207),')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_live_joint.sv';s=replace(f.read_text(),'nes_spi_boot loader_boot(.source_ready204','nes_spi_boot loader_boot(.source_local_reset207(reset),.source_ready204')
 # Assert the actual producer and no source-ready feedback before binding.
 assert 'core_release(.clk(clk),.raw_reset(common_reset),.reset(reset))' in s
 assert '.init_done(memory_ready)' in s and 'common_reset=raw_stop || !memory_ready' in s
 f.write_text(s,encoding='utf8',newline='\n')
 result=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['sources'],
  public_sources={'tools/nes_board207_shared.py':sha(Path(__file__))},
  changed=[n for n,h in p['sources'].items() if sha(out/n)!=h],
  old_constraints_unchanged=True,no_package=True,adopted=False,shared_board_core_release=True)
 (out/'preparation207.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
 print(json.dumps(dict(files=len(result['sources']),changed=result['changed'])))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
