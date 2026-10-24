# SPDX-License-Identifier: MIT
import os
import map_nes_ingress338 as previous
from nes_runs342 import apply,host
old=previous.patch

def patch(d):
 old(d);host(d)
 if os.environ.get('NES342_HOST_ONLY')!='1':apply(d)
previous.engine.apply=patch
if __name__=='__main__':previous.engine.main()
