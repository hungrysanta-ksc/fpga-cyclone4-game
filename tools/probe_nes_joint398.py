# SPDX-License-Identifier: MIT
"""398 live actual-count EA; shared byte controller revision is materialized."""
import probe_nes_joint396 as prior
from nes_joint398 import arm,rtl
prior.old.apply_arm=lambda d,cold_quantum=0:arm(d)
prior.old.apply_rtl=rtl
prior.old.__file__=__file__
prepare=prior.old.prepare
def fresh(d,last,cold_quantum=0):
 src=prepare(d,last,cold_quantum)+['nes_byte398.sv']
 from nes_joint398 import hint_top
 q=d/'joint266_tb.sv';q.write_text(hint_top(q.read_text().replace('[113:0]','[153:0]').replace('dut.flow.header[0]','dut.flow.op')),newline='\n')
 s=q.read_text();at=s.rindex('endmodule')
 s=s[:at]+''' always @(posedge host_clk)if(!reset&&dut.flow.write_end&&dut.flow.ap==24'h006058)$display("FINAL398 t%0t f%0d phase%0d empty%0b active%0b tileempty%0b sealed%0b view%0d data%h mask%h written%h fence%h accepted%0d retired%0d reserved%0b",$time,f,dut.flow.phase,dut.flow.storage_empty312,dut.flow.active_fragment,dut.flow.tile_empty396,sealed,dut.flow.view_at,dut.flow.dp,dut.flow.mask,dut.flow.written,dut.flow.fence,dut.flow.queue.accepted,dut.flow.queue.retired,dut.flow.queue.reserved398);
 always @(posedge dut.flow.fault)if(!reset)$display("FAULT398 t%0t f%0d pc%0d failed%0b q%0b tile%0b tap%0b cpu%0b pe%0b ce%0b phase%0d view%0d mask%h token%h fence%h event%0d kind%0b flags%h",
  $time,f,dut.flow.debug_pc,dut.flow.failed,dut.flow.qfault,dut.flow.tile_fault,dut.flow.tap_fault,dut.flow.cpufault,dut.flow.pe,dut.flow.ce,dut.flow.phase,dut.flow.view_at,dut.flow.mask,dut.flow.written,dut.flow.fence,dut.flow.queue.event_count,dut.flow.queue.event_end,dut.flow.queue.event_flags);
 always @(posedge romfault267)if(!reset)$display("PLANFAULT398 t%0t f%0d endpoint%0b transport%0b source%0b hint%0b",$time,f,planrom.ef,planrom.bf,planrom.sf,planrom.hfault361);
'''+s[at:];s=s.replace('dut.flow.tile_empty396,sealed,dut.flow.view_at','dut.flow.tile_empty396,dut.flow.sealed,dut.flow.view_at');q.write_text(s,newline='\n')
 import json
 from nes_delta231 import sha
 (d/'manifest398.json').write_text(json.dumps(dict(RTL={n:sha(d/n)for n in src},ELF=sha(d/'output.elf'),program=sha(d/'program398.hex'),test=sha(d/'joint266_tb.sv')),indent=2)+'\n')
 # Fail early on the same program/ports, before starting the long frame run.
 # This uses the current wrapper's single seat sequentially, not a second sim.
 import subprocess,sys
 from nes_delta231 import ROOT
 with(d/'preflight398.log').open('wb')as log:
  subprocess.run([sys.executable,str(ROOT/'tools/probe_nes_hint398.py'),'--rtl',str(d),'--out',str(d/'preflight398')],check=True,stdout=log,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW)
 return src
prior.old.prepare=fresh
if __name__=='__main__':prior.old.main()
