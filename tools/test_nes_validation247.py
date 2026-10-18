# SPDX-License-Identifier: MIT
"""Actual range marking: independent byte oracle for receipt and BOTH banks."""
from pathlib import Path
import json,sys
import test_nes_maskbatch247 as batch

OBSERVE=r'''
local range247=assert(io.open(OUT_DIR..'/range247.csv','w'))
range247:write('generation,start,count,take,bank\n')
local pendingrange247=nil
local function checkrange247()
 if not pendingrange247 then return end
 for addr,value in pairs(pendingrange247) do assert(rd(addr)==value,'range bitmap oracle '..addr)end
 pendingrange247=nil
end
local function startrange247()
 checkrange247()
 local first=word(0x6a);local count=word(0x6c);local bank=word(0x1254)
 assert(count>0 and first+count<=1328 and (bank==0 or bank==166),'range admission')
 local take=math.min(16-(first%16),count);local expected={}
 for i=0,165 do expected[0x1280+i]=rd(0x1280+i)end
 for i=0,331 do expected[0x1340+i]=rd(0x1340+i)end
 for bit=first,first+take-1 do
  local at=math.floor(bit/8);local mask=1<<(bit%8)
  assert((expected[0x1280+at]&mask)==0,'normal duplicate')
  expected[0x1280+at]=expected[0x1280+at]|mask
  expected[0x1340+bank+at]=expected[0x1340+bank+at]|mask
 end
 pendingrange247=expected
 range247:write(string.format('%d,%d,%d,%d,%d\n',pw(8),first,count,take,bank));range247:flush()
end
'''


def main():
 client=Path(sys.argv[sys.argv.index('--client')+1]);labels=json.loads((client/'labels.json').read_text())
 body=(client/'body.bin').read_bytes();target=labels['mark212']&65535;needle=bytes((0x20,target&255,target>>8))
 hits=[i for i in range(len(body)-2) if body[i:i+3]==needle];assert len(hits)==1
 extra=OBSERVE+'emu.addMemoryCallback(startrange247,emu.callbackType.exec,'+str(labels['bits212'])+')\n'
 extra+='emu.addMemoryCallback(checkrange247,emu.callbackType.exec,'+str(0x7e2000+hits[0]+3)+')\n'
 batch.OBSERVE+=extra;batch.__file__=__file__;batch.__doc__=__doc__;batch.main()


if __name__=='__main__':main()
