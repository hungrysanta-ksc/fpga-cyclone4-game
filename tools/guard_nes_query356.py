# SPDX-License-Identifier: MIT
from pathlib import Path
if __name__=='__main__':
 p=Path(__file__).with_name('guard_nes_read336.py')
 s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_query356.py'")
 s=s.replace("previous.base.old.CASES.update({17:","previous.base.old.CASES.update({24:'STOP collector query in flight',25:'STOP returned query before source consume',26:'STOP input-to-display handoff',17:")
 s=s.replace('  else if(NEG319==17)wait', '  else if(NEG319==24)wait(dut.core.query356.ns==dut.core.query356.WAIT);\n  else if(NEG319==25)wait(dut.core.raw_response);\n  else if(NEG319==26)wait(dut.core.handoff356);\n  else if(NEG319==17)wait')
 s=s.replace('||NEG319==17||NEG319==20)begin','||NEG319==17||NEG319==20||NEG319>=24)begin')
 s=s.replace('        return original(s,a,b)', '        if a==\'endmodule\':b=b.replace(\'  if(v_sealed||lease_valid||staged||rack||flow_retired)\', \'  if(NEG319>=24&&(!dut.core.query_drained356||dut.core.plan_cursor319!=0))$fatal(1,"query not drained356");\\n  if(v_sealed||lease_valid||staged||rack||flow_retired)\')\n        return original(s,a,b)')
 s=s.replace('        return original(s,a,b)', '        if a==\'endmodule\':b=b.replace(\' parameter integer NEG319=0;\', \' parameter integer NEG319=0;\\n always @(posedge source_done)if(injected319&&test_abort)$fatal(1,"source DONE after STOP356");\')\n        return original(s,a,b)')
 exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
