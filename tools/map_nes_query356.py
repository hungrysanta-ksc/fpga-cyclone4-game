# SPDX-License-Identifier: MIT
import map_nes_ingress338 as previous
from nes_query356 import apply
old_patch=previous.patch
def patch(d):old_patch(d);apply(d)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
