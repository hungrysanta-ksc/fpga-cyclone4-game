# SPDX-License-Identifier: MIT
"""Explicit178 report identity with the unchanged177 history wire decoder."""
from pathlib import Path
import argparse,inspect,json
import decode_nes_boundary177 as prior

source=inspect.getsource(prior.report)
assert source.count("'NES-GAME-177'")==1
source=source.replace("'NES-GAME-177'","'NES-GAME-178'")
namespace=dict(prior.__dict__)
exec(compile(source,'decode_clip178','exec'),namespace)
report=namespace['report']

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('report',type=Path);a=p.parse_args()
    print(json.dumps(report(a.report.read_text(encoding='utf8')),indent=2))
