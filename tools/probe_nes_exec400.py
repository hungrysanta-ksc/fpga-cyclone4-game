# SPDX-License-Identifier: MIT
import probe_nes_exec398 as old
from nes_fixed400 import program
old.host_program=program
if __name__=='__main__':old.main()
