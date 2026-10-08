# SPDX-License-Identifier: MIT
"""Fresh physical fit for observation-only source, never CF86 signoff reuse."""
from pathlib import Path
import argparse,json,re,shutil
from nes_clock_observation087 import materialize
from nes_board_diagnostic import constraints
from nes_spi_boot import run,sha,put

def main():
 p=argparse.ArgumentParser()
 for n in ['out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
 files=materialize(out);pins=constraints(out);shutil.copy2(__file__,out/'executed-driver.py')
 put(out/'board.sdc','''create_clock -name board8 -period 125 [get_ports CLKIN]
create_clock -name snes_ref -period 45.454 [get_ports SNES_SYSCLK]
derive_clock_uncertainty
set src [get_registers {*observe|divider[3]}]
set dst [get_registers {*observe|ref_sync[0]}]
if {[get_collection_size $src]!=1 || [get_collection_size $dst]!=1} {error "CF87 synchronizer boundary mismatch"}
set_false_path -from $src -to $dst
# First->second synchronizer remains timed. External SPI IO not signed off.
''')
 shutil.copy2(out/'board.qsf',out/'input-board.qsf.txt')
 result=dict(candidate='NES-CLOCK-OBSERVATION-087',sources={n:sha(out/n) for n in files+['board.sdc','input-board.qsf.txt']},physical_pins=pins,phases={},hardware_execution=False,installable=False,external_io_signoff=False)
 for phase in ['map','fit','sta']:
  run([a.quartus_bin/('quartus_'+phase+'.exe'),'board'],out,phase,1200);result['phases'][phase]=0
  put(out/'result.json',json.dumps(result,indent=2)+'\n');print(phase+' done',flush=True)
 s=(out/'output_files/board.sta.summary').read_text(encoding='latin1')
 slacks=[float(v) for v in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',s,re.M)]
 assert len(slacks)>=12 and min(slacks)>=0
 result.update(summary_slacks=slacks,minimum_constrained_slack_ns=min(slacks))
 put(out/'result.json',json.dumps(result,indent=2)+'\n')
 print((out/'output_files/board.fit.summary').read_text(encoding='latin1'),flush=True)

if __name__=='__main__':main()
