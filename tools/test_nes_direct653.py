"""Replay direct-cell D1 bytes under the verified board-owner gate."""
import argparse
import json
import runpy
import sys
from pathlib import Path
from unittest.mock import patch
import nes_geometry650
from nes_direct653 import encode
from test_nes_sender652 import gates

if __name__=="__main__":
    p=argparse.ArgumentParser(add_help=False);p.add_argument("--sender653",type=Path,required=True)
    a,rest=p.parse_known_args();sys.argv[1:]=rest
    with gates(json.loads(a.sender653.read_text()),True),patch.object(nes_geometry650,"encode",encode):
        runpy.run_module("test_nes_geometry650",run_name="__main__")
