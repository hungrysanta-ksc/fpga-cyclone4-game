"""Reconcile output credit and next-input timing against a generation-local control."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from check_nes_packed883 import report
from check_nes_strip869 import digest


def trace(path):
    events = [e for e in load(path/'events.json') if e['event'] == 'SPI']
    writes = [e for e in events if e['opcode'] == '0xe1']
    payloads = packets(path)
    assert len(writes) == len(payloads)
    output = [(b, e) for b, e in zip(payloads, writes) if int.from_bytes(b[8:10], 'little') == 962]
    rows = window(path)
    obj = [r['clock'] for r in rows if r['g'] == 962 and r['event'] == 'ack' and r['op'] == 7 and r['section'] == 1]
    fin = [e for e in events if e['generation'] == 962 and e['opcode'] == '0xe8']
    table = [e for b,e in output if b[0:2] == bytes([2,5]) and len(b)-16 == 240]
    seal = [e for b,e in output if b[0] == 3]
    inputs = [e for e in events if e['opcode'] == '0xd1' and e['input_generation'] == 963]
    first = inputs[0]
    final = next(r['clock'] for r in rows if r['g'] == 962 and r['op'] == 3 and r['event'] == 'ack')
    ea = next(e for e in events if e['generation'] == 962 and e['opcode'] == '0xea')
    input_trace = [[e['bytes'],round(e['start']),round(e['clock'])] for e in inputs]
    reveal = next(r['clock'] for r in rows if r['g'] == 961 and r['event'] == 'reveal')
    source = next(e for e in load(path/'events.json') if e['event'] == 'source_begin' and e['generation'] == 963)
    observations = load(path/'credit962.json') if (path/'credit962.json').exists() else []
    return events, [b for b,_ in output], dict(
        reveal961=reveal, capture_ready963=round(source['capture_ready']), first_D1=round(first['start']),
        last_OBJ_ACK=max(obj,default=None), last_E8_end=round(fin[-1]['clock']),
        table240_starts=[round(e['start']) for e in table], SEAL_start=round(seal[-1]['start']),
        final962=final, EA962_end=round(ea['clock']), D1_trace=input_trace,
        D1_before_962_final=sum(e['clock']<final for e in inputs),
        D0=[r for r in observations if r['event']=='D0'],
        deferred=[r['clock'] for r in observations if r['event']=='deferred'])


def compare(temp, phase):
    prefix = f'nes-tile821-demo-jointmirror-p{phase}-'
    a, packets_a, active = trace(temp/(prefix+'884-room'))
    b, packets_b, control = trace(temp/(prefix+'884-late962'))
    baseline = trace(temp/(prefix+'883-shared'))[2]
    assert packets_a == packets_b and active['reveal961'] == control['reveal961']
    assert all(active[k] == control[k] for k in ('capture_ready963',))
    if control['deferred']:
        edge = control['deferred'][0]
        aa = [e for e in a if e['clock'] <= edge]
        bb = [e for e in b if e['clock'] <= edge]
        assert aa == bb and aa
    else:
        assert a == b
        aa = a
    return dict(shared=baseline, active=active, control=control, identical_prior_SPI=len(aa),
                first_D1_saved_clocks=control['first_D1']-active['first_D1'])


def audit(temp, phase, tag):
    path = temp/f'nes-mapwait880-consumer-{phase}-{tag}'/'idle-vram.csv'
    with path.open() as handle:
        return list(csv.reader(handle))


def reconcile(temp, work):
    candidate = {clip:report(temp,'884-room',clip) for clip in ('opening','transition','demo')}
    controls = report(temp,'884-late962','demo')
    firmware = work/'link-credit/src/obj-nes-100/firmware.stm'
    arm = digest(firmware)
    size = firmware.stat().st_size
    assert size <= 212992
    for row in [*controls, *(r for scene in candidate.values() for r in scene)]:
        assert row['ARM'] == arm
    contexts = []
    for phase, row in enumerate(candidate['demo'],1):
        contexts.append(compare(temp,phase))
        before = audit(temp,phase,'883-shared')
        after = audit(temp,phase,'884-room')
        row['map950'].update(idle_bytes=len(after), same_port_address_value=after==before)
        assert len(before) == 1536 and after == before
    guards = {k:load(work/(k+'.json')) for k in ('input-guards','retire-guards','menu','room-guards','guards')}
    assert arm == guards['input-guards']['firmware'] == guards['retire-guards']['ARM'] == guards['menu']['firmware']
    assert guards['menu']['rows']['normal']['released']
    assert guards['guards']['source_tag'] == '884-room' and guards['guards']['client'] == candidate['demo'][0]['client']
    return dict(candidate=candidate, same_link_962_control=controls, timing=contexts, guards=guards,
                ARM_SHA256=arm, flash_B=size, flash_free_B=212992-size)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','work','output'):
        parser.add_argument(key,type=Path)
    args=parser.parse_args()
    args.output.write_text(json.dumps(reconcile(args.temp,args.work),indent=2)+'\n',encoding='utf-8')
