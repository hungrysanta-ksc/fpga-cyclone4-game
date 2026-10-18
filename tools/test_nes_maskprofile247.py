# SPDX-License-Identifier: MIT
"""Observe exact receiver record preparation/copy/append/service boundaries."""
from pathlib import Path
import json,sys
import test_nes_maskrun247 as base

OBSERVE=r'''
local detail247=assert(io.open(OUT_DIR..'/mask-detail247.csv','w'))
detail247:write('generation,ordinal,event,clock,cursor,group,mask\n')
local function detailhook247(name)
 detail247:write(string.format('%d,%d,%s,%d,%d,%d,%d\n',pw(8),ordinal,name,emu.getState().masterClock,word(0x80),word(0x86)//16,word(0x84)));detail247:flush()
end
'''


def main():
    client=Path(sys.argv[sys.argv.index('--client')+1]);labels=json.loads((client/'labels.json').read_text())
    extra=OBSERVE
    for name in ('mask_record247','profile_copy247','profile_copied247','profile_append247','profile_appended247','profile_service247','profile_serviced247'):
        extra+='emu.addMemoryCallback(function()detailhook247('+json.dumps(name)+')end,emu.callbackType.exec,'+str(labels[name])+')\n'
    base.OBSERVE+=extra;base.__file__=__file__;base.__doc__=__doc__;base.main()


if __name__=='__main__':main()
