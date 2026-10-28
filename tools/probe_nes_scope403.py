# SPDX-License-Identifier: MIT
"""Passive402 full-path port/IO/lease/raster trace; no replacement RTL."""
import json
import probe_nes_joint402 as prior
from nes_delta231 import ROOT,sha

prepare=prior.fresh
def traced(d,last,cold_quantum=0):
 sources=prepare(d,last,cold_quantum)
 monitor=(ROOT/'tests/nes-control399/ports.svh').read_text().replace('ports399.csv','ports403.csv').replace('capture&&!dut.flow.read359[33]','capture&&dut.flow.read_pending')
 monitor+=(ROOT/'tests/nes-scope403/extra.svh').read_text()
 p=d/'joint266_tb.sv';s=p.read_text();at=s.rindex('endmodule');s=s[:at]+monitor+s[at:];p.write_text(s,newline='\n')
 m=json.loads((d/'manifest402.json').read_text());m.update(passive_trace403=True,base402_test=sha(prior.BASE/'probes/nes-joint402/live04/joint266_tb.sv'),test=sha(p),monitor_sha256=sha(ROOT/'tests/nes-scope403/extra.svh'))
 (d/'manifest403.json').write_text(json.dumps(m,indent=2)+'\n',newline='\n')
 return sources
prior.driver.prepare=traced
if __name__=='__main__':prior.driver.main()
