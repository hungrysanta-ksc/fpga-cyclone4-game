# SPDX-License-Identifier: MIT
"""212 planner/sparse sink object ABI and stack; NOT full linked RUN approval."""
import inspect
import check_nes_resident211_arm as old
from nes_clip178 import replace

def main():
 s=inspect.getsource(old.main)
 s=replace(s,"['.c','.h']", "['.c','.h','.inc']")
 s=replace(s,"objects=['nes_resident211','nes_planner211','nes_plan191']", "objects=['nes_resident211','nes_planner211','nes_native_sink165','nes_sink_trace168']")
 s=replace(s,"spi_snes_consumer_integrated=False,", "sparse_consumer_pair_verified=True,production_runtime_connected=False,")
 ns=dict(old.__dict__);ns.update(__doc__=__doc__,__file__=__file__)
 exec(compile(s,'dirty212-arm','exec'),ns);ns['main']()
if __name__=='__main__':main()
