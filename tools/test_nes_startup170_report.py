# SPDX-License-Identifier: MIT
"""Exercise the actual170 formatter at maximum field widths, no SD writes."""
import inspect
import test_nes_sink168_report as prior
source=inspect.getsource(prior.main)
source=source.replace('#include "nes_sink_trace168.h"','#include "nes_sink_trace168.h"\n#include "nes_sink_io170.h"')
source=source.replace(' int n=save_report', ' memset(&nes_sink_io170,255,sizeof nes_sink_io170);\n int n=save_report')
source=source.replace("str(src/'nes_sink_trace168.c'),", "str(src/'nes_sink_trace168.c'),str(src/'nes_sink_io170.c'),")
ns=dict(prior.__dict__);exec(compile(source,'startup170_report','exec'),ns)
if __name__=='__main__':ns['main']()
