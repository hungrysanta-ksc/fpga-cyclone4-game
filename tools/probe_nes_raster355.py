# SPDX-License-Identifier: MIT
import probe_nes_raw352 as previous
from nes_raster355 import native
engine=previous.engine
engine.native=native
engine.__file__=__file__
if __name__=='__main__':engine.main()
