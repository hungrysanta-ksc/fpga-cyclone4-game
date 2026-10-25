# SPDX-License-Identifier: MIT
from pathlib import Path
if __name__=='__main__':
 p=Path(__file__).with_name('guard_nes_read336.py')
 s=p.read_text().replace("'probe_nes_read336.py'", "'probe_nes_host359.py'").replace("'check_nes_final336.py'", "'check_nes_final359.py'")
 exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
