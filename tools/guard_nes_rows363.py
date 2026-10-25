# SPDX-License-Identifier: MIT
"""Existing private/final checks plus local-query, row credit and handoff STOP."""
from pathlib import Path
if __name__=='__main__':
 p=Path(__file__).with_name('guard_nes_query356.py');s=p.read_text()
 s=s.replace("'probe_nes_query356.py'","'probe_nes_rows363.py'")
 s=s.replace('dut.core.query356.ns==dut.core.query356.WAIT','dut.core.rows363.q_pending')
 s=s.replace('wait(dut.core.raw_response)', 'wait(dut.core.row_valid363&&dut.source_take363)')
 s=s.replace("24:'STOP collector query in flight'", "27:'STOP both row slots held',24:'STOP collector query in flight'")
 s=s.replace('STOP returned query before source consume','STOP row byte before codec consume')
 s=s.replace('  else if(NEG319==24)wait', '  else if(NEG319==27)wait(dut.core.rows363.active&&dut.core.rows363.state==dut.core.rows363.SPACE&&dut.core.rows363.valid0&&dut.core.rows363.valid1&&!dut.core.rows363.ready0&&!dut.core.rows363.ready1);\\n  else if(NEG319==24)wait')
 s=s.replace(" exec(compile(s,str(p),'exec')", " s=s.replace(\"'check_nes_final336.py'\",\"'check_nes_final359.py'\")\n exec(compile(s,str(p),'exec')")
 exec(compile(s,'guards363','exec'),dict(__name__='__main__',__file__=__file__))
