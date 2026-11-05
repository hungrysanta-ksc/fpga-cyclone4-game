"""Remove the redundant combinational reset mask from the registered OE path."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha
from constraints_nes_board611 import text as cdc
ROOT=Path(__file__).resolve().parents[1]

def prepare(base,out,all_pins=False):
    evidence=json.loads((ROOT/'analysis/board611-verification.json').read_text())
    for n,h in evidence['inputs'].items():assert sha(base/n)==h,(n,'611 input changed')
    out.mkdir(parents=True,exist_ok=False)
    for n in evidence['inputs']:
        (out/n).parent.mkdir(parents=True,exist_ok=True);shutil.copy(base/n,out/n)
    p=out/'nes_rom_physical.sv'
    s=once(p.read_text(),' assign psram_oe=!reading;', ''' // reading_active is asynchronously cleared by mr, including stopped clocks.
 // Driving OE directly removes the duplicate mr combinational mask; SETUP,
 // ACTIVE sample, HOLD release and both ACK domains remain cycle-identical.
 assign psram_oe=!reading_active;''')
    if all_pins:
        # Do not simply drop mr from CE: chip's asynchronous reset must not
        # briefly select the other chip while reading_active is releasing.
        s=once(s,' assign psram_1ce=!(reading && !chip);\n assign psram_2ce=!(reading && chip);', ''' // Dedicated pin owners remove chip/reset decoding from the CE outputs.
 // SETUP uses the chip latched in IDLE; HOLD releases without extra cycles.
 reg [1:0] chip_active;
 always @(posedge mem_clk or posedge mr)
  if(mr)chip_active<=0;
  else if(state==SETUP)chip_active<=chip?2'b10:2'b01;
  else if(state==HOLD || state>RELEASE)chip_active<=0;
 assign psram_1ce=!chip_active[0];
 assign psram_2ce=!chip_active[1];''')
    p.write_text(s,newline='\n')
    (out/'cdc611.sdc').write_text(cdc(),newline='\n')
    extra='\nsource cdc611.sdc\n'
    if all_pins:extra+='set_max_delay 12.0 -from [get_registers {*|reader|chip_active[*]}] -to [get_ports {ROM_1CE ROM_2CE}]\n'
    p=out/'board.sdc';p.write_text(p.read_text()+extra,newline='\n')
    names=list(evidence['inputs'])+['cdc611.sdc']
    (out/'inputs612.json').write_text(json.dumps({n:sha(out/n) for n in names},indent=2)+'\n',newline='\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','out'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--all-pins',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.all_pins)
