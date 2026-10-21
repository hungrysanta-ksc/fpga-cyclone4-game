# SPDX-License-Identifier: MIT
"""Inherited independent CRC/receipt/STOP/final-ACK tests on endpoint290 RTL."""
import guard_nes_joint287 as prior
import sys
from nes_joint290 import apply


def main():
    if '--cases' not in sys.argv:sys.argv.extend(['--cases','3,23,24,39-52,56-63'])
    old=prior.apply
    def patch(d):old(d);apply(d)
    prior.apply=patch;prior.main()


if __name__=='__main__':main()
