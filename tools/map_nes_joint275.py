# SPDX-License-Identifier: MIT
"""Same whole270 board boundary, actual inline executor replacement, Lite MAP."""
import inspect
import map_nes_joint272 as prior
from nes_joint275 import patch

def main():
 ns=dict(prior.__dict__);ns.update(patch=patch,__file__=__file__,__doc__=__doc__)
 code=inspect.getsource(prior.main)
 code=code.replace('patch(d,shared=a.shared_context)','patch(d)')
 code=code.replace("p=d/'board.qsf';p.write_text(p.read_text()+'\\nset_global_assignment -name SYSTEMVERILOG_FILE nes_parser272.sv\\n',encoding='utf-8',newline='\\n')",'')
 code=code.replace("['nes_joint272.py','map_nes_joint272.py']","['nes_joint275.py','nes_inline275.sv.inc','map_nes_joint275.py']")
 exec(compile(code,'map275-main','exec'),ns);ns['main']()

if __name__=='__main__':main()
