# SPDX-License-Identifier: MIT
"""Selected ordered final ACK and STOP/clock freeze on the new joint boundary."""
import shutil,json,sys
from pathlib import Path
import guard_nes_joint278 as old
from nes_joint280 import patch
from probe_nes_refill280 import tb
from nes_delta231 import once,ROOT,BASE,sha


def main():
    old_adapt=old.adapt
    def joint_patch(d):
        # This directed consumer fixture does not instantiate the ARM plan
        # endpoint, but the common transaction generator patches its source.
        shutil.copyfile(BASE/'probes/nes-joint278/test07/nes_plan_spi200.sv',d/'nes_plan_spi200.sv')
        patch(d)
        reference=Path('C:/Users/mohallo/AppData/Local/Temp/nes-joint280/test05')
        for n in ['source-cost280.hex','source-length280.hex','source-expected280.hex','control280.hex','transaction-cost280.hex']:
            shutil.copyfile(reference/n,d/n)
    def adapt(s):
        s=old_adapt(s)
        s=once(s,' parameter real PHASE=3.5;',' parameter real PHASE=3.5;\n parameter real CPI=1.0;')
        s=tb(s)
        s=once(s,' initial begin : result264', ''' initial begin : source_stop280
  if(GNEG>=53&&GNEG<=55)begin
   case(GNEG)
    53:wait(dut.core.encoder.raw_mode&&dut.core.encoder.state==dut.core.encoder.FSTORE);
    54:wait(dut.core.transport.reading&&dut.core.transport.count270==14);
    55:wait(dut.core.encoder.state==dut.core.encoder.WAITACK&&dut.core.transport.read_seen);
   endcase
   @(negedge host_clk);disable consumer;disable bus263;
   bus_read=1;bus_write=1;injected264=1;test_abort=1;
  end
 end
 initial begin : result264''')
        return s
    old.CASES.update({53:'STOP during raw MASK/base update',54:'STOP during exchange reply',55:'STOP before input commit'})
    old.patch=joint_patch;old.adapt=adapt
    old.main()
    d=Path(sys.argv[sys.argv.index('--out')+1]).resolve()
    r=json.loads((d/'result.json').read_text())
    r['scope']=__doc__;r['entry_hashes']={}
    for n in ['guard_nes_joint280.py','nes_joint280.py','probe_nes_refill280.py','nes_exchange280.inc','nes_source_exchange280.inc']:
        shutil.copyfile(ROOT/'tools'/n,d/n);r['entry_hashes'][n]=sha(d/n)
    r['source_cost_hashes']={n:sha(d/n) for n in ['source-cost280.hex','source-length280.hex','source-expected280.hex','control280.hex','transaction-cost280.hex']}
    (d/'result.json').write_text(json.dumps(r,indent=2)+'\n')


if __name__=='__main__':main()
