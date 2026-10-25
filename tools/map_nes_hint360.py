# SPDX-License-Identifier: MIT
"""Host359 plus five-entry sequential cache capacity; no EA/lease controller credit."""
import map_nes_host359 as previous
from nes_cache360 import apply
old_patch=previous.patch
def patch(d):old_patch(d);apply(d)
previous.previous.engine.apply=patch
if __name__=='__main__':previous.previous.engine.main()
