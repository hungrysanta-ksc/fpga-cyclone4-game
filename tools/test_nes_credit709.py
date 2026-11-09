"""Actual linked ARM/65816 schedule with separately RTL-checked E1 response.

Only pre-transmission response bytes change; no acceptance/retirement time is
advanced. The normal timed SPI transfer and endpoint acceptance still run.
"""
import runpy
from unittest.mock import patch
from test_nes_raw506_joint import Link

original=Link.response
def response(self,tx):
    if tx[0]==0xe1:
        # Call the active E0 response (including existing progress wrapper).
        # No E0 transaction or latency is invented; these bytes share E1 wire.
        r=self.response(b'\xe0'+bytes(19))
        return r[:len(tx)] if len(tx)<20 else r+bytes(len(tx)-20)
    return original(self,tx)

if __name__=='__main__':
    with patch.object(Link,'response',response):
        runpy.run_module('test_nes_longrun694',run_name='__main__')
