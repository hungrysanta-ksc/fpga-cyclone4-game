# SPDX-License-Identifier: MIT
"""Factor state-specific illegal commands instead of shared conflict priority."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
 old='''   IDLE,READY:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin)state<=RECEIVE;
    else if(accepted_start)state<=(state==READY)?RUN:FAILED;
    else if(accepted_load_end || accepted_load_valid)state<=FAILED;
   end'''
 new='''   IDLE,READY:begin
    if(fault || accepted_load_end ||
       (!commands_blocked && ((load_begin && (start || stop || load_valid)) || (start && (stop || load_valid)))))state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin)state<=RECEIVE;
    else if(accepted_start)state<=(state==READY)?RUN:FAILED;
    else if(accepted_load_valid)state<=FAILED;
   end'''
 assert s.count(old)==1;s=s.replace(old,new)
 old='''   RECEIVE:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_begin || accepted_start)state<=FAILED;
    else if(accepted_load_end)state<=count_complete?READY:FAILED;
    else if(accepted_load_valid)state<=count_complete?FAILED:SETUP;
   end'''
 new='''   RECEIVE:begin
    // BEGIN/START are illegal even alone; END conflicts only need STOP/VALID.
    if(fault || accepted_load_begin || accepted_start || (accepted_load_end && (stop || accepted_load_valid)))state<=FAILED;
    else if(stop)state<=IDLE;
    else if(accepted_load_end)state<=count_complete?READY:FAILED;
    else if(accepted_load_valid)state<=count_complete?FAILED:SETUP;
   end'''
 assert s.count(old)==1;s=s.replace(old,new)
 old='''   RUN:begin
    if(fault || command_conflict)state<=FAILED;
    else if(stop)state<=READY;
    else if(accepted_load_begin || accepted_start || accepted_load_end || accepted_load_valid)state<=FAILED;
   end'''
 new='''   RUN:begin
    if(fault || accepted_load_begin || accepted_start || accepted_load_end)state<=FAILED;
    else if(stop)state<=READY;
    else if(accepted_load_valid)state<=FAILED;
   end'''
 assert s.count(old)==1
 return s.replace(old,new)

def prepare(baseline,out):
 assert not out.exists() and str(out).isascii()
 m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
 for n,h in m['sources'].items():
  assert sha(baseline/n)==h,n
  p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
 old=(baseline/'nes_rom_loader.sv').read_text();new=transform(old)
 (out/'nes_rom_loader.sv').write_text(new)
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
 result=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=['nes_rom_loader.sv'],public_sources={'tools/nes_commandguard165.py':sha(Path(__file__))})
 assert [n for n,h in result['sources'].items() if h!=m['sources'][n]]==result['changed']
 (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();prepare(a.baseline,a.out)
