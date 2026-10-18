# SPDX-License-Identifier: MIT
"""Standalone MAP of expanded receiver in direct8KiB and split6KiB ROM.

Same synchronous read latency, footer aliases and excluded address gaps.
Reuses frozen storage247 harness with explicit larger high bank. No FIT/STA.
"""
import inspect
import nes_storage247 as base
from nes_delta231 import once


def sources(original):
    r=base.sources(original)
    s=r.pop('split5k')
    for old,new in [('4096+1024','4096+2048'),('[0:1023]','[0:2047]'),("15'd5056","15'd6080"),('address_sync[9:0]','address_sync[10:0]')]:
        s=once(s,old,new)
    return r|{'split6k':s}


def main():
    s=inspect.getsource(base.main)
    for old,new in [('<=5056','<=6080'),('4096:5120','4096:6144'),('addr&1023','addr&2047'),('addr<5056','addr<6080'),('split_body_capacity=4960','split_body_capacity=5984'),('split_body_free=4960','split_body_free=5984')]:
        s=once(s,old,new)
    ns=dict(base.__dict__);ns.update(sources=sources,__file__=__file__,__doc__=__doc__)
    exec(compile(s,'faststorage247','exec'),ns);ns['main']()


if __name__=='__main__':main()
