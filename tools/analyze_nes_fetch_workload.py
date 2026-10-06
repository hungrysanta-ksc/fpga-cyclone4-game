# Causal immutable-CHR demand analysis. SPDX-License-Identifier: MIT.
from pathlib import Path
from collections import OrderedDict, Counter
import argparse, hashlib, json
from verify_nes_rtl_fetch import pixel_coordinate, PALETTE
from verify_nes_mmc3_integrated import verify, numbers

CANDIDATE = 'NES-R2-FETCH-WORKLOAD-019'

def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def events(rows, chrdata):
    output = []
    previous = -1
    for f, line, cycle, tick, virtual, physical, value, table in rows:
        assert tick > previous, 'non-monotonic or duplicate fetch tick'
        previous = tick
        offset = physical - 0x200000
        assert 0 <= offset < len(chrdata) and chrdata[offset] == value, 'CHR address/value'
        assert offset == table + virtual, 'physical bank mapping'
        line = -1 if line == 511 else line
        coord = pixel_coordinate(line, cycle - 1)
        output.append(dict(frame=f, line=line, dot=cycle-1, tick=tick,
                           offset=offset, tile=offset//16, value=value,
                           pixel=None if coord is None else list(coord)))
    return output

def demand(trace, capacity):
    assert capacity > 0
    cache = OrderedDict()
    misses = []
    hits = Counter()
    for index, e in enumerate(trace):
        key = e['tile']
        if key in cache:
            hits[e['frame']] += 1
            cache.move_to_end(key)
        else:
            evicted = cache.popitem(last=False)[0] if len(cache) == capacity else None
            cache[key] = None
            misses.append(dict(index=index, frame=e['frame'], line=e['line'],
                               tick=e['tick'], tile=key, evicted=evicted, bytes=16))
    return misses, hits

def max_window(misses, width):
    # Half-open rolling interval (right-width, right], in NES master ticks.
    left = 0
    best = dict(bytes=0, requests=0, first_tick=None, last_tick=None)
    for right, e in enumerate(misses):
        while misses[left]['tick'] <= e['tick'] - width:
            left += 1
        count = right-left+1
        if count > best['requests']:
            best = dict(bytes=count*16, requests=count,
                        first_tick=misses[left]['tick'], last_tick=e['tick'])
    return best

def describe(trace, capacity):
    misses, hits = demand(trace, capacity)
    frames = sorted({e['frame'] for e in trace})
    counts = Counter(m['frame'] for m in misses)
    lines = Counter((m['frame'], m['line']) for m in misses)
    return dict(capacity_tiles=capacity, capacity_bytes=capacity*16,
                initial_state='empty at capture start; history before capture is unknown',
                miss_requests=len(misses), fill_bytes=len(misses)*16,
                frames=[dict(frame=f, misses=counts[f], hits=hits[f],
                             fill_bytes=16*counts[f],
                             chr_dma_clocks_at_8_per_byte=128*counts[f]) for f in frames],
                max_line_fill_bytes=max(lines.values(), default=0)*16,
                rolling_windows_master_ticks={str(w):max_window(misses,w)
                                               for w in (32,1364,10912,357368)}), misses

def replay(trace, misses, chrdata, capacity):
    # An ideal zero-latency byte-integrity replay, not a transport scheduler.
    requests = {m['index']:m for m in misses}
    assert len(requests) == len(misses), 'duplicate request index'
    cache = OrderedDict()
    planes = {}
    output = {}
    for index,e in enumerate(trace):
        key = e['tile']
        if key not in cache:
            assert index in requests, 'missing tile request'
            m = requests[index]
            assert m['tick'] == e['tick'] and m['tile'] == key, 'noncausal/wrong request'
            evicted = cache.popitem(last=False)[0] if len(cache) == capacity else None
            assert m['evicted'] == evicted, 'eviction mismatch'
            cache[key] = chrdata[key*16:key*16+16]
        else:
            assert index not in requests, 'unexpected fill'
            cache.move_to_end(key)
        assert cache[key][e['offset']%16] == e['value'], 'replay byte mismatch'
        if e['pixel'] is None:
            continue
        y,x = e['pixel']
        plane = (e['offset']%16)//8
        pair = planes.setdefault((e['frame'],y,x), {})
        assert plane not in pair, 'duplicate pixel plane'
        pair[plane] = cache[key][e['offset']%16]
    assert all(0 <= i < len(trace) for i in requests), 'trailing request'
    for (f,y,x),p in planes.items():
        assert set(p) == {0,1}, 'missing pixel plane'
        pixels = output.setdefault(f, bytearray(256*240))
        for bit in range(8):
            pixels[y*256+x*8+bit] = PALETTE[((p[0]>>(7-bit))&1)|(((p[1]>>(7-bit))&1)<<1)]
    assert len(planes) == len(output)*240*32, 'incomplete frame'
    return {f:bytes(v) for f,v in output.items()}

def bank_declarations(control, frame_rows, trace):
    selected = None
    writes = []
    for row in control.read_text().splitlines():
        kind,tick,line,dot,address,value = row.split()
        tick,line,dot,address,value = map(int,(tick,line,dot,address,value))
        if kind != 'W':
            continue
        if address & 0xe001 == 0x8000:
            selected = value & 7
        elif address & 0xe001 == 0x8001 and selected in (0,1):
            writes.append(dict(register=selected, value=value, tick=tick, line=line, dot=dot))
    out = []
    for f,table,counter,start,*_ in frame_rows:
        first = next(e['tick'] for e in trace if e['frame'] == f)
        prior = []
        for reg in (0,1):
            matches = [w for w in writes if w['register']==reg and w['tick']<start]
            assert matches
            w = matches[-1]
            assert w['value'] == table//1024+reg*2
            prior.append(w)
        out.append(dict(frame=f, declared_bank_writes=prior,
                        all_four_kib_declared_tick=max(w['tick'] for w in prior),
                        ticks_from_both_bank_writes_to_first_fetch=first-max(w['tick'] for w in prior)))
    return out

def main():
    p=argparse.ArgumentParser()
    for name in ('run','reference','rom','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    assert not a.out.exists(), 'use a fresh output directory'
    audit=verify(a.run,a.reference,a.rom)
    assert audit['passed'], audit['errors']
    chrdata=bytes(int(v,16) for v in (a.run/'chr.hex').read_text().split())
    trace=events(numbers(a.run/'fetch.tsv'),chrdata)
    used=[e for e in trace if e['pixel'] is not None]
    frame_rows=numbers(a.run/'frames.tsv')
    # Never select preloads from the future trace. The observed union is descriptive only.
    frames=[]
    first_uses=[]
    for f,*_ in frame_rows:
        per=[e for e in trace if e['frame']==f]
        visible=[e for e in per if e['pixel'] is not None]
        seen=set()
        for e in per:
            if e['tile'] not in seen:
                first_uses.append(dict(frame=f,tile=e['tile'],tick=e['tick'],line=e['line'],dot=e['dot']))
                seen.add(e['tile'])
        frames.append(dict(frame=f,all_bg_fetches=len(per),pixel_referenced_fetches=len(visible),
                           unique_all_tiles=len(seen),unique_pixel_tiles=len({e['tile'] for e in visible}),
                           first_fetch_tick=per[0]['tick'],last_fetch_tick=per[-1]['tick']))
    policies={}
    all_misses={}
    for label,seq in (('all_bg',trace),('pixel_only_comparison',used)):
        policies[label]=[]
        for capacity in (128,256,512,1024):
            detail,misses=describe(seq,capacity)
            policies[label].append(detail)
            if label=='all_bg':
                all_misses[capacity]=misses
    a.out.mkdir(parents=True)
    replays=[]
    for capacity,misses in all_misses.items():
        decoded=replay(trace,misses,chrdata,capacity)
        for f,data in decoded.items():
            expected=bytes(int(v,16) for v in (a.run/f'frame-{f:3}.hex').read_text().split())
            assert data==expected, 'full240 replay pixels differ'
        replays.append(dict(capacity_tiles=capacity,pixels=sum(map(len,decoded.values())),
                            indexed_sha256={str(f):hashlib.sha256(b).hexdigest() for f,b in decoded.items()}))
        (a.out/f'misses-{capacity}.tsv').write_text(
            'index\tframe\tline\ttick\ttile\tevicted\tbytes\n'+
            ''.join('\t'.join(str(m[k]) for k in ('index','frame','line','tick','tile','evicted','bytes'))+'\n' for m in misses),
            encoding='utf-8')
    (a.out/'first-use.tsv').write_text('frame\ttile\ttick\tline\tdot\n'+
        ''.join('\t'.join(str(m[k]) for k in ('frame','tile','tick','line','dot'))+'\n' for m in first_uses),encoding='utf-8')
    result=dict(candidate=CANDIDATE,passed=True,frames=frames,
                scope='Four original zero-scroll Mapper4 BG-only frames, immutable CHR ROM; no rendered sprites, CHR RAM, game sample or hardware transport.',
                capture_start='Deliberately cold cache model at frame1, despite prior ROM initialization; no claim that game startup was captured.',
                observed_union_tiles=len({e['tile'] for e in trace}),
                observed_union_bytes=16*len({e['tile'] for e in trace}),
                whole_chr_rom_bytes=len(chrdata),
                causal_policy='Empty demand LRU keyed by physical 16-byte CHR tile; fill at current observed fetch, read immutable ROM tile; no future access ordering or preloads.',
                pixel_only_note='Removing unused fetches changes LRU history; this is not a guaranteed lower bound for a fixed replacement policy.',
                tile_format='16 NES planar bytes are source payload only; SNES conversion/role/VRAM placement and headers are excluded.',
                all_bg_reads=len(trace),pixel_referenced_reads=len(used),policies=policies,
                bank_declarations=bank_declarations(a.run/'control.tsv',frame_rows,trace),
                ideal_zero_latency_replay=replays,
                timing=dict(deadline_proven=False,queue_size_proven=False,
                            reason='Requests occur at NES fetch demand. No producer/consumer phase, service latency, packet format or SNES delivery schedule modeled.',
                            comparison_only=dict(prior_239_line_raw_blank_clocks=30008,
                                                 assumed_snes_dma_clocks_per_byte=8,
                                                 cold_4kib_chr_clocks=32768,
                                                 excess_over_raw_blank_clocks=2760,
                                                 crop_policy_approved=False)),
                input_audit=dict(passed=audit['passed'],rom_sha256=audit['rom_sha256'],
                                 frames=len(audit['frames']),pixels=sum(f['pixels'] for f in audit['frames'])),
                inputs={str(p):sha(p) for p in (a.run/'fetch.tsv',a.run/'frames.tsv',a.run/'control.tsv',
                         a.run/'chr.hex',a.reference/'trace.tsv',a.rom/'mmc3.nes')},
                tool_sha256=sha(__file__))
    (a.out/'input-audit.json').write_text(json.dumps(audit,indent=2)+'\n',encoding='utf-8')
    (a.out/'workload.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(candidate=CANDIDATE,passed=True,frames=frames,policies=policies['all_bg'],
                         bank_declarations=result['bank_declarations']),indent=2))
if __name__=='__main__':
    main()