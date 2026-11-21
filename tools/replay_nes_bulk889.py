"""Run the full tile reader, or change only the measured 959 OBJ on the original boot."""
import argparse
from pathlib import Path
from unittest.mock import patch
from nes_bulk889 import BASE, WORK, replacement
from nes_raw506 import once
import replay_nes_strip869 as replay
import replay_nes_column853 as other


def packet_override(s):
    old,_,pos,new=replacement()
    before=','.join(map(str,old[pos:pos+len(new)]))
    after=','.join(map(str,new))
    mark='packet=requests[index];sample516("load");reads=0;token={};decodeStart=nil'
    code=f"""
 if active889 or (pw(8)==959 and pb(0)==7 and pb(1)==1 and pw(10)==416) then
  local a,b={{{before}}},{{{after}}}
  if active889 then a,b=b,a end
  for i=1,#a do
   local k={0x2000+pos}+i-1;assert(rd(k)==a[i])
   emu.write(k,b[i],emu.memType.snesWorkRam)
  end
  active889=not active889
 end"""
    return once(s,mark,mark+code)


def run(temp,phase,scene,local):
    assert not local or scene=='dense'
    module=replay.dense if scene=='dense' else other
    main=module.main
    def setup(*args,**kw):
        if local:
            adapt=kw['adapt_template']
            kw['adapt_template']=lambda s:packet_override(adapt(s))
        else:
            client=WORK/'client03'
            kw.update(client=client,client_hash=replay.dense.sha(client/'sink165.sfc'))
        return main(*args,**kw)
    with patch.object(module,'main',setup):
        replay.run(temp,phase,BASE,'889-local' if local else '889-reader',scene)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('scene',choices=('opening','transition','dense'))
    p.add_argument('--local',action='store_true')
    run(**vars(p.parse_args()))
