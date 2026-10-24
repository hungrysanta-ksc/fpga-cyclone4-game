# SPDX-License-Identifier: MIT
import map_nes_control314 as old
from nes_response315 import apply
previous=old.patch
def patch(d):previous(d);apply(d)
old.old.apply=patch
if __name__=='__main__':old.old.main()
