"""Replay linked ARM and 65816 combinations on the same corpus, with optional ACK timer or section-5 controls."""
import argparse
import json
import sys
from pathlib import Path
from unittest.mock import patch

from replay_nes_column853 import joint, MirrorLink, gates, main, monitor, sha
from prepare_nes_trial802 import PROBES
from prepare_nes_ack861 import seed_slots
from unicorn import UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_R0, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3, UC_ARM_REG_R4, UC_ARM_REG_XPSR


def replay(temp, edition, phase, quiet, only_generation=None, high=False, consumer=None, tail864=None, arm_override=None, tag_override=None):
    work = temp/'nes-ack861'
    arm = PROBES/f'nes-trial{edition}/link/src'
    if tail864:
        assert edition==855 and consumer is None and high and quiet==128 and only_generation is None
        arm=PROBES/'nes-tail864'/('control' if tail864=='control' else 'link')/'src'
    if consumer is not None and (not high or quiet!=128 or only_generation is not None):
        raise ValueError('crossed links require the complete high-slot reference replay')
    client = PROBES/('nes-column854/client-e' if (consumer or edition)==855 else 'nes-seal858/client-e')
    source = json.loads((work/'sender-demo/sender.json').read_bytes())
    tag = f'861-{edition}-{quiet}'
    if high:
        tag+='-high'
    if consumer is not None:
        tag+=f'-cpu{consumer}-864'
    if tail864:
        tag+='-tail864'
        if tail864=='control':tag+='-control'
    if arm_override is not None or tag_override is not None:
        if not (arm_override and tag_override and high and edition==855 and quiet==128
                and consumer is None and tail864 is None and only_generation is None):
            raise ValueError('custom ARM comparison requires a full MMC855 high-slot replay')
        arm=arm_override
        tag=tag_override
    if only_generation is not None:
        assert quiet == 256 and 907 <= only_generation <= 964
        tag += f'-g{only_generation}-bounded'
        source = {key:value for key,value in source.items() if int(key)<=only_generation+1}
    original = joint.Runtime.__init__
    output, reason, loads = [], [], []
    def attach(cpu, args, link):
        original(cpu, args, link)
        if high:
            seed_slots(cpu,json.loads((work/'high-keys.json').read_bytes()))
        def hook(pc, fn):
            cpu.u.hook_add(UC_HOOK_CODE, fn, begin=pc, end=pc)
        def phase_end(u, pc, size, _):
            if u.reg_read(UC_ARM_REG_R0) == 2:
                now = int(cpu.clock * joint.ARM_HZ / joint.MASTER)
                elapsed = (now-u.reg_read(UC_ARM_REG_R1)) & 0xffffffff
                output.append([cpu.clock-elapsed*joint.MASTER/joint.ARM_HZ, cpu.clock])
        def wait(u, pc, size, _):
            reason.append([cpu.generation,cpu.clock,u.reg_read(UC_ARM_REG_R2),u.reg_read(UC_ARM_REG_R3)])
        def workload(u, pc, size, _):
            v = u.reg_read(UC_ARM_REG_R1)
            fields = cpu.layout['nes_native_video165']
            def read(k,n):
                return int.from_bytes(u.mem_read(v+fields[k],n),'little')
            loads.append([read('bg_count',2),read('obj_count',2),read('map_dirty',8).bit_count()])
        hook(cpu.syms['nes_cost471_phase'] & ~1, phase_end)
        hook(cpu.syms['nes_budget210_display'] & ~1, workload)
        pause = cpu.syms['nes_cost474_pause'] & ~1
        hook(pause, wait)
        if quiet != 128:
            assert edition == 860
            # At BCC after CMP.W R3,#10752, R3 is elapsed DWT ticks and R4 holds the reason.
            # Change only the carry tested by BCC; actual guard loop, elapsed ticks and IRQs remain.
            branch = pause+0x62
            assert bytes(cpu.u.mem_read(branch-4,6)).hex() == 'b3f5285ff4d3'
            def compare(u, pc, size, _):
                if (only_generation is None or cpu.generation == only_generation) and u.reg_read(UC_ARM_REG_R4) == 2:
                    flags = u.reg_read(UC_ARM_REG_XPSR) & ~(1<<29)
                    u.reg_write(UC_ARM_REG_XPSR, flags | (int(u.reg_read(UC_ARM_REG_R3)>=84*quiet)<<29))
            hook(branch, compare)
    argv = ['replay','','','','','',tag,str(Path.home()/'Downloads/nes-budget-mmc855.txt')]
    joint_run = joint.run
    def execute(args):
        if only_generation is not None:
            # Keep one full follower so input overlap on the target remains enabled.
            args.generations = [g for g in args.generations if g<=only_generation+1]
            args.frames = len(args.generations)
            args.next_generation = dict(zip(args.generations,args.generations[1:]))
        joint_run(args)
    with patch.object(sys,'argv',argv), patch.object(MirrorLink,'lookup_file',work/'hits-demo/hits.json'), gates(source,True), patch.object(joint.Runtime,'__init__',attach), patch.object(joint,'run',execute):
        main(work/('high' if high else 'fixture'),'demo','jointmirror',phase,temp,arm=arm,client=client,
             client_hash=sha(client/'sink165.sfc'),link_class=MirrorLink,packet_source=source,
             adapt_template=lambda s: monitor(s,'demo').replace('local n=pb(0)==2 and pw(12) or pw(14)',
                    'local n=pb(0)==9 and 1472 or pb(0)==2 and pw(12) or pw(14)'))
    assert len(output)==len(loads)==(len(source) if only_generation is None else only_generation+2-905) and reason
    folder = temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}'
    (folder/'ack861.json').write_text(json.dumps(dict(output=output, waits=reason, loads=loads)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('edition',type=int,choices=(855,860))
    p.add_argument('phase',type=int,choices=(1,2))
    p.add_argument('quiet',type=int,choices=(128,256))
    p.add_argument('--only-generation',type=int)
    p.add_argument('--high',action='store_true')
    p.add_argument('--consumer',type=int,choices=(855,860))
    p.add_argument('--tail864',nargs='?',const='joined',choices=('joined','control'))
    replay(**vars(p.parse_args()))
