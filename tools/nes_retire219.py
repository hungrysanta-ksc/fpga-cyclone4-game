# SPDX-License-Identifier: MIT
"""Local command response qualifications and enabled counter data selection."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha,replace

def spi(s):
 old=' {check_request,stop,start,load_end,load_valid,load_begin}<=approved_pulse & {6{command_retire_ok}};'
 assert s.count(old)==1
 anchor=' wire command_retire_ok='
 a=s.index(anchor);b=s.index('\n',s.index('check_response_address!=check_request_tag));',a))
 s=s[:a]+''' // 219: command-local half comparisons retain same-edge response checks.
 // Preserve the qualified pulse nets so synthesis need not route the shared
 // error_response node across every command output. No response pipeline.
 wire retire_base_ok=!fault && ss_sync[1] && !check_fault &&
  !(check_enable && boot_fault) && !(check_response && (!check_enable || !check_busy));
 (* keep *) wire [5:0] retire_low=approved_pulse &
  {6{!check_response || check_response_address[8:0]==check_request_tag[8:0]}};
 (* keep *) wire [5:0] retire_high=approved_pulse &
  {6{!check_response || check_response_address[18:9]==check_request_tag[18:9]}};'''+s[b:]
 return replace(s,old,' {check_request,stop,start,load_end,load_valid,load_begin}<=retire_low & retire_high & {6{retire_base_ok}};')

def loader(s):
 # Under count_update, a one-hot RELEASE with STOP clear can only be a
 # count_advance; all other updates clear. Preserve the enable equation.
 s=replace(s,' wire count_clear=active_reset || count_stop || count_begin;', ''' wire count_clear=active_reset || count_stop || count_begin;
 // 219: use the enabled-data truth table, not the shared clear decode.
 // count_update still owns admission. One-hot phase is maintained by the
 // existing phase register, including unused encoded states and reset.
 wire count_increment_data=!active_reset && phase[RELEASE] && !stop;''')
 assert s.count('if(count_clear)')==2
 return s.replace('if(count_clear)','if(!count_increment_data)')

def prepare(out):
 old=BASE/'probes/nes-boundary218/source02';p=json.loads((old/'preparation218.json').read_bytes());out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n
  (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 for n,fn in [('nes_rom_spi.sv',spi),('nes_rom_loader.sv',loader)]:
  before=(old/n).read_text();after=fn(before);(out/n).write_text(after,encoding='utf8',newline='\n')
  (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['sources'],changed=['nes_rom_loader.sv','nes_rom_spi.sv'],
  public_sources=p['public_sources']|{str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},no_package=True,adopted=False)
 assert sorted(n for n,h in r['sources'].items() if h!=r['baseline'][n])==r['changed']
 (out/'preparation219.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
