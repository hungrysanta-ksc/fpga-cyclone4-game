# SPDX-License-Identifier: MIT
"""Force multiple tile continuation calls and STOP inside map preparation."""
import inspect
import check_nes_resume330 as base
from nes_delta231 import once

def main():
    s=inspect.getsource(base.main)
    s=once(s,"assert arm.call('service296',[]) and arm.call('tiles290',[0])", "assert arm.call('service296',[])")
    s=once(s,"        actual=bytes(arm.uc.mem_read", """        pauses=[]
        while word('at290')<word('output_size285'):
            old_at=word('at290');assert arm.call('tiles290',[0])
            assert word('at290')>old_at
            pauses.append(word('left330'))
        if f in (905,906):assert len(pauses)>1 and any(pauses)
        guards.append([f,'bounded tile continuation',pauses])
        actual=bytes(arm.uc.mem_read""")
    s=once(s,"put('map_issued327',1);slices=0", """put('map_issued327',1);slices=1
        assert arm.call('prepare_map330',[]) and word('map_state330')==1
        partial=save();arm.call('stop286',[])
        assert word('map_state330')==0 and word('left330')==0
        scratch=bytes(arm.uc.mem_read(arm.symbols['metadata317'],209))
        assert arm.call('prepare_map330',[])
        assert bytes(arm.uc.mem_read(arm.symbols['metadata317'],209))==scratch
        assert not arm.call('tiles290',[1]) and not arm.call('commit285',[])
        guards.append([f,'partial map STOP freezes scratch and rejects commit']);restore(partial)""")
    ns=dict(base.__dict__);ns.update(__file__=__file__,__doc__=__doc__)
    exec(compile(s,'pause330','exec'),ns);ns['main']()

if __name__=='__main__':main()
