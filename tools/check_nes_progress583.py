# SPDX-License-Identifier: MIT
"""Reference response guards; not hardware execution or arbitrary RAM fault proof."""
import argparse
import copy
import json
from pathlib import Path
from nes_progress583 import Receiver, snapshot
from nes_abi582 import crc, sha


def run():
    ack = bytes([0, 2, 0, 1, 0, 0, 0, 0, 0, 0, 0x65, 0x9a])
    r = Receiver(sent=1, plan_sent=1, expected_ack={1: ack})
    # New command's acceptance is not fabricated from its pre-command snapshot.
    assert r.observe(snapshot()) and r.accepted == r.retired == 0
    assert r.observe(snapshot(sequence=2, accepted=1, plan=1)) and r.retired == 0
    assert r.observe(snapshot(sequence=3, accepted=1, retired=1, plan=1, flags=1, ack=ack))
    assert not r.observe(r.previous)
    negatives = []
    def reject(name, obj, b):
        before = copy.deepcopy(obj)
        try: obj.observe(b)
        except AssertionError: pass
        else: raise AssertionError(name)
        assert obj == before, name
        negatives.append(name)
    base = dict(sequence=4, accepted=1, retired=1, plan=1, flags=1, ack=ack)
    for name, kw in [('epoch',dict(epoch=2)), ('serial',dict(serial=2)),
                     ('generation',dict(generation=906)), ('reserved',dict(reserved=1)),
                     ('fault',dict(flags=17)), ('cancel',dict(flags=33)),
                     ('accepted_future',dict(accepted=2)), ('retired_future',dict(retired=2)),
                     ('retired_backwards',dict(retired=0)), ('plan_future',dict(plan=2)),
                     ('wrong_ack',dict(ack=bytes(12))), ('snapshot_backwards',dict(sequence=2))]:
        reject(name, copy.deepcopy(r), snapshot(**(base | kw)))
    b = bytearray(snapshot(**base)); b[8] ^= 1
    reject('CRC', copy.deepcopy(r), bytes(b))
    reject('short', copy.deepcopy(r), snapshot(**base)[:-1])
    reject('same_sequence_changed', copy.deepcopy(r), snapshot(**(base | dict(sequence=3, flags=5))))
    # Check missing completion ACK specifically at a retired transition.
    fresh = Receiver(sent=1)
    reject('missing_completion_identity', fresh, snapshot(accepted=1, retired=1))
    stopped = copy.deepcopy(r); stopped.stop()
    reject('late_completion_after_STOP', stopped, snapshot(**base))
    bulk = bytes([1,0,0,0,0,0,0,0,1,0,0,0])
    pending = Receiver(sent=1, accepted=1, bulk=bulk, bulk_until=1, expected_ack={1:ack})
    reject('END_before_bulk_consumed', pending, snapshot(accepted=1, flags=8))
    newer = bulk[:8] + (2).to_bytes(4,'little')
    reject('replace_unconsumed_bulk', pending, snapshot(accepted=1, flags=2, bulk=newer))
    reject('END_with_new_bulk', Receiver(), snapshot(flags=10, bulk=bulk))
    assert pending.observe(snapshot(accepted=1, retired=1, flags=9, ack=ack))
    wrapped = Receiver(sent=0, accepted=65535, retired=65535, plan_sent=0, plan=65535,
                       sequence=65535, expected_ack={0:ack})
    assert wrapped.observe(snapshot(sequence=0, accepted=0, retired=0, plan=0, flags=1, ack=ack))
    return dict(stage=583, passed=True, response_B=50, carrier_minimum_B=52,
        normal_conditions=['pre_command_not_current_acceptance','accepted_not_consumed','checked_consumption',
                           'identical_snapshot_idempotent','END_after_bulk_consumed','16bit_wrap'],
        rejection_conditions=negatives,
        scope='Python reference of coherent snapshot fields only; source FETCH, CDC/IRQ/physical STOP and full bulk semantics not executed',
        source_SHA256=sha(Path(__file__).with_name('nes_progress583.py')), checker_SHA256=sha(Path(__file__)))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__); p.add_argument('--out',type=Path,required=True)
    a = p.parse_args(); result = run()
    a.out.parent.mkdir(parents=True,exist_ok=True)
    assert not a.out.exists()
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))
