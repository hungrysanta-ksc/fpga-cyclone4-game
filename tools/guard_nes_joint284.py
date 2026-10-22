# SPDX-License-Identifier: MIT
"""Retain ordered ACK, independent coverage and STOP on IRQ284 sources."""
import guard_nes_joint280 as old
from nes_joint284 import patch


def main():
    previous=old.tb;old.patch=patch
    old.tb=lambda s:previous(s).replace('[106:0] link270','[107:0] link270')
    old.main()


if __name__=='__main__':main()
