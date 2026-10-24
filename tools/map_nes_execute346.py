# SPDX-License-Identifier: MIT
import map_nes_ingress338 as previous
from nes_execute346 import source,host
old=previous.patch
def patch(d):old(d);source(d);host(d)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
