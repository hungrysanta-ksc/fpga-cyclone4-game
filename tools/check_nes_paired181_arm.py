# SPDX-License-Identifier: MIT
"""Recompute the complete linked RUN/IRQ bound with the DATA5 callback owner."""
import check_nes_board181_arm as prior
from nes_clip178 import replace

source=replace(prior.source,
    "review['callbacks']['nes_runtime165_step']=['native_ticks165']",
    "review['callbacks']['nes_runtime165_step']=['native_ticks165']\n review['callbacks']['packet_wire']=review['callbacks'].pop('packet')")
source=replace(source,
    "'tools/check_nes_board181_arm.py','tools/nes_board181.py','tools/nes_reject180.py'",
    "'tools/check_nes_paired181_arm.py','tools/nes_paired181.py','tools/nes_packed181.py','tools/nes_stream181.py'")
source=replace(source,
    '181 paired receiver/raw converter/24-byte sink included in the recomputed linked RUN graph. Runtime/platform and optional post-STOP history retained. No FPGA or physical approval.',
    '1813 packed ingress and1815 stream sink included in the linked RUN graph, including span and packet_wire callback. Expired BG key workspace may hold OBJ validation bytes. Platform/history retained; no FPGA or physical approval.')
namespace=dict(prior.namespace)
checker=namespace['checker']
checker.CALLBACKS['packet_wire']=checker.CALLBACKS.pop('packet')
exec(compile(source,'check_paired181','exec'),namespace)
if __name__=='__main__':namespace['main']()
