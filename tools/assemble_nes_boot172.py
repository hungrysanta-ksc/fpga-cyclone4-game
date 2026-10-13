# SPDX-License-Identifier: MIT
"""Reuse171 routed FPGA; replace only the SNES boot ROM MIF."""
import inspect
import assemble_nes_banked169 as prior
source=inspect.getsource(prior.main)
source=source.replace('f9648bba30ec185fd7c6571080ca6115a25f73da4d81243d6514c3b6859c2dea','cb4585acb23b4ffc5f475da83fb692979b408157bb6c3dcdcc1e0170b6a2b68e')
source=source.replace('169','172').replace('assemble_nes_banked172.py','assemble_nes_boot172.py')
namespace=dict(prior.__dict__);exec(compile(source,'assemble_boot172','exec'),namespace)
if __name__=='__main__':namespace['main']()
