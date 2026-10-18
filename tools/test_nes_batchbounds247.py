# SPDX-License-Identifier: MIT
"""Actual receiver span gap96/98 and final4096 endpoint after two displays."""
import inspect
import test_nes_fastmasks247 as base
from nes_delta231 import once


def main():
 s=inspect.getsource(base.main)
 for old,new in [('for mask in range(1,256):','for group,mask in ((1,128),(8,1),(14,4),(255,128)):'),('record=bytearray([mask,mask]);receipt[mask]=mask','record=bytearray([group,mask]);receipt[group]=mask'),('at=mask*16+bit*2','at=group*16+bit*2'),('"masks":255','"masks":4'),('"words":1024','"words":4'),('PASS FASTMASKS247 masks=255 words=1024 exact_map=4096','PASS BATCHBOUNDS247 gap96/98 endpoint4096 exact_map=4096')]:s=once(s,old,new)
 ns=dict(base.__dict__);ns.update(__file__=__file__,__doc__=__doc__);exec(compile(s,'batchbounds247','exec'),ns);ns['main']()


if __name__=='__main__':main()
