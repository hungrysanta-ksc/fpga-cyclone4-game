# SPDX-License-Identifier: MIT
from pathlib import Path
if __name__=='__main__':
 p=Path(__file__).with_name('guard_nes_query356.py');s=p.read_text()
 s=s.replace("'probe_nes_query356.py'","'probe_nes_execute362.py'")
 s=s.replace(" exec(compile(s,str(p),'exec')", " s=s.replace(\"'check_nes_final336.py'\",\"'check_nes_final362.py'\")\n exec(compile(s,str(p),'exec')")
 exec(compile(s,'guard362','exec'),dict(__name__='__main__',__file__=__file__))
