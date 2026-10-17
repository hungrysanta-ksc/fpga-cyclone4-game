# SPDX-License-Identifier: MIT
"""214 gate retained;215 first-error cleared only on new boot, not budget reset."""
import inspect
import test_nes_startup214_gate as prior
from nes_runtime213 import once
code=prior.CODE.replace('#include "nes_boot214.h"','#include "nes_boot214.h"\n#include "nes_plan215.h"\nstruct nes_plan215 nes_plan215;')
code=once(code,'bool ok=native_boot172(&io);','memset(&nes_plan215,255,sizeof nes_plan215);\n  bool ok=native_boot172(&io);\n  struct nes_plan215 empty={0};assert(!memcmp(&empty,&nes_plan215,sizeof empty));')
s=inspect.getsource(prior.main)
s=once(s,"for n in ['nes_boot214.h','nes_boot214.inc']:","for n in ['nes_boot214.h']:")
s=s.replace(".replace('214','213')",".replace('215','213')")
s=s.replace('tools/test_nes_startup214_gate.py','tools/test_nes_plan215_boot.py')
ns=dict(prior.__dict__);ns.update(CODE=code,__file__=__file__);exec(compile(s,'plan215-boot','exec'),ns)
if __name__=='__main__':ns['main']()
