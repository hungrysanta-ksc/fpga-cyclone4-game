# SPDX-License-Identifier: MIT
import map_nes_response315 as old
from nes_joint317 import apply
previous=old.patch
def patch(d):previous(d);apply(d)
old.old.old.apply=patch
if __name__=='__main__':old.old.old.main()
