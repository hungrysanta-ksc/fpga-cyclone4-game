# SPDX-License-Identifier: MIT
"""Full184 identity/RUN/IRQ check; release still needs paired RTL/IO/report gates."""
import check_nes_window184_arm as prior
from nes_clip178 import replace
source=prior.source
for a,b in [('GAME183-DEV','GAME184-DEV'),('GAME 183.nh1','GAME 184.nh1'),('progress-183.txt','progress-184.txt'),('last-183.txt','last-184.txt')]:source=replace(source,a,b)
source=replace(source," assert b'sink_io170=' in fw", " assert b'sink_io170=' not in fw and b'sink_window_schema=184' in fw\n assert b'sink_window_flags=' in fw and b'sink_window_ack=' in fw")
source=replace(source,"'tools/check_nes_window184_arm.py','tools/nes_window184.py'","'tools/check_nes_window184_trial_arm.py','tools/nes_window184_trial.py','tools/check_nes_window184_arm.py','tools/nes_window184.py'")
ns=dict(prior.ns);exec(compile(source,'check_window184_trial','exec'),ns)
if __name__=='__main__':ns['main']()
