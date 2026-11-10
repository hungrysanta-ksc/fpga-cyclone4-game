"""Actual65816 retirement/beam/STOP with queue-empty advisory publication."""
import argparse
from pathlib import Path
from unittest.mock import patch
import check_nes_complete685 as suite
from nes_raw506 import once

original=suite.fixture
def fixture(s,l,body):
 s=original(s,l,body)
 return once(s,"assert(v==0xa5 and dmaRemaining==0,'progress before actual DMA completion')",
  "assert(v==0xa5 and dmaRemaining==0,'progress before actual DMA completion')\n assert(word(0x1250)==word(0x1252),'progress before accepted DMA queue drained')")

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ('trace','client','mesen','out'):p.add_argument('--'+n,type=Path,required=True)
 with patch.object(suite,'fixture',fixture):suite.run(p.parse_args())
