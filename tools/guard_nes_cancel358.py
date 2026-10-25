# SPDX-License-Identifier: MIT
from pathlib import Path
if __name__=='__main__':
 p=Path(__file__).with_name('guard_nes_query356.py')
 s=p.read_text().replace("'probe_nes_query356.py'","'probe_nes_cancel358.py'")
 exec(compile(s,str(p),'exec'),dict(__name__='__main__',__file__=__file__))
