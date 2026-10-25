# SPDX-License-Identifier: MIT
import map_nes_ingress338 as previous
from nes_reader351 import apply
old=previous.patch
def patch(d):old(d);apply(d)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
