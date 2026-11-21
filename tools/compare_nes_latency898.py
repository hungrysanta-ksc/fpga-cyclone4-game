"""Build matched Adventure Island IV source clips and replay two released ARM/client pairs."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

import geometry_nes_848 as geometry
from capture_nes_mask820 import capture
from check_nes_input848 import run as check_sender
from check_nes_game478 import Machine
from prepare_nes_ack861 import seed_slots
from corpus_nes_848 import index
from nes_raw506 import once, sha
from prepare_nes_tile821 import prepare
from prepare_nes_trial802 import PROBES
from replay_nes_mask820 import simulate
from replay_nes_output852 import joint, monitor, main, MirrorLink, gates
from replay_nes_strip869 import map_samples
from test_nes_mirror822 import test as check_cache
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R1

CLIPS = {'early': list(range(1950, 1979, 4)), 'late': list(range(3450, 3479, 4))}
FRAMES = sum(CLIPS.values(), [])
IMAGES = {872: ('nes-trial872/link-credit', 'nes-trial872/client02'),
          897: ('nes-sram897/link', 'nes-trial890/client02')}


def board(temp, work, rom):
    rtl = work/'rtl'
    board_src = temp/'nes-trial816-board872'
    def testbench(s):
        s = once(s, 'for(t=7*341+257;', 'for(t=0;')
        s = once(s, 'integer first,last,f,t,', 'integer sample_id,first,last,f,t,')
        return once(s, 'for(f=first;f<=last;f++)begin',
                    'for(sample_id=first;sample_id<=last;sample_id++)begin '
                    'f=sample_id<8 ? 1950+4*sample_id : 3450+4*(sample_id-8);')
    simulate(board_src, rtl, [(0,7),(8,15)], adapt=testbench)
    arm = PROBES/'nes-output823/link-826/src'
    prepare(rtl, work/'split', rom, arm, work/'fixture', list(CLIPS.items()))
    check_cache(temp, work/'fixture', work/'fixture', rom, held=True,
                inputs=[(work/'fixture', work/'split', rtl)], out=work/'hits')
    for name in CLIPS:
        check_sender(board_src, work/'fixture'/name, arm, work/('sender-'+name))


def replay(temp, work, edition, clip, phase, *, candidate_arm=None, replay_tag=None):
    arm_dir, client_dir = IMAGES[edition]
    arm, client = PROBES/arm_dir/'src', PROBES/client_dir
    results = PROBES.parent/'repository-nes-milestone/analysis'
    manifest = json.loads((results/f'trial{edition}-package.json').read_bytes())
    assert sha(arm/'obj-nes-100/firmware.stm') == manifest['ARM']
    assert sha(client/'sink165.sfc') == manifest['client']
    if candidate_arm is not None:
        assert replay_tag
        arm=candidate_arm
    source = json.loads((work/('sender-'+clip)/'sender.json').read_bytes())
    loads = []
    original = joint.Runtime.__init__
    def init(cpu, args, link):
        original(cpu, args, link)
        seed_slots(cpu, json.loads((work/f'{clip}-slots.json').read_bytes()))
        def display(u, pc, size, _):
            video = u.reg_read(UC_ARM_REG_R1)
            def field(k, n):
                return int.from_bytes(u.mem_read(video+cpu.layout['nes_native_video165'][k],n),'little')
            loads.append([field('bg_count',2),field('obj_count',2),field('map_dirty',8).bit_count()])
        at = cpu.syms['nes_budget210_display'] & ~1
        cpu.u.hook_add(UC_HOOK_CODE, display, begin=at, end=at)
    def adapt(s):
        return map_samples(once(monitor(s, 'demo'), 'local n=pb(0)==2 and pw(12) or pw(14)',
                               'local n=pb(0)==9 and 1472 or pb(0)==2 and pw(12) or pw(14)'))
    tag = replay_tag or f'898-{edition}'
    # Same wire calibration, start offsets, ROM calendar and initial state on both sides.
    argv = ['replay','','','','','',tag,str(Path.home()/'Downloads/nes-budget-mmc872.txt')]
    with patch.object(sys,'argv',argv), patch.object(MirrorLink,'lookup_file',work/'hits/hits.json'), \
            patch.object(joint.Runtime,'__init__',init), gates(source,True):
        main(work/f'{clip}-high',clip,'jointmirror',phase,temp,arm=arm,client=client,
             client_hash=manifest['client'],link_class=MirrorLink,packet_source=source,adapt_template=adapt)
    assert len(loads) == len(CLIPS[clip])
    (temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}'/'loads898.json').write_text(json.dumps(loads))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=('capture','geometry','board','history','replay'))
    p.add_argument('temp', type=Path)
    p.add_argument('rom', type=Path)
    p.add_argument('--edition', type=int, choices=IMAGES)
    p.add_argument('--clip', choices=CLIPS)
    p.add_argument('--phase', type=int, choices=(1,2))
    a = p.parse_args()
    work = a.temp/'nes-latency898'
    if a.action == 'capture':
        capture(a.rom, a.temp/'nes-bonus698-mesen/Mesen.exe', work/'capture', FRAMES)
    elif a.action == 'geometry':
        index(work/'capture', work/'split', work/'index.json', CLIPS)
        with patch.object(geometry, 'ids', lambda: FRAMES):
            geometry.prepare(work/'split', work/'rtl')
        assert json.loads((work/'rtl/index.json').read_bytes())['translated'] == FRAMES
    elif a.action == 'board':
        board(a.temp, work, a.rom)
    elif a.action == 'history':
        # Populate only unused tag identities, never VRAM validity or received rows.
        # Match the rounded physical BG slot level without tuning any timing result.
        for clip, workload in [('early',502),('late',526)]:
            ref = work/'fixture'/clip
            def plans(folder):
                return [bytes.fromhex(h) for g in range(905,913)
                        for _,h in json.loads((folder/f'frame{g}/plans.json').read_bytes())]
            old = plans(ref)
            bg = [q for q in old if q[6] == 0]
            count = workload - 1 - max(int.from_bytes(q[2:4],'little') for q in bg)
            used = {int.from_bytes(q[4:6],'little') for q in bg}
            keys = sorted(set(range(8192))-used,reverse=True)[:count]
            assert len(keys)==count and 0<count<512
            (work/f'{clip}-slots.json').write_text(json.dumps(keys))
            init = Machine.__init__
            def seeded(cpu,*args):
                init(cpu,*args)
                seed_slots(cpu,keys)
            dest = work/f'{clip}-high'
            with patch.object(Machine,'__init__',seeded):
                prepare(work/'rtl', work/'split', a.rom, PROBES/'nes-output823/link-826/src',
                        dest, [(clip,CLIPS[clip])])
            for x,y in zip(old,plans(dest/clip),strict=True):
                assert x[:2]==y[:2] and x[4:]==y[4:]
                assert int.from_bytes(y[2:4],'little')-int.from_bytes(x[2:4],'little')==(count if x[6]==0 else 0)
    else:
        replay(a.temp, work, a.edition, a.clip, a.phase)
