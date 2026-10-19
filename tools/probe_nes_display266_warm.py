# SPDX-License-Identifier: MIT
"""Same display266 CPU/RTL test, longer wall timeout for instrumented warmup.

Full +acc simulation replays905/906 before907; the 240second harness deadline
expired during warmup. Only the wall deadline changes; CPU/RTL clocks do not.
"""
import inspect
import probe_nes_display266 as old
from nes_delta231 import once


if __name__=='__main__':
 s=once(inspect.getsource(old.main),'deadline=time.monotonic()+240','deadline=time.monotonic()+600')
 s=once(s,"script=ROOT/'tools/probe_nes_display266.py';", "script=ROOT/'tools/probe_nes_display266.py';")
 s=once(s," cpu_result=json.loads", " runner=ROOT/'tools/probe_nes_display266_warm.py';shutil.copyfile(runner,d/runner.name);pins[runner.relative_to(BASE).as_posix()]=sha(runner)\n cpu_result=json.loads")
 ns=dict(old.__dict__);exec(compile(s,'display266-long-warmup','exec'),ns);ns['main']()
