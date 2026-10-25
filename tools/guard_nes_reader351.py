# SPDX-License-Identifier: MIT
"""Reader351 header/descriptor/expected STOP plus retained consumption guards."""
from pathlib import Path
if __name__=='__main__':
    p=Path(__file__).with_name('guard_nes_port350.py')
    s=p.read_text().replace("'probe_nes_port350.py'","'probe_nes_reader351.py'")
    s=s.replace('dut.flow.state==dut.flow.HLOAD315&&dut.flow.at==5',
                'dut.flow.state==dut.flow.HLOAD315&&dut.flow.header_pending351&&dut.flow.return_addr351==10')
    s=s.replace('dut.flow.state==dut.flow.DCAP','dut.flow.state==dut.flow.PCAP&&dut.flow.read_kind351==1')
    s=s.replace('dut.flow.queue.read_address312','dut.flow.ram_address351')
    exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
