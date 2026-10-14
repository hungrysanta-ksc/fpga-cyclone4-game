# SPDX-License-Identifier: MIT
"""Reuse172 safety review, recompute actual173 call graph including timer calls."""
import check_nes_boot172_arm as prior
source=prior.source
for a,b in [('GAME172-DEV','GAME173-DEV'),('GAME 172.nh1','GAME 173.nh1'),('progress-172.txt','progress-173.txt'),('last-172.txt','last-173.txt')]:
 assert a in source;source=source.replace(a,b)
source=source.replace("'tools/check_nes_boot172_arm.py','tools/nes_boot172_mcu.py','src/nes/firmware/nes_boot172.inc'", "'tools/check_nes_profile173_arm.py','tools/nes_profile173.py','src/nes/firmware/nes_boot172.inc'")
anchor="review=json.loads((ROOT/'analysis/pacing167-stack-review.json').read_bytes())"
assert anchor in source
source=source.replace(anchor,anchor+"\n review['callbacks']['nes_runtime165_step']=['native_ticks165']")
source=source.replace("result.update(io_trace_bytes=20", "assert re.search(r'^\\S+ 00000028 B nes_trace166$',nm,re.M)\n assert b'trace_schema=173' in fw and b'profile_last_display_tick=' in fw\n result.update(profile_trace_bytes=40,io_trace_bytes=20")
source=source.replace('assert hashlib.sha256(restored.encode()).hexdigest()==h,n',"restored=restored.replace('return getticks();','nes_trace166.now=getticks();return nes_trace166.now;')\n   assert hashlib.sha256(restored.encode()).hexdigest()==h,n")
namespace=dict(prior.namespace)
namespace['checker'].CALLBACKS['nes_runtime165_step']=['native_ticks165']
exec(compile(source,'check_profile173','exec'),namespace)
if __name__=='__main__':namespace['main']()
