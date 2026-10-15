# SPDX-License-Identifier: MIT
"""Execute actual184 formatter at maximum widths; no stale IO170 fields."""
import inspect
import test_nes_sink168_report as prior
from nes_clip178 import replace
s=inspect.getsource(prior.main)
s=replace(s,"+' return n;\\n}\\n'", '''+r' assert(strstr(text,"sink_window_schema=184\\n")); assert(strstr(text,"sink_window_error=255\\n")); assert(strstr(text,"sink_window_sent=65535\\n")); assert(strstr(text,"sink_window_retired=65535\\n")); assert(strstr(text,"sink_window_flags=255\\n")); assert(strstr(text,"sink_window_ack=255\\n")); assert(!strstr(text,"sink_io")); return n;'+'\\n}\\n' ''')
ns=dict(prior.__dict__);exec(compile(s,'window184-report','exec'),ns)
if __name__=='__main__':ns['main']()
