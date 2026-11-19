"""Exercise cancellation, WRAM validation and menu recovery on a linked 857 candidate."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from analyze_nes_column853 import verify_partial_stop
from guard_nes_output852 import arm_guard, run
from prepare_nes_trial802 import PROBES
from replay_nes_column853 import joint, run as replay
from unicorn.arm_const import UC_ARM_REG_LR, UC_ARM_REG_PC, UC_ARM_REG_R0, UC_ARM_REG_R1


def stop_before_successor(temp, arm, client):
    """Assert STOP while the raw successor qualifies but before it is sent."""
    state = {}
    original = joint.Runtime.hook
    tag = '857h-raw-stop'

    def hook(cpu, u, pc, size, ctx):
        if cpu.live and 'generation' not in state and pc == cpu.syms['nes_plan200_progress']:
            plan = u.reg_read(UC_ARM_REG_R0)
            fields = cpu.layout['nes_plan200']
            def read(name, width=1):
                return int.from_bytes(u.mem_read(plan+fields[name],width),'little')
            if u.reg_read(UC_ARM_REG_R1) == 0 and read('ending') and read('bulk_pending') and not read('finished'):
                win = read('window',4)
                layout = cpu.layout['nes_sink_window184']
                headers = bytes(u.mem_read(win+layout['last'],2))
                sent = int.from_bytes(u.mem_read(win+layout['sent'],2),'little')
                ahead = (sent-read('bulk_until',2)) & 0xffff
                if headers == bytes((4,5)) and ahead < 3:
                    state.update(generation=cpu.generation, distance=ahead, clock=cpu.clock)
        if cpu.live and 'generation' in state and pc == cpu.syms['nes_cf86_check094']:
            state['injected'] = True
            u.reg_write(UC_ARM_REG_R0,0)
            u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
            return
        return original(cpu,u,pc,size,ctx)

    with patch.object(joint.Runtime,'hook',hook):
        try:
            replay(temp,'demo',1,True,tag,arm=arm,client=client,
                   budget=Path.home()/'Downloads/nes-budget-mmc855.txt')
        except AssertionError as exc:
            fault = exc.args[0]
            assert state.get('injected') and fault[:3] == ('runtime fault',state['generation'],2), fault
        else:
            raise AssertionError('successor accepted after STOP')
    folder = temp/f'nes-tile821-demo-jointmirror-p1-{tag}'
    events = json.loads((folder/'events.json').read_bytes())
    assert not any(e.get('clock',-1)>state['clock'] and e.get('opcode') in ('0xe1','0xea','0xd3')
                   for e in events)
    return dict(**state, fault=fault, no_later_E1_EA_D3=True)


def check(temp, edition, case):
    probe = PROBES / 'nes-output857'
    arm = probe / f'link-{edition}/src'
    client = PROBES / 'nes-column854/client-e'
    tag = '857' + edition
    folder = temp / f'nes-tile821-demo-jointmirror-p1-{tag}-on'
    if case == 'raw-stop':
        assert edition == 'h'
        result = stop_before_successor(temp,arm,client)
    elif case == 'consumer':
        result = {name:run(temp, folder, name, column_client=client)
                  for name in ('damage', 'stop', 'late-stop')}
        result['partial'] = verify_partial_stop(folder)
        result['restart'] = run(temp, folder, 'restart', folder/'guard-stop/canceled.bin', client)
    else:
        def selected(temp, clip, phase, policy, name, dma):
            replay(temp, clip, phase, True, name, arm=arm, client=client,
                   budget=Path.home()/'Downloads/nes-budget-mmc855.txt')
        result = arm_guard(temp, case, selected, 'column_serial', tag)
    (probe / f'{edition}-{case}.json').write_text(json.dumps(result, indent=2)+'\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp', type=Path)
    parser.add_argument('edition', choices=('b', 'c', 'h'))
    parser.add_argument('case', choices=('consumer', 'stop', 'identity','raw-stop'))
    args = parser.parse_args()
    check(args.temp, args.edition, args.case)
