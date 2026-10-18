# SPDX-License-Identifier: MIT
"""Replay batch receiver with actual span flush counts and service boundaries."""
from pathlib import Path
import json,sys
import test_nes_maskrun247 as base

OBSERVE=r'''
local detail247=assert(io.open(OUT_DIR..'/batch-detail247.csv','w'))
detail247:write('generation,ordinal,event,clock,cursor,start,finish\n')
local function detailhook247(name)
 detail247:write(string.format('%d,%d,%s,%d,%d,%d,%d\n',pw(8),ordinal,name,emu.getState().masterClock,word(0x80),word(0x94),word(0x96)));detail247:flush()
end
'''


def main():
 client=Path(sys.argv[sys.argv.index('--client')+1]);labels=json.loads((client/'labels.json').read_text());extra=OBSERVE
 for name in ('mask_record247','batch_range247','batch_ranged247','batch_flush247','profile_service247','profile_serviced247'):
  extra+='emu.addMemoryCallback(function()detailhook247('+json.dumps(name)+')end,emu.callbackType.exec,'+str(labels[name])+')\n'
 base.OBSERVE+=extra;base.__file__=__file__;base.__doc__=__doc__;base.main()


if __name__=='__main__':main()
