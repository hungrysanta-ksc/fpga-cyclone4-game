# SPDX-License-Identifier: MIT
import map_nes_owner319 as old
from nes_expand325 import apply
previous=old.patch
def patch(d):previous(d);apply(d)
old.old.old.old.apply=patch
if __name__=='__main__':old.old.old.old.main()
