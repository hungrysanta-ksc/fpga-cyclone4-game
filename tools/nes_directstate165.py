# SPDX-License-Identifier: MIT
"""Explicit one-bit-per-state loader and same-edge local reader capture enables."""
from pathlib import Path
import argparse,json,difflib,shutil,re
from nes_game147 import sha

STATES='IDLE RECEIVE WRITE HOLD READY RUN FAILED SETUP RELEASE'.split()

def loader(s):
    needle='reg [3:0] state;'
    assert s.count(needle)==1
    # Numeric state remains a verification view, not the transition feedback.
    view=' | '.join(f'({{4{{phase[{i}]}}}} & 4\'d{i})' for i in range(1,16))
    s=s.replace(needle,'reg [15:0] phase;\n wire [3:0] state='+view+';')
    a=s.index(' wire [3:0] unused_hold=');b=s.index('\n wire count_stop=',a)
    s=s[:a]+''' // Each bit is a destination register; no binary encode/decode feedback.
 wire to_idle=(from_ir && !ir_bad && (stop ||
       (state==IDLE && !accepted_load_begin && !accepted_start && !accepted_load_valid))) ||
  (state==RECEIVE && !receive_bad && stop) ||
  ((state==SETUP || state==RELEASE) && !timed_bad && stop);
 always @(posedge mem_clk or posedge reset)begin
  if(reset)phase<=16'b1;
  else if(active_reset)phase<=16'b1;
  else phase<={phase[15:9] & {7{!fault && !command_conflict}},
    to_release,to_setup,to_failed,to_run,to_ready,to_hold,to_write,to_receive,to_idle};
 end
''' +s[b:]
    s=s.replace('state>RELEASE','(|phase[15:9])')
    for name in STATES:s=s.replace('state=='+name,'phase['+name+']')
    # Convert each remaining case selector and its exact source-state labels.
    s=s.replace('case(state)',"case(1'b1)")
    s=re.sub(r'(?m)^(\s*)((?:'+ '|'.join(STATES)+r')(?:,(?:'+ '|'.join(STATES)+r'))*):',
             lambda m:m[1]+' || '.join('phase['+n+']' for n in m[2].split(','))+':',s)
    assert not re.search(r'\bstate\s*(?:==|>|<=)',s) and 'case(state)' not in s
    return s

def physical(s):
    a='reg [7:0] data_hold;'
    assert s.count(a)==1
    s=s.replace(a,a+'''
 // Predict exactly the next ACTIVE terminal edge, without moving the sample.
 // Independent enables permit local placement of the two data nibbles.
 (* preserve, dont_merge *) reg capture_low,capture_high;
 wire capture_next=(state==SETUP && READ_CYCLES==1) ||
                   (state==ACTIVE && !read_last && remaining==2);
 always @(posedge mem_clk or posedge mr)
  if(mr)begin capture_low<=0;capture_high<=0;end
  else begin capture_low<=capture_next;capture_high<=capture_next;end
 always @(posedge mem_clk or posedge mr)
  if(mr)data_hold<=0;
  else begin
   if(capture_low)data_hold[3:0]<=lane?psram_data[3:0]:psram_data[11:8];
   if(capture_high)data_hold[7:4]<=lane?psram_data[7:4]:psram_data[15:12];
  end
''')
    # Place new logic after state/read_last declarations, before pin logic.
    start=s.index(' // Predict exactly');end=s.index(' (* altera_attribute=',start)
    block=s[start:end];s=s[:start]+s[end:]
    at=s.index(' reg chip,lane;');s=s[:at]+s[at:].replace(' reg chip,lane;',' reg chip,lane;\n'+block,1)
    assert s.count('ack_toggle<=0;data_hold<=0;')==1
    s=s.replace('ack_toggle<=0;data_hold<=0;','ack_toggle<=0;')
    assert s.count('data_hold<=lane?psram_data[7:0]:psram_data[15:8];')==1
    return s.replace('data_hold<=lane?psram_data[7:0]:psram_data[15:8];','')

def prepare(baseline,out):
    assert not out.exists() and str(out).isascii()
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir()
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    changed=['nes_rom_loader.sv','nes_rom_physical.sv']
    for n,fn in zip(changed,[loader,physical]):
        old=(baseline/n).read_text();new=fn(old);(out/n).write_text(new)
        (out/(n+'.diff')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))))
    r=dict(sources={n:sha(out/n) for n in m['sources']},baseline=m['sources'],baseline_result_sha256=sha(baseline/'result.json'),changed=changed,public_sources={'tools/nes_directstate165.py':sha(Path(__file__))})
    assert set(n for n,h in r['sources'].items() if h!=m['sources'][n])==set(changed)
    (out/'preparation.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.out)
