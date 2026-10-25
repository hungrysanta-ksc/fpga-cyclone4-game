# SPDX-License-Identifier: MIT
import map_nes_ingress338 as previous
from nes_host359 import apply
old_patch=previous.patch
def patch(d):old_patch(d);apply(d,board=True)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
