# SPDX-License-Identifier: MIT
"""Actual current formatter, with170 IO trace declaration/object/max fields."""
import inspect
import test_nes_sink168_report as prior
from nes_clip178 import replace
s=inspect.getsource(prior.main)
s=replace(s,'#include "nes_sink_trace168.h"','#include "nes_sink_trace168.h"\n#include "nes_sink_io170.h"')
s=replace(s,' int n=save_report(', ' memset(&nes_sink_io170,255,sizeof nes_sink_io170);\n int n=save_report(')
s=replace(s,"str(src/'nes_sink_trace168.c'),'-o'", "str(src/'nes_sink_trace168.c'),str(src/'nes_sink_io170.c'),'-o'")
ns=dict(prior.__dict__);exec(compile(s,'batch183-report','exec'),ns)
if __name__=='__main__':ns['main']()
