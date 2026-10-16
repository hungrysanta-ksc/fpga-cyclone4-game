# SPDX-License-Identifier: MIT
"""Execute209 actual post-STOP formatter with maximal-width trace fields."""
import test_nes_window184_report as prior
from nes_clip178 import replace
s=replace(prior.s,'return n;\'','assert(strstr(text,"plan_error=255\\n")); assert(strstr(text,"plan_sent=65535\\n")); assert(strstr(text,"plan_end=")); return n;\'')
ns=dict(prior.ns);exec(compile(s,'paired209-report','exec'),ns)
if __name__=='__main__':ns['main']()
