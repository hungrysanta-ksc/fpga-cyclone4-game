# SPDX-License-Identifier: MIT
"""Move scrub readiness to the NES port and restrict source ownership to RUN."""
import argparse
import json
from pathlib import Path
from prepare_nes_close561 import prepare as close561
from nes_raw506 import once,sha


def prepare(base,out):
    close561(base,out)
    root=Path(__file__).resolve().parents[1]
    pins=json.loads((root/'analysis/trial558-verification.json').read_text())['inputs']
    def edit(name,changes):
        p=out/name
        assert sha(p)==pins[name]
        s=p.read_text()
        for old,new in changes:
            s=once(s,old,new)
        p.write_text(s,newline='\n')
    edit('nes_live_joint.sv',[
        ('.reset(diagnostic_reset),.read_reset(common_reset)', '.reset(diagnostic_reset),.read_reset(raw_stop)'),
        (' nes_spi_boot loader_boot(', ''' // Local RAM scrub completes on the NES clock. Hold both sides of the
 // NES ready/valid handshake until core_release, leaving PSRAM idle in RUN.
 wire boot_read_ready;
 assign native_mem_ready=boot_read_ready&&!reset;
 nes_spi_boot loader_boot('''),
        ('.rom_request(native_mem_request),.rom_address(native_mem_address),.rom_ready(native_mem_ready)',
         '.rom_request(native_mem_request&&!reset),.rom_address(native_mem_address),.rom_ready(boot_read_ready)')])
    edit('nes_rom_boot.sv',[
        ('.READ_CYCLES(16)', '.READ_CYCLES(16),.HOLD_SOURCE_IN_CHECK(1)'),
        ('.rom_request(rom_request && run_enable)', '.rom_request(rom_request)')])
    edit('nes_rom_physical.sv',[
        ('parameter integer READ_CYCLES=3','parameter integer READ_CYCLES=3, parameter integer HOLD_SOURCE_IN_CHECK=0'),
        (' always @(posedge clk or posedge reset)\n  if(reset)source_reset', ''' // RUN ownership reaches the source through this asynchronous assertion
 // and two local release edges. CHECK continues to use the memory port.
 wire source_cancel=reset||(HOLD_SOURCE_IN_CHECK!=0 && check_mode);
 always @(posedge clk or posedge source_cancel)
  if(source_cancel)source_reset''')])


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('base','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
