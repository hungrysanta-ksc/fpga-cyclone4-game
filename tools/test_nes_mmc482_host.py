# SPDX-License-Identifier: MIT
"""Actual482 C/FatFS/programmer/run136 host check; native/observer peers modeled.

Adds stale79/7a profile rejection to the retained47920-case harness.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
s = (ROOT/'tools/test_nes_mmc479_loader.py').read_text(encoding='utf8')
def once(old, new):
    global s
    assert s.count(old) == 1, old[:100]
    s = s.replace(old, new)
once('s = fixture.read_text()', '''s = fixture.read_text().replace('if(tx[0]==0x73){rx[1]=0xe6;rx[7]=2;}', 'if(tx[0]==0x73){rx[1]=0xe6;rx[7]=3;}')''')
once('STALE_READ_TAG=19};', 'STALE_READ_TAG=19,STALE79=20,STALE7A=21};')
once('board_id=test==WRONG_ID?0x74:(test==NROM_ID?0x78:0x79);',
     'board_id=test==WRONG_ID?0x74:(test==NROM_ID?0x78:(test==STALE79?0x79:(test==STALE7A?0x7a:0x7b)));')
once("'i<=STALE_READ_TAG'", "'i<=STALE7A'")
once("assert log.count('case=') == 20 and 'case=19' in log", "assert log.count('case=') == 22 and 'case=21' in log")
s = s.replace("'cases': 20", "'cases': 22")
s = s.replace("'wrong NROM78 and legacy74 board'", "'wrong NROM78/legacy74 and stale MMC79/7a boards'")
s = s.replace('__doc__', repr(__doc__))
exec(compile(s, str(ROOT/'tools/test_nes_mmc479_loader.py'), 'exec'), {'__name__': '__main__', '__file__': str(ROOT/'tools/test_nes_mmc479_loader.py')})
