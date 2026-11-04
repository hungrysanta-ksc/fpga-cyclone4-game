"""Run the 561 closed schedule with independent palette/section-5 fixed-fill checks."""
import runpy
from unittest.mock import patch

import observe_nes_repeat545
from nes_raw506 import once

original=observe_nes_repeat545.observe


def observe(source):
    checked=original(source)
    checked=once(checked,'return packet and pb(1)==5 and ((pb(0)==4',
                 'return packet and (pb(1)==5 or pb(1)==3) and ((pb(0)==4')
    return once(checked,'+0x6500+pw(10)','+(pb(1)==5 and 0x6500 or 0x6000)+pw(10)')


if __name__=='__main__':
    with patch.object(observe_nes_repeat545,'observe',observe):
        runpy.run_module('test_nes_close561',run_name='__main__')
