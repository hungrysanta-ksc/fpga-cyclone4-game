# SPDX-License-Identifier: MIT
"""Whole host359 plus 17-entry cache capacity; EA dispatch/prefetch lease NOT included."""
import map_nes_host359 as previous
from nes_cache359 import apply
old_patch=previous.patch
def patch(d):old_patch(d);apply(d)
previous.previous.engine.apply=patch
if __name__=='__main__':previous.previous.engine.main()
