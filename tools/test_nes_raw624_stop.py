# SPDX-License-Identifier: MIT
"""Assert STOP at each of the three certified-path service boundaries."""
import argparse
import json
from pathlib import Path

from test_nes_seal538_stop import exercise


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('client','trace','mesen','out'):
        p.add_argument('--'+key,type=Path,required=True)
    a=p.parse_args()
    a.out=a.out.resolve()
    a.out.mkdir(parents=True,exist_ok=False)
    results=[exercise(a,g,f'row624_{pair}') for g in (907,922) for pair in range(3)]
    results.extend(exercise(a,906,label) for label in ('raw_row489','raw_high489'))
    (a.out/'result.json').write_text(json.dumps(results,indent=2)+'\n')
