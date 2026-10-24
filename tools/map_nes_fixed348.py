# SPDX-License-Identifier: MIT
import os
import map_nes_ingress338 as previous
from nes_fixed348 import source
from nes_control348 import apply
old=previous.patch
def patch(d):
 old(d)
 if os.environ.get('NES348_CONTROL')!='1':source(d)
 if os.environ.get('NES348_SOURCE')!='1':apply(d)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
