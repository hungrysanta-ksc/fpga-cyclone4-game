# SPDX-License-Identifier: MIT
"""Pinned130 state-only mapping plus idle preload of the phase counter."""
import json,shutil
from nes_loader127 import ROOT,sha,put,replace

def materialize(o,baseline,full=False):
 e=baseline/'nes-enable130/evidence';m=json.loads((ROOT/'analysis/enable130-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prefix='fit01/'
 names=[n[len(prefix):] for n in pins if n.startswith(prefix) and n.endswith(('.sv','.v','.vhd','.qsf','.sdc','.qpf'))]
 if not full:names=[n for n in names if '/' not in n and n.endswith('.sv')]
 inputs={}
 for n in names:
  src=e/prefix/n;assert sha(src)==pins[prefix+n];dst=o/n;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);inputs[n]=sha(src)
 p=o/'nes_rom_loader.sv';s=p.read_text()
 # Preload while no timed phase is active. Acceptance/address checks no
 # longer drive the timer enable. During every active phase the old command
 # pause and sticky-fault WRITE/HOLD drain behavior remain exact.
 s=replace(s,' task automatic advance_phase;begin',""" wire timed_phase=(state==SETUP || state==WRITE || state==HOLD || state==RELEASE);
 wire phase_step=fault ? (state==WRITE || state==HOLD) :
     (timed_phase && !(load_begin || load_end || start || stop));
 always @(posedge mem_clk or posedge reset)begin
  if(reset)remaining<=0;
  else if(active_reset)remaining<=0;
  else if(!timed_phase)remaining<=CW'(SETUP_CYCLES);
  else if(phase_step)begin
   if(remaining!=1)remaining<=remaining-1'b1;
   else case(state)
    SETUP:remaining<=CW'(WRITE_CYCLES);
    WRITE:remaining<=CW'(HOLD_CYCLES);
    HOLD:remaining<=CW'(RELEASE_CYCLES);
    default:;
   endcase
  end
 end
 task automatic advance_phase;begin""")
 # Remove only the original task/main assignments; retain the separate
 # timer block just inserted above.
 split=s.index(' task automatic advance_phase;begin')
 head,tail=s[:split],s[split:]
 tail=replace(tail,"  if(remaining!=1)remaining<=remaining-1'b1;","  if(remaining!=1)begin end")
 for assignment in ["remaining<=CW'(WRITE_CYCLES);","remaining<=CW'(HOLD_CYCLES);","remaining<=CW'(RELEASE_CYCLES);","remaining<=CW'(SETUP_CYCLES);"]:
  tail=replace(tail,assignment,'')
 assert tail.count('remaining<=0;')==2
 tail=tail.replace('remaining<=0;','')
 s=head+tail
 # fit02 exposed the state.RECEIVE synchronous-load input, not its enable.
 # Disable that additional shared control only on the state register.
 s=replace(s,'AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) reg [3:0] state;',
     'AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [3:0] state;')
 # fit03's remaining worst path ended at load_address[2].ena. Apply the
 # same data-input mapping to this output register; do not change acceptance.
 s=replace(s,' output reg [21:0] load_address,',
     ' (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) output reg [21:0] load_address,')
 put(p,s)
 # The first actual fit closed the timer path but exposed the SPI CHECK index
 # enable path. Keep behavior, locally map that index through its data input.
 p=o/'nes_rom_spi.sv';s=p.read_text()
 s=replace(s,' reg [16:0] check_next;',' (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF" *) reg [16:0] check_next;')
 # fit04 exposed the response-data enable after its address validation.
 s=replace(s,' reg [7:0] checked_data;',
     ' (* altera_attribute="-name AUTO_CLOCK_ENABLE_RECOGNITION OFF; -name ALLOW_SYNCH_CTRL_USAGE OFF" *) reg [7:0] checked_data;')
 put(p,s)
 put(o/'materialization131.json',json.dumps(dict(inputs=inputs,outputs={p.relative_to(o).as_posix():sha(p) for p in o.rglob('*') if p.is_file()}),indent=2)+'\n')
