# SPDX-License-Identifier: MIT
"""Cross the two equal-sized 955 map packets and the partial DMA direction at fixed arrivals."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
from nes_raw506 import once, sha


def run(a):
    a.frames=53
    assert sha(a.probe/'client.sfc')==sha(a.client/'sink165.sfc')
    def observer(_,args,unused):
        s=(args.probe/'capture.lua').read_text(encoding='utf8')
        s=once(s,'local ROOT='+json.dumps(args.probe.resolve().as_posix()),'local ROOT='+json.dumps(args.out.as_posix()))
        s=once(s,'checkedMem527(function()rpc()end','emu.addMemoryCallback(function()rpc()end')
        return once(s,'checkedEvent527(function()\n if sequence==1','emu.addEventCallback(function()\n if sequence==1')

    def edit(script):
        path=a.out/'arrivals.tsv'
        rows=[line.split('\t') for line in path.read_text().splitlines()]
        if a.swap:
            pair={}
            for i,(clock,h,bulk) in enumerate(rows[:-1]):
                packet=bytes.fromhex(h)
                offset=int.from_bytes(packet[10:12],'little')
                if packet[:2]==b'\x02\x02' and int.from_bytes(packet[8:10],'little')==955 and offset in (2048,2240):
                    assert offset not in pair and not bulk and len(packet)==208
                    pair[offset]=(i,packet)
            for offset, (i,packet) in pair.items():
                other=pair[4288-offset][1]
                assert packet[4:10]==other[4:10] and packet[12:16]==other[12:16]
                rows[i][1]=(packet[:10]+other[10:]).hex()
            assert len(pair)==2
        rows[-1][0]=str(int(rows[-2][0])+1)
        path.write_text(''.join('\t'.join(r)+'\n' for r in rows),newline='\n')
        if a.beam_log:
            assert 'local sample626' in script and a.probe==a.trace and not a.swap
            labels=json.loads((a.client/'labels.json').read_text())
            script=once(script,'local pending526=nil',f'''local pending526=nil
local fallback626=false
emu.addMemoryCallback(function()fallback626=false end,emu.callbackType.exec,{labels['prefix523']})
emu.addMemoryCallback(function()fallback626=true end,emu.callbackType.exec,{labels['fallback_length532']})''')
            script=once(script,"  sample516('idle524',0x10000+off)","""  if fallback626 and n==1344 then
   local f=assert(io.open(ROOT..'/fallback.csv','a'))
   f:write(word(0x1226),',',sample626,',',n,',',off,'\\n');f:close()
  end
  if word(0x1226)==955 and n>=1152 then
   local f=assert(io.open(ROOT..'/wide955.csv','a'))
   f:write(sample626,',',word(0x4004+i),',',n,',',off,',',fallback626 and 1 or 0,'\\n');f:close()
  end
  sample516('idle524',0x10000+off)""")
        return script

    def compare(before,after):
        first=min(int(r['clock']) for r in before if r['g']=='955')
        prefix=lambda rows:[r for r in rows if int(r['clock'])<first]
        identical=prefix(before)==prefix(after)
        if a.probe==a.trace:
            assert identical
            if not a.swap:
                assert before==after
        return dict(matched_before_955=identical,swap=a.swap,source=sha(a.trace/'packets.jsonl'),
                    consumer=sha(a.client/'sink165.sfc'))
    with patch.object(replay,'observe',observer):
        replay.run(a,edit_script=edit,compare_trace=compare,source_client=a.original)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('client','original','probe','trace','mesen','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--swap',action='store_true')
    p.add_argument('--beam-log',action='store_true')
    run(p.parse_args())
