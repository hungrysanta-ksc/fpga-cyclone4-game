"""Compare static ROM boot with a generation-local coverage replacement on the old boot."""
import argparse
from pathlib import Path
from unittest.mock import patch
import replay_nes_strip869 as replay
import replay_nes_column853 as other
from nes_coverage886 import BASE, WORK, replacement
from nes_raw506 import once


def run(temp, phase, scene, local):
    assert not local or scene=='dense'
    module=replay.dense if scene=='dense' else other
    original=module.main
    def changes(*args, **kwargs):
        if local:
            adapt=kwargs['adapt_template']
            old, _, pos, code=replacement()
            def template(s):
                s=adapt(s)
                enable=','.join(map(str,code))
                disable=','.join(map(str,old[pos:pos+len(code)]))
                mark='packet=requests[index];sample516("load");reads=0;token={};decodeStart=nil'
                hook=f"""
 if pb(0)==3 and (pw(8)==959 or pw(8)==960) then
  local old,new={{{disable}}},{{{enable}}}
  if pw(8)==960 then old,new=new,old end
  for i=1,#new do
   local addr={0x2000+pos}+i-1
   assert(rd(addr)==old[i])
   emu.write(addr,new[i],emu.memType.snesWorkRam)
  end
 end"""
                return once(s,mark,mark+hook)
            kwargs['adapt_template']=template
        else:
            client=WORK/'client02'
            kwargs.update(client=client,client_hash=replay.dense.sha(client/'sink165.sfc'))
        return original(*args,**kwargs)
    with patch.object(module,'main',changes):
        replay.run(temp,phase,BASE,'886-only959' if local else '886-static',scene)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('scene',choices=('opening','transition','dense'))
    p.add_argument('--local',action='store_true')
    run(**vars(p.parse_args()))
