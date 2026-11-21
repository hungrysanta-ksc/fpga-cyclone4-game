"""Trace bank publication and display accounting on the coupled 886/888 boots."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from prepare_nes_history888 import BASE, WORK
from check_nes_game478 import ELFFile
from replay_nes_coverage886 import replay, run as baseline
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_LR


def routine(work):
    obj = work/'link-credit/src/obj-nes-100'
    with (obj/'sd2snes.elf').open('rb') as f:
        syms = ELFFile(f).get_section_by_name('.symtab')
        s, = syms.get_symbol_by_name('nes_resident211_commit')
        abort, = syms.get_symbol_by_name('nes_resident211_abort')
        addr = s['st_value'] & ~1
        offset = addr-0x0800c000
        return (addr,abort['st_value']), (obj/'firmware.stm').read_bytes()[offset:offset+s['st_size']]


def run(temp, phase, scene, reference, local=False):
    runtime = replay.dense.joint.Runtime
    init = runtime.__init__
    observations = []
    generation = {'dense':945,'opening':916}.get(scene)
    if local:
        assert generation and not reference
        addresses, old = routine(BASE)
        linked, new = routine(WORK)
        assert addresses == linked and len(new) <= len(old)
        new += old[len(new):]
    def attach(cpu,args,link):
        init(cpu,args,link)
        if local:
            def swap(u,pc,size,ctx):
                if cpu.generation in (generation-1,generation):
                    before,after = (old,new) if cpu.generation==generation-1 else (new,old)
                    at=addresses[0]
                    assert bytes(u.mem_read(at,len(before)))==before
                    u.mem_write(at,after)
                    u.ctl_remove_cache(at,at+len(after))
            mark=cpu.syms['nes_budget210_display']
            cpu.u.hook_add(UC_HOOK_CODE,swap,begin=mark,end=mark)
        active = {}
        returns = set()
        def sample(name):
            observations.append([name,cpu.clock,cpu.instructions])
        def leave(u,pc,size,_):
            if pc in active:
                sample(active.pop(pc)+'_end')
        def enter(u,pc,size,name):
            if cpu.generation != generation:
                return
            ret = u.reg_read(UC_ARM_REG_LR) & ~1
            assert ret not in active
            active[ret] = name
            if ret not in returns:
                u.hook_add(UC_HOOK_CODE,leave,begin=ret,end=ret)
                returns.add(ret)
            sample(name)
        if generation:
            for name in ('nes_resident211_commit','commit635','nes_budget210_display','nes_plan200_retire'):
                pc = cpu.syms[name]
                cpu.u.hook_add(UC_HOOK_CODE,enter,name,begin=pc,end=pc)
    tag = '888-local' if local else '888-reference' if reference else '888-word'
    with patch.object(runtime,'__init__',attach):
        if reference or local:
            original = replay.run
            def renamed(t,ph,work,oldtag,clip):
                assert oldtag == '886-static'
                return original(t,ph,work,tag,clip)
            with patch.object(replay,'run',renamed):
                baseline(temp,phase,scene,False)
        else:
            replay.run(temp,phase,WORK,tag,scene)
    clip = 'demo' if scene=='dense' else scene
    (temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}/profile888.json').write_text(json.dumps(observations))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('scene',choices=('dense','opening','transition'))
    p.add_argument('--reference',action='store_true')
    p.add_argument('--local',action='store_true')
    run(**vars(p.parse_args()))
