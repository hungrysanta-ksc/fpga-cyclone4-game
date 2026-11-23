"""Lend an existing queue credit to the immutable section-5 prefix before checking E8."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_raw506 import once
from nes_window924 import replay
from prepare_nes_trial925 import ROOT, WORK as ORIGINAL
from replay_nes_supply905 import joint, UC_HOOK_CODE, UC_ARM_REG_R1, UC_ARM_REG_R2, UC_ARM_REG_R3
from unicorn.arm_const import UC_ARM_REG_SP

WORK = ORIGINAL.parent / 'nes-section929'
LAST = ORIGINAL.parent / 'nes-section929-last'


def observe(temp, phase, cache, control):
    """Take a read-only snapshot at packet_wire, before its tile arbiter runs."""
    init = joint.Runtime.__init__
    marks = []

    def attach(cpu, args, link):
        init(cpu, args, link)
        def watch(u, pc, size, user):
            if cpu.generation != 912 or u.reg_read(UC_ARM_REG_R2) != 5:
                return
            sp = u.reg_read(UC_ARM_REG_SP)
            data = int.from_bytes(u.mem_read(sp,4),'little')
            length = int.from_bytes(u.mem_read(sp+4,4),'little')
            if length != 201:
                return
            last = next(e for e in reversed(cpu.events) if e.get('opcode')=='0xe0')
            reply = bytes.fromhex(last['reply'])
            extra = sum(1 for e in cpu.events if e.get('opcode')=='0xe1' and e['clock']>last['clock'])
            used = (int.from_bytes(reply[3:5],'big')-int.from_bytes(reply[5:7],'big')+extra)&65535
            assert used<=4
            marks.append(dict(clock=round(cpu.clock), offset=u.reg_read(UC_ARM_REG_R3),
                              selector=u.reg_read(UC_ARM_REG_R1), outstanding=used,
                              last_checked_E0=round(last['clock']),
                              joined_sha256=hashlib.sha256(bytes(u.mem_read(data,441))).hexdigest()))
        addr = cpu.syms['packet_wire']
        cpu.u.hook_add(UC_HOOK_CODE, watch, begin=addr, end=addr)

    tag = '929mark' + ('base' if control else 'prefix')
    with patch.object(joint.Runtime,'__init__',attach):
        replay(temp, 'objheader', phase, cache=='cold', arm=ORIGINAL if control else WORK,
               edition=925, tag=tag)
    assert len(marks)==1
    out=temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{cache}-pair'
    (out/'prefix929.json').write_text(json.dumps(marks[0])+'\n')


def prepare(last_credit):
    package = json.loads((ROOT/'analysis/trial925-package.json').read_bytes())
    firmware = ORIGINAL/'link/src/obj-nes-100/firmware.stm'
    assert hashlib.sha256(firmware.read_bytes()).hexdigest() == package['firmware']
    link = (LAST if last_credit else WORK)/'link'
    shutil.copytree(ORIGINAL/'link', link)
    src = link/'src/nes_native_sink165.c'
    old = '  if(!packet(s,2,5,offset,joined,201))return false;'
    # The <=2 bound leaves a further physical queue slot for the producer.
    # Limit the outstanding receipt's age as well, even if the consumer has
    # freed ordinary credits. The next head and SEAL both service the plan.
    new = '''  struct nes_plan200 *plan=s->plan;
  unsigned selector=2;
  if(plan && plan->window &&
     (uint16_t)(plan->window->sent-plan->window->retired)<=2 &&
     (!plan->bulk_pending || (uint16_t)(plan->window->sent-plan->bulk_until)<3))
   selector=24;
  if(!packet(s,selector,5,offset,joined,201))return false;'''
    if last_credit:
        # Use the last already-checked ordinary credit. through() still
        # enforces the four-head receipt horizon before reusing a tile bank.
        new = once(new, '->retired)<=2', '->retired)<=3')
    src.write_text(once(src.read_text(), old, new), newline='\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    sub.add_parser('prepare').add_argument('--last-credit',action='store_true')
    run = sub.add_parser('replay')
    run.add_argument('temp', type=Path)
    run.add_argument('phase', type=int, choices=(1,2))
    run.add_argument('cache', choices=('warm','cold'))
    policy=run.add_mutually_exclusive_group()
    policy.add_argument('--observe',choices=('base','prefix'))
    policy.add_argument('--last-credit',action='store_true')
    args = parser.parse_args()
    if args.action == 'prepare':
        prepare(args.last_credit)
    elif args.observe:
        observe(args.temp,args.phase,args.cache,args.observe=='base')
    else:
        replay(args.temp, 'objheader', args.phase, args.cache=='cold',
               arm=LAST if args.last_credit else WORK, edition=925,
               tag='929last' if args.last_credit else '929prefix')
