# SPDX-License-Identifier: MIT
"""Matching whole Quartus Lite MAP, including bounded compact-plan ingress."""
import map_nes_context375 as old
import nes_compact390 as compact
previous=old.board
def board(d):previous(d);compact.rtl(d)
old.board=board
if __name__=='__main__':old.main()
