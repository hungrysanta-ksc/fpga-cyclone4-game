# SPDX-License-Identifier: MIT
import map_nes_read336 as previous
from nes_ingress338 import apply
old_patch=previous.patch


def patch(d):old_patch(d);apply(d)


engine=previous.old.old.old.old.old.old.old
engine.apply=patch
if __name__=='__main__':engine.main()
