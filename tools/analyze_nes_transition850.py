"""Verify held pixels, independent source RGB and final display identity over the capture gap."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_input848 import CLOCK_MS, stats
from analyze_nes_map830 import packets, window
from check_nes_lease850 import offsets
from test_nes_raw506_joint import PERIOD


SOURCES = [*range(1525,1545), *range(1557,1587)]
RGB555 = bytes((x & 248) | (x >> 5) for x in range(256))
STRIDE = 256 * 3


def read(path):
    return json.loads(path.read_bytes())


def source_rgb(temp, f):
    path = temp / f'nes-contiguous848-split02/{f}/frame-{f}.rgb'
    return path.read_bytes()[8*STRIDE:232*STRIDE].translate(RGB555)


def measure(temp, edition, phase, missed, points, rtl):
    data = temp / f'nes-trans850-c{missed}'
    run = temp / f'nes-tile821-transition-jointmirror-p{phase}-850c{missed}-{edition}'
    work = read(data / 'transition/transition/work.json')
    verified = read(data / 'sender-transition/verified.json')['frames']
    gs = [row['g'] for row in work]
    assert [row['source_frame'] for row in work] == [v['source'] for v in verified] == SOURCES
    assert gs == [v['generation'] for v in verified]
    assert gs[19:21] == [924,937-missed]
    cpu = read(run / 'joint.json')
    assert cpu['passed'] and cpu['commits'] == 50 and cpu['last_status'] == 1
    events = read(run / 'events.json')
    gap, = [e for e in events if e['event'] == 'blank_interval']
    assert gap == read(run / 'blank-interval.json') and gap['source_frames'] == 12
    trial = temp / f'nes-tile821-transition-jointmirror-p{phase}-850c0-{edition}'
    assert gap == read(trial / 'blank-interval.json')
    spi = [e for e in events if e['event'] == 'SPI']
    returns = [e for e in spi if e['opcode'] == '0xea']
    commits = [e for e in spi if e['opcode'] == '0xd3']
    assert [e['generation'] for e in returns] == [e['input_generation'] for e in commits] == gs
    assert [f['generation'] for f in cpu['frames']] == gs
    assert all(f['ACK_masterclock'] <= ea['start'] for f,ea in zip(cpu['frames'],returns))
    assert all(ea['clock'] <= d3['start'] for ea,d3 in zip(returns,commits[1:]))
    wire = [p for p in packets(run) if p[0] == 1]
    assert [int.from_bytes(p[8:10],'little') for p in wire] == gs
    assert [int.from_bytes(p[4:8],'little') for p in wire] == list(range(1,51))
    assert all(p[18] == i % 2 for i,p in enumerate(wire))
    replies = {e['generation']: bytes.fromhex(e['reply']) for e in spi if e['opcode']=='0xe0'}
    for serial,g in enumerate(gs,1):
        ack = replies[g]
        assert ack[7:9] == bytes([1,3]) and int.from_bytes(ack[11:15],'little') == serial
        assert int.from_bytes(ack[15:17],'little') == g
    d1s = [e for e in spi if e['opcode'] == '0xd1']
    for g,v in zip(gs,verified):
        assert sum(e['bytes'] for e in d1s if e['input_generation']==g) == v['board_D1_B']
    resumed = [e for e in d1s if e['input_generation']==gs[20]][0]
    assert resumed['start'] >= gap['first_ready'] + 12*PERIOD
    assert {e['input_generation'] for e in d1s} == set(gs)
    reveals = [r for r in window(run) if r['event']=='reveal']
    assert [r['g'] for r in reveals] == gs
    pixel_mismatches = {}
    for f,g in zip(SOURCES,gs):
        actual = (run / f'frame-{g}.rgb').read_bytes()[7*STRIDE:231*STRIDE]
        expected = source_rgb(temp,f)
        assert len(expected) == len(actual) == 224*STRIDE
        if expected != actual:
            pixel_mismatches[f] = sum(actual[i:i+3] != expected[i:i+3] for i in range(0,len(actual),3))
    with (run / 'held.csv').open() as log:
        held = [tuple(map(int,row)) for row in csv.reader(log)]
    assert [r[0] for r in held] == list(range(reveals[19]['frame']+1,reveals[20]['frame']))
    assert all(bank == wire[19][18] and (lo,hi) == (20,0) for _,_,bank,lo,hi in held)
    old_pixels = (run / 'frame-924.rgb').read_bytes()
    assert all((run/f'held-{v}.rgb').read_bytes() == old_pixels for v,*_ in held)
    assert held[-1][1] >= resumed['start']
    elapsed = reveals[-1]['clock'] - reveals[1]['clock']
    intervals = [(b['clock']-a['clock'])/CLOCK_MS for a,b in zip(reveals[1:],reveals[2:])]
    ack_delay = [(e['clock']-f['ACK_masterclock'])/CLOCK_MS for e,f in zip(returns[2:],cpu['frames'][2:])]
    return dict(arm=cpu['firmware_SHA256'], snes=cpu['client_SHA256'], EA_offset_bounds=points,
                blank_captured=rtl['resume'][0], blank_missed=missed, resume_generation=gs[20],
                checked_display_ACKs=len(gs), held_VBlanks=len(held), measured_display_intervals=len(gs)-2,
                pixel_mismatches=pixel_mismatches, first_nonblack_after_resume=next(f for f in SOURCES[20:] if any(source_rgb(temp,f))),
                elapsed_VBlanks=reveals[-1]['frame']-reveals[1]['frame'], elapsed_ms=round(elapsed/CLOCK_MS,3),
                display_interval_ms=stats(intervals), ACK_to_EA_ms=stats(ack_delay),
                resume_display_interval=reveals[20]['frame']-reveals[19]['frame'],
                final_ACK=cpu['frames'][-1]['ACK_masterclock'], final_EA=round(returns[-1]['clock']),
                D1_B=sum(v['board_D1_B'] for v in verified))


def analyze(temp, lease):
    bounds = offsets(temp,'850c0')
    cases = read(lease/'result.json')
    results = {}
    for edition in (826,849):
        for phase in (1,2):
            k = f'{edition}-p{phase}'
            a,b = (cases[str(t)] for t in bounds[k])
            assert a['resume'] == b['resume'] and a['captures'] == b['captures']
            results[k] = measure(temp,edition,phase,a['resume'][2],bounds[k],a)
    assert all(not any(source_rgb(temp,f)) for f in range(1544,1563))
    delta = {}
    for phase in (1,2):
        a,b = (results[f'{edition}-p{phase}'] for edition in (826,849))
        assert a['snes'] == b['snes']
        delta[phase] = dict(VBlanks=b['elapsed_VBlanks']-a['elapsed_VBlanks'],
                            final_ACK_ms=round((b['final_ACK']-a['final_ACK'])/CLOCK_MS,3))
    fixed = temp/'nes-trans850-c0'
    canonical = read(fixed/'sender-transition/verified.json')
    legacy = read(temp/'nes-trans850/sender-transition/verified.json')
    assert canonical['rtl'] == legacy['rtl']
    assert [v['source'] for v in legacy['frames']] == SOURCES
    raw_sizes = {}
    for f,v in zip(SOURCES,canonical['frames']):
        name = 'frame%d.raw' % v['generation']
        old,new = ((temp/folder/'transition/transition'/name).stat().st_size
                   for folder in ('nes-trans850','nes-trans850-c0'))
        assert old-new == 256
        raw_sizes[f] = [old,new]
    geometry = dict(removed_raw_B_per_frame=256, raw_B_at_boundary={f:raw_sizes[f] for f in (1544,1557)},
                    old_D1_B=sum(v['board_D1_B'] for v in legacy['frames']),
                    corrected_D1_B=sum(v['board_D1_B'] for v in canonical['frames']),
                    sender_RTL=canonical['rtl'])
    return dict(sources=SOURCES,runs=results,delta=delta,geometry=geometry,
                clock_scope='linked ARM CPI2, emulated 65816, board sender/cache traces; scheduled EA replay on lease RTL')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('temp','lease','out'):
        p.add_argument(name,type=Path)
    a=p.parse_args()
    result=analyze(a.temp,a.lease)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
    assert all(not r['pixel_mismatches'] for r in result['runs'].values()), 'independent RGB mismatch'
