# SPDX-License-Identifier: MIT
"""STOP/ordered ACK/independent H2 guards on the single identity owner."""
import json,shutil,sys
from pathlib import Path
import guard_nes_joint280 as old
from nes_joint284 import patch as prior
from nes_joint286 import apply
from nes_delta231 import once,ROOT,sha


def patch(d):prior(d);apply(d)


def main():
    previous=old.tb;old.patch=patch
    def tb(s):
        s=previous(s).replace('[106:0] link270','[107:0] link270')
        s=once(s,'  if(PRENEG==4)prelude262[19]=prelude262[19]^1;', '''  if(GNEG>=56&&GNEG<=60)begin : forged286
   integer where286;reg [15:0] check286;
   case(GNEG)56:where286=20;57:where286=24;58:where286=28;59:where286=36;default:where286=19;endcase
   prelude262[where286]=prelude262[where286]^1;
   check286=16'hffff;for(integer k286=16;k286<46;k286++)check286=c16(check286,prelude262[k286]);
   prelude262[46]=check286[7:0];prelude262[47]=check286[15:8];injected264=1;
  end
  if(PRENEG==4)prelude262[19]=prelude262[19]^1;''')
        s=once(s,' initial begin : result264',''' initial begin : immutable286
  reg [83:0] admitted_before286;
  if(GNEG==61)begin
   wait(dut.flow.have_identity&&dut.core.validator.context_complete);
   @(negedge host_clk);admitted_before286=dut.flow.admitted286;
   force dut.flow.full_idata278=84'h123456789abcdef012345;
   repeat(32)@(negedge host_clk);
   if(dut.flow.admitted286!==admitted_before286||
      dut.core.validator.epoch!==admitted_before286[83:52]||
      dut.core.validator.generation!==admitted_before286[47:32]||
      dut.core.validator.base_serial!==admitted_before286[31:0])$fatal(1,"unaccepted identity replaced reference");
   release dut.flow.full_idata278;disable bus263;bus_read=1;bus_write=1;injected264=1;test_abort=1;
  end
 end
 initial begin : result264''')
        return s
    old.tb=tb
    old.old.CASES.update({56:'forged H2 epoch with recomputed certificate CRC',57:'forged H2 serial with recomputed certificate CRC',58:'forged H2 generation with recomputed certificate CRC',59:'forged H2 raw with recomputed certificate CRC',60:'forged H2 bank with recomputed certificate CRC',61:'unaccepted mailbox mutation must not replace admitted identity, then STOP'})
    old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1]).resolve()
    r=json.loads((d/'result.json').read_text());r['scope286']=__doc__
    for n in ('guard_nes_joint286.py','nes_joint286.py','nes_joint284.py'):
        shutil.copyfile(ROOT/'tools'/n,d/n);r['entry_hashes'][n]=sha(d/n)
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
