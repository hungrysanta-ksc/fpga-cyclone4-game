# SPDX-License-Identifier: MIT
import os
import map_nes_executor313 as old
from nes_control314 import apply,fsm
previous=old.apply
def patch(d):
    previous(d)
    (fsm if os.environ.get('NES314_FSM_ONLY')=='1' else apply)(d)
old.apply=patch
if __name__=='__main__':old.main()
