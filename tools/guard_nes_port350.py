# SPDX-License-Identifier: MIT
"""338 cancellation traces at header/descriptor response and expected RAM."""
from pathlib import Path

if __name__=='__main__':
    p=Path(__file__).with_name('guard_nes_read336.py')
    s=p.read_text().replace("'probe_nes_read336.py'","'probe_nes_port350.py'")
    s=s.replace('    original=previous.base.old.once',
        "    previous.base.old.CASES.update({30:'STOP with header RAM response pending',31:'STOP with batch descriptor response pending'})\n    original=previous.base.old.once")
    s=s.replace('  else if(NEG319==17)wait(',
        '  else if(NEG319==30)wait(dut.flow.state==dut.flow.HLOAD315&&dut.flow.at==5);\n  else if(NEG319==31)wait(dut.flow.state==dut.flow.DCAP);\n  else if(NEG319==17)wait(')
    s=s.replace("'||NEG319==13||NEG319==17||NEG319==20)begin'",
        "'||NEG319==13||NEG319==17||NEG319==20||NEG319==30||NEG319==31)begin'")
    s=s.replace("        if a=='endmodule':", """        if a=='endmodule':
            b=b.replace('  @(negedge host_clk);injected319=1;', '  @(negedge host_clk);injected319=1; $display("INJECT350 case=%0d state=%0d addr=%0d previous=%0d time=%0t",NEG319,dut.flow.state,dut.flow.queue.read_address312,prevaddr350,$time);')""")
    exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
