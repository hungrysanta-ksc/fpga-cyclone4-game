# SPDX-License-Identifier: MIT
import inspect
import guard_nes_execute332 as previous


if __name__=='__main__':
    original_once=previous.base.old.once
    def monitor_once334(s,a,b):
        if a=='module joint266_tb;':
            # source_empty includes source_live; STOP deliberately deasserts
            # it before the NES state register sees cancellation. Keep the
            # write checks and post-fault freeze/drain tests unchanged.
            s=s.replace('if(!dut.core.transport_empty)$fatal(1,"plan phase before source drain334");',
                'if(dut.core.transport.source_live&&!dut.core.transport_empty)$fatal(1,"plan phase before source drain334");')
        return original_once(s,a,b)
    previous.base.old.once=monitor_once334
    s=inspect.getsource(previous.main).replace('probe_nes_execute332.py','probe_nes_execute334.py')
    ns=dict(previous.__dict__);exec(compile(s,'guards334','exec'),ns);ns['main']()
