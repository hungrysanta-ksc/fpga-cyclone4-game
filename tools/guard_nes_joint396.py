# SPDX-License-Identifier: MIT
import inspect
import guard_nes_jobs394 as old
s=inspect.getsource(old.guards).replace('range(1,18)','range(1,20)').replace('13,14,15,16):','13,14,15,16,19):')
s=s.replace('    elif case==13:', "    elif case==19:pp[job][15:17]=struct.pack('<H',2064)\n    elif case==13:")
ns=dict(old.__dict__);exec(compile(s,'guards396','exec'),ns);guards=ns['guards']
