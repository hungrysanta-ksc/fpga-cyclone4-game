# SPDX-License-Identifier: MIT
"""Distribute response absence into bitwise address guards; no new state or latency."""
from pathlib import Path
import argparse,json,shutil,difflib
from nes_game147 import ROOT,sha

def transform(s):
    needle=' // Dynamic faults/response ownership still win on the retirement edge.'
    assert s.count(needle)==1
    logic=' // Each 3-input guard fits one LUT; keep it separate from the shared fault comparator.\n (* keep = "true" *) wire [18:0] counter_response_bit_ok;\n'
    for i in range(19):
        logic+=f' assign counter_response_bit_ok[{i}]=!check_response || (check_response_address[{i}]==check_next[{i}]);\n'
    s=s.replace(needle,logic+needle)
    needle='!(check_response && (!check_enable || !check_busy || check_response_address!=check_next));'
    assert s.count(needle)==1
    return s.replace(needle,'(!check_response || (check_enable && check_busy)) && (&counter_response_bit_ok);')

def drain(s):
    needle='  end else begin\n   //128 State-local command decoding:'
    assert s.count(needle)==1
    return s.replace(needle,'''  end else if(state==WRITE || state==HOLD)begin
   // In-flight writes keep their pulse even when a command is rejected.
   // Decode the advance guard once, without threading state through error priority.
   if(!stop && (commands_blocked || !(load_begin || load_end || start)))advance_phase();
   if(command_conflict)begin fault<=1;error_code<=5;end
   else if(stop)begin fault<=1;error_code<=6;end
   else if(accepted_load_begin)begin fault<=1;error_code<=1;end
   else if(accepted_start)begin fault<=1;error_code<=3;end
   else if(accepted_load_end)begin fault<=1;error_code<=2;end
  end else begin
   //128 State-local command decoding:''').replace('    SETUP,WRITE,HOLD,RELEASE:begin','    SETUP,RELEASE:begin')

def causes(s):
    needle=' reg [4:0] pending_causes;'
    assert s.count(needle)==1
    s=s.replace(needle,needle+'\n reg pending_check_begin_error,pending_check_read_error;')
    needle="pending_causes[2]?4'd6:"
    assert s.count(needle)==1
    s=s.replace(needle,"(pending_causes[2] || pending_check_begin_error || pending_check_read_error)?4'd6:")
    needle='pending_causes<=0;';assert s.count(needle)==1
    s=s.replace(needle,needle+'pending_check_begin_error<=0;pending_check_read_error<=0;')
    needle='pending_causes<=body_causes;';assert s.count(needle)==1
    s=s.replace(needle,'''pending_causes<={body_causes[4:3],((cmd60 || cmd61 || cmd62 || cmd63) && check_enable),body_causes[1:0]};
     pending_check_begin_error<=cmd66 && (!loaded || run_enable || check_enable || offset!=0);
     pending_check_read_error<=cmd67 && (!check_enable || check_busy || check_done || !check_ready || !offset_matches_next || !next_below_length);''')
    return s

def fault(s):
    assert s.count('fault<=0;')==2 and s.count('fault<=1;')==6
    s=s.replace('fault<=0;','').replace('fault<=1;','')
    at=s.index(' task automatic fail')
    logic=''' // Sticky fault uses parallel state legality; error-code priority stays unchanged.
 wire phase_state=(state==SETUP || state==WRITE || state==HOLD || state==RELEASE);
 wire fault_begin=accepted_load_begin && (state==RECEIVE || state==RUN || phase_state);
 wire fault_start=accepted_start && (state==IDLE || state==RECEIVE || state==RUN || phase_state);
 wire fault_end=accepted_load_end && (state==IDLE || state==READY || state==RUN || phase_state || (state==RECEIVE && !count_complete));
 wire fault_valid=accepted_load_valid && !stop && !accepted_load_begin && !accepted_start && !accepted_load_end &&
  (state==IDLE || state==READY || state==RUN || (state==RECEIVE && count_complete));
 wire fault_stop=stop && (state==WRITE || state==HOLD);
 always @(posedge mem_clk or posedge reset)
  if(reset)fault<=0;
  else if(active_reset)fault<=0;
  else if(command_conflict || fault_begin || fault_start || fault_end || fault_valid || fault_stop)fault<=1;
'''
    return s[:at]+logic+s[at:]

def prepare(baseline,out,variant='fault'):
    assert not out.exists() and str(out).isascii()
    v=json.loads((ROOT/'analysis/predecode165-verification.json').read_bytes())
    assert sha(baseline/'result.json')==v['raw_result_sha256']['map03']
    m=json.loads((baseline/'preparation.json').read_bytes());out.mkdir(parents=True)
    for n,h in m['sources'].items():
        assert sha(baseline/n)==h,n
        p=out/n;p.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(baseline/n,p)
    p=out/'nes_rom_spi.sv';old=p.read_text();new=transform(old)
    if variant in ['causes','fault']:new=causes(new)
    p.write_text(new,encoding='utf8')
    (out/'spi.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
    changed=['nes_rom_spi.sv']
    if variant in ['drain','causes','fault']:
        p=out/'nes_rom_loader.sv';old=p.read_text();new=drain(old)
        if variant=='fault':new=fault(new)
        p.write_text(new,encoding='utf8')
        (out/'loader.diff').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True))),encoding='utf8')
        changed.append('nes_rom_loader.sv')
    else:assert variant=='compare'
    result=dict(variant=variant,baseline=m['sources'],sources={n:sha(out/n) for n in m['sources']},changed=sorted(changed),public_sources={'tools/nes_compare165.py':sha(Path(__file__))})
    assert sorted(n for n,h in result['sources'].items() if h!=result['baseline'][n])==result['changed']
    (out/'preparation.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--variant',choices=['compare','drain','causes','fault'],default='fault')
    a=p.parse_args();prepare(a.baseline,a.out,a.variant)
