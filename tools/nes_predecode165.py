# SPDX-License-Identifier: MIT
"""Predecode counter command intent on the existing SPI frame-capture edge."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 start=s.index('        // Bitwise carry prefixes');end=s.index('\n       end',start)
 increment=s[start:end];s=s[:start]+s[end:]
 assert s.count('check_next<=0;')==4;s=s.replace('check_next<=0;','')
 at=s.index(' task automatic fail')
 logic=''' // Static command validity is captured with pending, never one edge earlier.
 reg pending_counter_clear,pending_counter_inc;
 wire counter_header_ok=byte_count==8 && bit_count==0 && crc==received_crc &&
  tail==8'ha5 && arg_not==~arg && command<=8'h6a &&
  (command==8'h61 || command==8'h68 || ((command==8'h60)?arg==2:arg==0));
 // Dynamic faults/response ownership still win on the retirement edge.
 wire counter_retire_ok=!fault && pending && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) &&
  !(check_response && (!check_enable || !check_busy || check_response_address!=check_next));
 always @(posedge mem_clk or posedge reset)
  if(reset)check_next<=0;
  else if(counter_retire_ok)begin
   if(pending_counter_clear)check_next<=0;
   else if(pending_counter_inc)begin
'''+increment+'''
   end
  end
'''
 s=s[:at]+logic+s[at:]
 old='pending<=0;pending_command<=0;';assert s.count(old)==1
 s=s.replace(old,'pending_counter_clear<=0;pending_counter_inc<=0;'+old)
 old='pending_causes<=body_causes;';assert s.count(old)==1
 s=s.replace(old,old+'''
     pending_counter_clear<=counter_header_ok && body_causes==0 && (cmd60 || cmd64 || cmd66);
     pending_counter_inc<=counter_header_ok && body_causes==0 && cmd68;''')
 return s

def loader(s):
 assert s.count('loaded_bytes==total')==2
 s=s.replace('loaded_bytes==total','count_complete')
 needle=" wire [18:0] total=19'h60000;"
 assert s.count(needle)==1;s=s.replace(needle,needle+'\n reg count_complete;')
 for needle in ['if(reset)loaded_bytes<=0;','else if(active_reset)loaded_bytes<=0;','if(count_stop || count_begin)loaded_bytes<=0;']:
  assert s.count(needle)==1
  s=s.replace(needle,needle.replace('loaded_bytes<=0;','begin loaded_bytes<=0;count_complete<=0;end'))
 needle="else if(count_advance)loaded_bytes<=loaded_bytes+1'b1;"
 assert s.count(needle)==1
 return s.replace(needle,"else if(count_advance)begin loaded_bytes<=loaded_bytes+1'b1;count_complete<=loaded_bytes==total-1'b1;end")

def specialize(s):
 old="tail==8'ha5 && arg_not==~arg && command<=8'h6a &&\n  (command==8'h61 || command==8'h68 || ((command==8'h60)?arg==2:arg==0));"
 assert s.count(old)==1;s=s.replace(old,"tail==8'ha5 && arg_not==~arg;")
 old='pending_counter_clear<=counter_header_ok && body_causes==0 && (cmd60 || cmd64 || cmd66);'
 assert s.count(old)==1;s=s.replace(old,'''pending_counter_clear<=counter_header_ok &&
      ((cmd60 && arg==2 && offset==0 && !check_enable) ||
       (cmd64 && arg==0 && offset=={5'd0,loaded_bytes}) ||
       (cmd66 && arg==0 && offset==0 && loaded && !run_enable && !check_enable));''')
 old='pending_counter_inc<=counter_header_ok && body_causes==0 && cmd68;'
 assert s.count(old)==1
 return s.replace(old,'''pending_counter_inc<=counter_header_ok && cmd68 && check_enable &&
      !check_busy && check_done && offset_matches_next && arg==checked_data;''')

def masked(s):
 start=s.index(' always @(posedge mem_clk or posedge reset)\n  if(reset)check_next<=0;')
 end=s.index(' task automatic fail',start)
 logic=''' wire counter_clear=counter_retire_ok && pending_counter_clear;
 wire counter_inc=counter_retire_ok && pending_counter_inc;
 always @(posedge mem_clk or posedge reset)
  if(reset)check_next<=0;
  else begin
'''
 for i in range(19):
  carry="1'b1" if i==0 else f'(&check_next[{i-1}:0])' if i<8 else 'next_carry8' if i==8 else f'(next_carry8 && (&check_next[{i-1}:8]))'
  logic+=f'   check_next[{i}] <= (check_next[{i}] ^ (counter_inc && {carry})) && !counter_clear;\n'
 return s[:start]+logic+'  end\n'+s[end:]

def prepare(baseline,out,variant='specialized'):
 assert not out.exists() and str(out).isascii()
 v=json.loads((ROOT/'analysis/retire165-verification.json').read_bytes())
 assert sha(baseline/'result.json')==v['raw_result_sha256']['map02']
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 p=out/'nes_rom_spi.sv';old=p.read_text();new=transform(old)
 if variant in ['specialized','masked']:new=specialize(new)
 if variant=='masked':new=masked(new)
 p.write_text(new,encoding='utf8')
 (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
 changed=['nes_rom_spi.sv']
 if variant in ['length','specialized','masked']:
  p=out/'nes_rom_loader.sv';old=p.read_text();new=loader(old);p.write_text(new,encoding='utf8')
  (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
  changed.append('nes_rom_loader.sv')
 else:assert variant=='predecode'
 result=dict(variant=variant,baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=sorted(changed),public_sources={'tools/nes_predecode165.py':sha(Path(__file__))})
 assert sorted(n for n,h in result['sources'].items() if h!=result['baseline'][n])==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--variant',choices=['predecode','length','specialized','masked'],default='specialized')
 a=p.parse_args();prepare(a.baseline,a.out,a.variant)
