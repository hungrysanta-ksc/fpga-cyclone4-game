"""Compare the same workload and capture-to-display schedule on MMC872 and the word-fill client."""
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from analyze_nes_transition850 import STRIDE
from check_nes_strip869 import digest, metrics


def stages(folder, g, trace, wire):
    rows = [e for e in trace if e['g'] == g]
    starts = {e['index']:e for e in rows if e['event'] == 'load'}
    acks = {e['index']:e for e in rows if e['event'] == 'ack'}
    def point(e):
        return [e['clock'], e['frame'], e['line']]
    def at(event):
        return point(next(e for e in rows if e['event'] == event))
    maps = [i for i in starts if starts[i]['section'] == 2]
    fills = {}
    for i in maps:
        b = wire[i-1]
        if b[:2] == bytes((4,2)) and b[12:16] == bytes((2,0,192,0)) and b[16:] == bytes.fromhex('b821'):
            fills[int.from_bytes(b[10:12], 'little')] = acks[i]['clock'] - starts[i]['clock']
    p = [json.loads(line) for line in (folder/'producer.jsonl').read_text().splitlines()]
    last = max((e for e in p if e['generation']==g), key=lambda e:e['producer'], default=None)
    dma = defaultdict(list)
    for e in rows:
        if e['event']=='ppu_dma':
            dma[e['frame']].append([e['line'],e['value']])
    with (folder/'seal528.csv').open() as f:
        marks = {row['event']:[int(row[k]) for k in ('clock','line','h')]
                 for row in csv.DictReader(f) if row['event'] in ('final_credit','latch') and int(row['g'])==g}
    seal = next(i for i in starts if starts[i]['op']==3)
    tile = [i for i in starts if starts[i]['op']==7]
    return dict(last_tile_ready_and_E8=None if last is None else [last['producer'], round(last['observed'])],
                last_tile_return=point(acks[tile[-1]]) if tile else None,
                last_map_return=point(acks[maps[-1]]) if maps else None, word_service_clocks=fills,
                seal=point(starts[seal]), upload=at('upload165_entry'),
                final_check=marks['final_credit'], latch=marks.get('latch'), dma_line_bytes_by_VBlank=dma,
                reveal=at('reveal'), final_ACK=point(acks[seal]))


def physical(budget):
    rows = dict(line.split('=',1) for line in budget.read_text().splitlines() if '=' in line)
    data = dict(zip(rows['columns'].split(','), (int(x,16) for x in rows['b07'].split(',')), strict=True))
    return dict(sha256=digest(budget), frames=data['frames'], seal_ms_per_frame=10*data['seal']/data['frames'],
                per_frame={k:data[k]/data['frames'] for k in ('bg','obj','mapdirty','e1','e0','e8')})


def scene(temp, clip, phase):
    base = f'nes-tile821-{clip}-jointmirror-p{phase}-'
    paths = [temp/(base+tag) for tag in ('866-on','872-final','873-word')]
    reference = load(paths[0]/'joint.json')
    firmware = load(paths[1]/'joint.json')['firmware_SHA256']
    result = {}
    for path in paths:
        run = load(path/'joint.json')
        if path != paths[0]:
            assert run['firmware_SHA256'] == firmware
        assert run['parameters']==reference['parameters']
        row = metrics(path)
        assert row['pictures']==len(reference['frames'])
        for frame in reference['frames']:
            g = frame['generation']
            rgb = f'frame-{g}.rgb'
            actual = (path/rgb).read_bytes()
            expected = (paths[0]/rgb).read_bytes()
            assert len(actual)==len(expected) and actual[7*STRIDE:231*STRIDE]==expected[7*STRIDE:231*STRIDE], (path,g)
            assert (path/f'map-{g}.bin').read_bytes()==(paths[0]/f'map-{g}.bin').read_bytes()
        trace = window(path)
        reveals = [e for e in trace if e['event']=='reveal']
        row['gaps'] = {b['g']:b['frame']-a['frame'] for a,b in zip(reveals[1:],reveals[2:])}
        if clip=='demo':
            loads = load(path/'ack861.json')['loads']
            assert loads == load(paths[0]/'ack861.json')['loads']
            row['g950_BG_OBJ_dirtyrows']=loads[950-reveals[0]['g']]
            wire = packets(path)
            row['alternating_map_words'] = [int.from_bytes(b[8:10],'little') for b in wire
                                            if b[:2]==bytes((4,2)) and b[16]!=b[17]
                                            and int.from_bytes(b[8:10],'little')>906]
            row['stages'] = {g:stages(path,g,trace,wire) for g in (940,947,950)}
        result[path.name.removeprefix(base)] = row
    return result


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('temp','work','downloads','out'):
        parser.add_argument(key,type=Path)
    a = parser.parse_args()
    results = {f'{clip}-{ph}':scene(a.temp,clip,ph) for clip in ('demo','opening','transition') for ph in (1,2)}
    gates={}
    for key, variants in results.items():
        old,new=variants['872-final'],variants['873-word']
        dense = key.startswith('demo-')
        gates[key] = dict(intervals=(new['after_two_VBlanks']<old['after_two_VBlanks'] if dense else
                                     new['after_two_VBlanks']<=old['after_two_VBlanks']))
        if dense:
            gates[key].update(ACK=new['last_ACK']<old['last_ACK'],map_wire=new['warm_map_wire_B']==old['warm_map_wire_B'],
                              g936=new['gaps'][936]<=2)
        if key.startswith('opening-'):
            gates[key]['opening_deadlines']=all(new['opening_marks'][i]<=old['opening_marks'][i] for i in ('910','966'))
    fw=a.work/'link-credit/src/obj-nes-100/firmware.stm'
    out=dict(source='Adventure Island IV; replay master clocks, not board FPS. Stage points are [clock,VBlank,line], final_check is [clock,line,h].',
             physical_b07={n:physical(a.downloads/f'nes-budget-mmc{n}.txt') for n in (866,872)},
             ROM=digest(a.work/'client02/sink165.sfc'),ROM_free_B=load(a.work/'client02/build.json')['physical_free_B'],
             ARM=digest(fw),ARM_B=fw.stat().st_size,results=results,gates=gates,
             selected=all(all(v.values()) for v in gates.values()),
             boot=load(a.temp/'nes-word873-boot/result.json'), guards=load(a.work/'guards.json'),
             word_cancel=load(a.work/'word-guards.json'),menu=load(a.work/'menu869.json')['rows']['normal']['released'])
    assert out['menu'] and out['ARM']==load(a.work/'menu869.json')['firmware']
    assert out['ROM']==out['guards']['client'] and any(
        row['ROM']==out['ROM'] and row['kind']=='restored' for row in out['boot']['cases'])
    out['offline_section5']={}
    for tag,suffix in (('872-final','-872-final'),('873-word','')):
        for ph in (1,2):
            key=f'{tag}-p{ph}'
            pair=[load(a.temp/f'nes-word873-idle-p{ph}-{delay}{suffix}/summary.json') for delay in (0,1)]
            live=results[f'demo-{ph}'][tag]['stages'][950]
            assert pair[0]['ACK']==live['final_ACK'][0] and pair[0]['show'][2]==live['reveal'][0]
            assert pair[0]['previous']==pair[1]['previous']
            out['offline_section5'][key]=dict(control=pair[0],delayed=pair[1])
    a.out.write_text(json.dumps(out,indent=2)+'\n')
