# SPDX-License-Identifier: MIT
"""Record the exact 65816 bulk-release write on the immutable two-phase arrivals."""
import argparse
import json
from unittest.mock import patch
from pathlib import Path

import replay_nes_map527 as replay
from nes_raw506 import once
from trace_nes_owner739 import observe


def record(script, root):
    # Lua accepts literal UTF-8 path characters.
    script=once(script,'local ROOT='+json.dumps(root),'local ROOT='+json.dumps(root,ensure_ascii=False))
    return once(script, '  consumed[#consumed+1]', """  if pw(8)==969 then
   local f=assert(io.open(ROOT..'/consume776.tsv','a'))
   f:write(index,'\\t',pw(16)+65536*pw(18),'\\t',emu.getState().masterClock,'\\n')
   f:close()
  end
  consumed[#consumed+1]""")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('trace', 'out', 'mesen', 'client'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    args.frames = 66
    with patch.object(replay, 'observe', observe):
        replay.run(args, edit_script=lambda script: record(script,args.out.as_posix()))
