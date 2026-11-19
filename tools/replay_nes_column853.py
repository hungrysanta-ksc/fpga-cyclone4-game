"""Time the identical ARM and SNES links with the column command enabled or disabled."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from replay_nes_output852 import joint, monitor, main, MirrorLink, gates, sha
from nes_raw506 import once
from prepare_nes_column853 import PROBE


def run(temp,clip,phase,enabled,tag,scalar=False,eager=False,arm=None,client=None,budget=None):
    root=temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')
    arm=arm or PROBE/('link3/src' if eager else 'link5/src')
    client=client or PROBE/('client' if scalar else 'fast')
    source=json.loads((root/f'sender-{clip}/sender.json').read_bytes())
    original=joint.Runtime.__init__
    def init(cpu,a,link):
        original(cpu,a,link)
        if 'disable_column' not in cpu.layout['nes_native_sink165']:
            return
        field=cpu.layout['nes_native_sink165']['disable_column']
        cpu.u.mem_write(cpu.rt+cpu.layout['nes_native_runtime165']['sink']+field,bytes([not enabled]))
    def template(s):
        s=monitor(s,clip)
        s=once(s,'local n=pb(0)==2 and pw(12) or pw(14)\n   for offset',
                 'local n=pb(0)==9 and 1472 or pb(0)==2 and pw(12) or pw(14)\n   for offset')
        labels=json.loads((client/'labels.json').read_bytes())
        # All hooks observe clocks without altering the client or its schedule.
        hooks=[]
        for label in ('column_write','literal1814','column_service','accepted'):
            if label not in labels:
                continue
            hooks.append(f"checkedMem527(function() if packet and pb(1)==2 then sample516('{label}') end end,emu.callbackType.exec,{labels[label]})")
        s=once(s,'local function loaded()', '\n'.join(hooks)+'\nlocal function loaded()')
        return s
    argv=['replay','','','','','',tag,str(budget or Path.home()/'Downloads/nes-budget-mmc826.txt')]
    with patch.object(sys,'argv',argv),patch.object(MirrorLink,'lookup_file',root/f'hits-{clip}/hits.json'),gates(source,True),patch.object(joint.Runtime,'__init__',init):
        main(root/clip,clip,'jointmirror',phase,temp,arm=arm,client=client,client_hash=sha(client/'sink165.sfc'),
             link_class=MirrorLink,packet_source=source,adapt_template=template)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('clip',choices=('opening','transition','demo'))
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('policy',choices=('on','off'))
    p.add_argument('tag')
    p.add_argument('--scalar',action='store_true')
    p.add_argument('--eager',action='store_true')
    p.add_argument('--arm',type=Path)
    p.add_argument('--client',type=Path)
    a=p.parse_args()
    run(a.temp,a.clip,a.phase,a.policy=='on',a.tag,scalar=a.scalar,eager=a.eager,arm=a.arm,client=a.client)
