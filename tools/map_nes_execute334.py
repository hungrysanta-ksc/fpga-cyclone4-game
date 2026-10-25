# SPDX-License-Identifier: MIT
import map_nes_execute332 as old
from nes_execute334 import apply
previous=old.patch


def patch(d):previous(d);apply(d)


old.old.old.old.old.old.old.apply=patch
if __name__=='__main__':old.old.old.old.old.old.old.main()
