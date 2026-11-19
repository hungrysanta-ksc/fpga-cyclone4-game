"""Capture a no-input sample inside the 35–40 s source window and build both boards' common workload."""
import argparse
import json
import struct
from pathlib import Path
from unittest.mock import patch

import geometry_nes_848 as geometry
from capture_nes_mask820 import capture
from check_nes_input848 import run as verify_sender
from corpus_nes_848 import index
from nes_raw506 import once, sha
from prepare_nes_tile821 import prepare
from prepare_nes_trial802 import PROBES
from replay_nes_mask820 import simulate
from test_nes_mirror822 import test as verify_cache
from check_nes_game478 import Machine
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1


SOURCE = list(range(2120, 2365, 4))

def seed_slots(cpu, keys):
    """Retain ROM tag identities only. Neither bank claims a single preloaded VRAM byte."""
    fields=cpu.layout['nes_resident211']
    pc=cpu.syms['nes_resident211_begin']&~1
    def inject(u, address, size, _):
        s=u.reg_read(UC_ARM_REG_R0)
        assert not any(u.mem_read(s+fields['resident'],288))
        assert not any(u.mem_read(s+fields['serial'],4))
        u.mem_write(s+fields['epoch'],struct.pack('<I',u.reg_read(UC_ARM_REG_R1)))
        u.mem_write(s+fields['bg_slots'],struct.pack('<H',len(keys)+1))
        u.mem_write(s+fields['bg']+2,struct.pack('<'+'H'*len(keys),*keys))
        u.hook_del(handle)
    handle=cpu.u.hook_add(UC_HOOK_CODE,inject,begin=pc,end=pc)


def high_fixture(work, rom):
    original=work/'fixture/demo'
    def plans(d):
        return [bytes.fromhex(q) for g in range(905,967)
                for _,q in json.loads((d/f'frame{g}/plans.json').read_bytes())]
    old=plans(original)
    used={int.from_bytes(q[4:6],'little') for q in old if q[6]==0}
    # All tags address real tiles in the 128 KiB CHR. The chosen count depends
    # only on workload support, before inspecting any high-slot timings.
    keys=sorted(set(range(8192))-used,reverse=True)[:439]
    (work/'high-keys.json').write_text(json.dumps(keys))
    init=Machine.__init__
    def seeded(cpu,*args):
        init(cpu,*args)
        seed_slots(cpu,keys)
    with patch.object(Machine,'__init__',seeded):
        prepare(work/'rtl',work/'split',rom,PROBES/'nes-output823/link-826/src',work/'high',[('demo',SOURCE)])
    new=plans(work/'high/demo')
    for a,b in zip(old,new,strict=True):
        assert a[:2]==b[:2] and a[4:]==b[4:]
        shift=len(keys) if a[6]==0 else 0
        assert int.from_bytes(b[2:4],'little')==int.from_bytes(a[2:4],'little')+shift
    for g in range(905,967):
        for ext in ('geometry','raw'):
            assert (original/f'frame{g}.{ext}').read_bytes()==(work/'high/demo'/f'frame{g}.{ext}').read_bytes()


def run(temp, rom, stage):
    work = temp / 'nes-ack861'
    cap, split, rtl = (work / name for name in ('capture', 'split', 'rtl'))
    board = temp / 'nes-trial816-board860'
    if stage == 'capture':
        capture(rom, temp/'nes-bonus698-mesen/Mesen.exe', cap, SOURCE)
    elif stage == 'prepare':
        index(cap, split, work/'index.json', {'demo': SOURCE})
        with patch.object(geometry, 'ids', lambda: SOURCE):
            geometry.prepare(split, rtl)
        assert json.loads((rtl/'index.json').read_bytes())['translated'] == SOURCE
    elif stage=='high':
        high_fixture(work,rom)
    else:
        def bench(s):
            s = once(s, 'for(t=7*341+257;', 'for(t=0;')
            s = once(s, 'integer first,last,f,t,', 'integer sample_id,first,last,f,t,')
            return once(s, 'for(f=first;f<=last;f++)begin',
                        'for(sample_id=first;sample_id<=last;sample_id++)begin f=2120+4*sample_id;')
        simulate(board, rtl, [(i, min(i+11, len(SOURCE)-1)) for i in range(0,len(SOURCE),12)], adapt=bench)
        data = work/'fixture'
        arm = PROBES/'nes-output823/link-826/src'
        prepare(rtl, split, rom, arm, data, [('demo', SOURCE)])
        # Cache harness selects the held 822 implementation. Compare both files to the fitted board.
        for filename in ('nes_chr_cache611.sv','nes_obj_capture611.sv'):
            assert sha(temp/'nes-trial816-board822held'/filename) == sha(board/filename)
        verify_cache(temp, data, data, rom, held=True, inputs=[(data, split, rtl)], out=work/'hits-demo')
        verify_sender(board, data/'demo', arm, work/'sender-demo')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('capture','prepare','board','high'))
    parser.add_argument('temp', type=Path)
    parser.add_argument('rom', type=Path)
    run(**vars(parser.parse_args()))
