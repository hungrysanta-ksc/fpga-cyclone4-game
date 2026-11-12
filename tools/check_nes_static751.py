# SPDX-License-Identifier: MIT
"""Fault an actual DMA boundary in a replay of a static ROM; leave receiver code untouched."""
import argparse
import csv
import json
from pathlib import Path
from unittest.mock import patch

import replay_nes_map527 as replay
import trace_nes_owner739 as owner
from analyze_nes_bg750 import counters
from analyze_nes_owner739 import read, sha
from nes_raw506 import once


def run(args):
    fixed=replay.run
    def observe(script):
        if args.fault=='stale':
            return script
        if args.fault=='head':
            action="""rpc()
 if sent==retired then
  assert(b522~='FINISH' and target522>st.masterClock)
  target522=st.masterClock;rpc()
 end
 assert(sent>retired and not packet)
 f:write(' ',index,' ',requests[index]:byte(1),' ',requests[index]:byte(2))"""
        else:
            script=once(script,'if pw(8)==957 and pb(0)==9 then stop739=true end','')
            action='stop739=true'
        site=read(args.client/'labels.json')['priority524']
        event='emu.callbackType.write,0x2118' if args.fault=='during' else f'emu.callbackType.exec,{site}'
        watch=f"""local fired751=false
checkedMem527(function()
 if fired751 or word(0x1226)~=957 or packet or regs[0x4302]+256*regs[0x4303]~={args.source} or
    regs[0x4305]+256*regs[0x4306]~={args.size} then return end
 fired751=true
 local st=emu.getState();local f=assert(io.open(ROOT..'/guard751.txt','w'));f:write(st.masterClock)
 {action}
 f:close()
end,{event})
"""
        return once(script,'local finished522=false',watch+'local finished522=false')
    def guarded(a,*,edit_script):
        def compare(old,new):
            assert [r for r in old if int(r['g'])<957]==[r for r in new if int(r['g'])<957]
            return dict(frames_before_fault=52)
        return fixed(a,edit_script=lambda s:observe(edit_script(s)),compare_trace=compare)
    args.mode={'before':'stop','during':'stop','head':'trace','stale':'stale'}[args.fault]
    with patch.object(replay,'run',guarded):
        owner.run(args)
    verify(args)


def verify(args):
    result=read(args.out/'result.json')
    assert result['passed']
    assert not any((args.out/name).exists() for name in ('callback-error.txt','map-error.txt'))
    if args.fault=='stale':
        assert result['last_status']==0xe0
    if args.fault in ('before','during'):
        assert result['last_status'] in (0,0xe4)
    with (args.out/'window.csv').open() as f:
        rows=[r for r in csv.DictReader(f) if r['g']=='957']
    if args.fault=='head':
        t,index,op,section=map(int,(args.out/'guard751.txt').read_text().split())
        first=next(r for r in rows if int(r['clock'])>t and r['event'] in ('ppu_dma','load'))
        assert (first['event'],int(first['index']),int(first['op']),int(first['section']))==('load',index,op,section)
        assert result['commits']==53
    else:
        assert result['commits']==52 and not any(r['op']=='3' and r['event']=='ack' for r in rows)
        assert sha(args.out/'retained.rgb')==sha(args.trace/'frame-956.rgb')
        if args.fault!='stale':
            t=int((args.out/'guard751.txt').read_text())
            starts=[r for r in counters(args.out/'dma748.csv') if r['g']==957 and r['source']==args.source]
            assert sum(r['bytes'] for r in starts)==(args.size if args.fault=='during' else 0)
            if starts:
                assert starts[-1]['clock']<t<=int(rows[-1]['clock']) and rows[-1]['event']=='ppu_last'

    evidence=dict(variant=args.client.name.removeprefix('nes-static751-'),client=sha(args.client/'sink165.sfc'),
                  fault=args.fault,source=args.source,size=args.size,commits=result['commits'],
                  status=result['last_status'],trace=sha(args.out/'window.csv'))
    if args.fault!='stale':
        evidence['injection']=(args.out/'guard751.txt').read_text()
    if args.fault!='head':
        evidence['retained_RGB']=sha(args.out/'retained.rgb')
    (args.out/'verified751.json').write_text(json.dumps(evidence,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('client','mesen','trace','out'):
        p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--source',type=int,default=19104)
    p.add_argument('--size',type=int,default=288)
    p.add_argument('--fault',choices=('before','during','head','stale'),required=True)
    p.add_argument('--verify-existing',action='store_true')
    a=p.parse_args()
    if a.verify_existing:verify(a)
    else:run(a)
