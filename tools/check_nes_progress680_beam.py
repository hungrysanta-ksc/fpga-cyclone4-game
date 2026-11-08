"""Check actual late-252-line interior DMA and STOP without altering its code."""
import argparse,inspect
from pathlib import Path
from unittest.mock import patch
import check_nes_beam639 as beam
from check_nes_progress680_interior import fixture
from nes_raw506 import once


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('client','mesen','trace','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out=a.out.resolve()
    s=inspect.getsource(beam.attempt)
    s=once(s,'script=head_fixture(width(map_fixture(script,symbols),1152))',
        'script=fixture(script,symbols,image)')
    s=once(s,'word(0x4004+word(0x1252))>=1152','word(0x4004+selected680)>=1152')
    ns=dict(vars(beam),fixture=fixture);exec(compile(s,'interior680-beam','exec'),ns)
    with patch.object(beam,'attempt',ns['attempt']):beam.main(a)
