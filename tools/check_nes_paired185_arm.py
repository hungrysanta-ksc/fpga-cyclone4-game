# SPDX-License-Identifier: MIT
"""Full linked185 RUN/IRQ bound, including the renamed converter callback."""
import check_nes_window184_trial_arm as prior
from nes_clip178 import replace
source=prior.source
for a,b in [('GAME184-DEV','GAME185-DEV'),('GAME 184.nh1','GAME 185.nh1'),('progress-184.txt','progress-185.txt'),('last-184.txt','last-185.txt')]:source=replace(source,a,b)
anchor=" review['callbacks']['io']=['guard','transfer']"
source=replace(source,anchor,anchor+"\n review['callbacks']['nes_native_video185_build']=review['callbacks'].pop('nes_native_video165_build')")
source=replace(source,"'tools/check_nes_window184_trial_arm.py','tools/nes_window184_trial.py'","'tools/check_nes_paired185_arm.py','tools/nes_paired185.py','tools/nes_map185.py','tools/nes_pad185.py','tools/check_nes_window184_trial_arm.py','tools/nes_window184_trial.py'")
source=replace(source,'1813 packed ingress and1815 stream sink','1813 packed ingress and1851 map inheritance sink')
ns=dict(prior.ns);checker=ns['checker']
checker.CALLBACKS['nes_native_video185_build']=checker.CALLBACKS.pop('nes_native_video165_build')
exec(compile(source,'check_paired185','exec'),ns)
if __name__=='__main__':ns['main']()
