"""Unchanged688 CPU schedule; bind the separately checked689 RTL interface."""
import argparse,json,runpy,sys
from pathlib import Path
from nes_raw506 import sha
if __name__=='__main__':
    p=argparse.ArgumentParser(add_help=False);p.add_argument('--rtl-evidence',type=Path,required=True);p.add_argument('--board689',type=Path,required=True)
    a,rest=p.parse_known_args();r=json.loads(a.rtl_evidence.read_text());assert r['passed']
    for n,h in r['pins'].items():
        root=a.rtl_evidence.parent if n.endswith('_tb.sv') else a.board689
        assert sha(root/n)==h,n
    sys.argv=[sys.argv[0],*rest]
    print('STATUS689 actual RTL interface guards pinned; SPI/IRQ/ROM remain timing model',flush=True)
    runpy.run_module('test_nes_owner688',run_name='__main__')
