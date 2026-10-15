# SPDX-License-Identifier: MIT
"""Recompute linked queued RUN callbacks; retain platform instruction review."""
import check_nes_status183_arm as prior
from nes_clip178 import replace
source=prior.source
anchor=" review['callbacks']['packet_wire']=review['callbacks'].pop('packet')"
source=replace(source,anchor,anchor+"""
 review['callbacks']['packet_wire']=['nes_window184_barrier','nes_window184_enqueue']
 del review['callbacks']['nes_sink_spi165_exchange']
 review['callbacks']['io']=['guard','transfer']""")
source=replace(source,"'tools/check_nes_status183_arm.py','tools/nes_status183.py'","'tools/check_nes_window184_arm.py','tools/nes_window184.py','tools/nes_status183.py','src/nes/firmware/nes_sink_window184.c','src/nes/firmware/nes_sink_window184.h'")
source=replace(source,'result.update(status_cache_bytes=9,','result.update(window_packets=4,queue_firmware_not_deployable=True,status_cache_bytes=9,')
ns=dict(prior.ns);checker=ns['checker']
checker.CALLBACKS['packet_wire']=['nes_window184_barrier','nes_window184_enqueue']
del checker.CALLBACKS['nes_sink_spi165_exchange']
checker.CALLBACKS['io']=['guard','transfer']
exec(compile(source,'check_window184','exec'),ns)
if __name__=='__main__':ns['main']()
