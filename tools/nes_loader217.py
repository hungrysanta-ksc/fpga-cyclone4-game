# SPDX-License-Identifier: MIT
"""Parallel loader error-bit updates; same-edge priority, no extra state/latency."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_board204 import ROOT,BASE,sha

def transform(s):
 assert s.count('error_code<=code;')==1 and s.count('error_code<=0;')==2
 s=s.replace('error_code<=code;','').replace('error_code<=0;','')
 s=s.replace('output reg [3:0] error_code,','(* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) output reg [3:0] error_code,')
 marker=' // Each destination is selected independently;'
 assert s.count(marker)==1
 logic=''' // 217: mutually exclusive error classes, with independent bit hold paths.
 // Conflict wins even in unused states. STOP+VALID is not a conflict;
 // STOP wins there, and blocked commands cannot suppress a WRITE/HOLD drain.
 // No shared error-event CE followed by a second priority encoder.
 wire err5=command_conflict;
 wire err1=!commands_blocked && load_begin && !load_end && !start && !stop && !load_valid &&
           (phase[RECEIVE] || phase[RUN] || timed_phase);
 wire err3=!commands_blocked && start && !load_begin && !load_end && !stop && !load_valid &&
           (phase[IDLE] || phase[RECEIVE] || phase[RUN] || timed_phase);
 wire err2=!commands_blocked && load_end && !load_begin && !start && !stop && !load_valid &&
           (phase[IDLE] || phase[READY] || phase[RUN] || timed_phase || (phase[RECEIVE] && !count_complete));
 wire err4=!commands_blocked && load_valid && !load_begin && !load_end && !start && !stop &&
           (phase[IDLE] || phase[READY] || phase[RUN] || (phase[RECEIVE] && count_complete));
 wire err6=stop && (commands_blocked || !(load_begin || load_end || start)) && (phase[WRITE] || phase[HOLD]);
 always @(posedge mem_clk or posedge reset)begin
  if(reset)error_code<=0;
  else if(active_reset)error_code<=0;
  else if(!fault)begin
   error_code[0]<=(err1 || err3 || err5) || (error_code[0] && !(err2 || err4 || err6));
   error_code[1]<=(err2 || err3 || err6) || (error_code[1] && !(err1 || err4 || err5));
   error_code[2]<=(err4 || err5 || err6) || (error_code[2] && !(err1 || err2 || err3));
   error_code[3]<=error_code[3] && !(err1 || err2 || err3 || err4 || err5 || err6);
  end
 end

'''
 return s.replace(marker,logic+marker)

def prepare(out):
 old=BASE/'probes/nes-wait216/source02';p=json.loads((old/'preparation216.json').read_bytes())
 out.mkdir(parents=True,exist_ok=False)
 for n,h in p['sources'].items():
  assert sha(old/n)==h,n;(out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(old/n,out/n)
 before=(old/'nes_rom_loader.sv').read_text();after=transform(before)
 (out/'nes_rom_loader.sv').write_text(after,encoding='utf8',newline='\n')
 (out/'loader.diff').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True))),encoding='utf8')
 r=dict(sources={n:sha(out/n) for n in p['sources']},baseline=p['sources'],changed=['nes_rom_loader.sv'],
  public_sources={str(Path(__file__).relative_to(ROOT)):sha(Path(__file__))},no_package=True,adopted=False)
 assert [n for n in p['sources'] if r['sources'][n]!=p['sources'][n]]==r['changed']
 (out/'preparation217.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(dict(changed=r['changed'],files=len(r['sources']))))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);prepare(p.parse_args().out)
