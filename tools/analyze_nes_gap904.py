"""Compare the physical interval, unmodified game pictures, fitted sources and joint replay."""
import csv
import io
import json
import struct
import sys
from pathlib import Path

from PIL import Image
from analyze_nes_map830 import window
from analyze_nes_output822 import CLK_MS
from replay_nes_gap904 import ARM,CLIENT,PROBES,TEST,sha

ROOT=Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_bytes())


def ms(clocks):
    return round(clocks/CLK_MS,4)


def original(temp,w):
    path=temp/'nes-mask820-continuous03/normal/frames.bin'
    blacks=[]
    with path.open('rb') as f:
        for frame in range(1,3601):
            data=f.read(struct.unpack('<I',f.read(4))[0])
            if 3300<=frame<=3500:
                with Image.open(io.BytesIO(data)) as im:
                    rgb=im.convert('RGB').tobytes()
                if not any(rgb):blacks.append(frame)
                for name in ('capture','edges'):
                    sampled=w/name/f'frame-{frame:04d}.rgb'
                    if sampled.exists():assert rgb==sampled.read_bytes()
        assert not f.read(1)
    counts=[list(map(int,r)) for r in csv.reader((w/'count.csv').read_text().splitlines())]
    assert all(a==b==3300+i for i,(a,b,_,_) in enumerate(counts)) and len(counts)==201
    empty=[f for f,_,_,n in counts if n==0]
    assert blacks==list(range(3347,3369)) and empty==list(range(3349,3362))
    for file in ('index.json','edge-index.json'):
        for group in read(w/file)['clips'].values():
            for r in group['frames']:
                assert counts[r['source']-3300][3]==r['records']['ppu-fetch.bin']
    board=(w/'rtl/0.log').read_text()
    assert all('REJECT904 '+str(f)+' ' in board for f in (3348,3350))
    assert 'GEOMETRY230 frame=3362 records=' in board and f'PASS GEOMETRY230 frames={len(TEST)}' in board
    return dict(ROM=read(w/'capture/capture.json')['rom'],core=read(w/'capture/capture.json')['core'],
                frames_sha256=sha(path),bus_sha256=sha(w/'count.csv'),black=[blacks[0],blacks[-1]],
                no_pattern_reads=[empty[0],empty[-1]],counts_at_edges=[row for row in counts if row[0] in (3347,3348,3349,3361,3362)],
                rtl_log_sha256=sha(w/'rtl/0.log'),rejected_test_frames=[3348,3350],resumed=3362)


def analyze_run(temp,w,group,phase,control):
    tag={'ideal':'904-ideal2','cold':'904-cold','':'904-retire' if group=='obj' else '904-trace2'}[control]
    p=temp/f'nes-tile821-{group}-jointmirror-p{phase}-{tag}'
    result=read(p/'joint.json')
    assert result['passed'] and result['last_status']==1
    assert result['firmware_SHA256']==sha(ARM/'obj-nes-100/firmware.stm')
    assert result['client_SHA256']==sha(CLIENT/'sink165.sfc')
    verified=read(w/f'sender-{group}/verified.json')['frames']
    work=read(w/f'data-{group}/{group}/work.json')
    events=read(p/'events.json')
    spi=[r for r in events if r['event']=='SPI']
    status={(r['input_generation'],r['clock']):bytes.fromhex(r['reply'])
            for r in events if r['event']=='input_status904'}
    grants=read(p/'grants904.json')
    producers=[json.loads(line) for line in (p/'producer.jsonl').read_text().splitlines()]
    returns=dict(read(p/'returns904.json')) if group=='obj' and not control else {}
    banks=read(p/'banks904.json')
    shows={r['g']:r for r in window(p) if r['event']=='reveal'}
    rows=[]
    for a,b,v in zip(work[1:-1],work[2:],verified[2:],strict=True):
        g=b['g']
        assert g==v['generation'] and b['source_frame']==v['source']
        prev=shows[a['g']]['clock']
        def elapsed(clock):return ms(clock-prev)
        ins=[r for r in spi if r.get('input_generation')==g]
        first=next(r for r in ins if r['opcode']=='0xd1')
        offer=next(r for r in reversed(ins[:ins.index(first)]) if r['opcode']=='0xd0')
        assert status[g,offer['start']][2]&1
        d3=next(r for r in ins if r['opcode']=='0xd3')
        pops=[r for r in ins if r['opcode']=='0xd2' and r['clock']<d3['start']]
        last=pops[-1]
        confirm=next(r for r in ins if r['opcode']=='0xd0' and r['start']>=last['clock'])
        assert confirm['clock']<=d3['start'] and len(pops)==v['transactions']-1
        confirmed=confirm['clock']
        first_source=next(r for r in events if r['event']=='sender652_ready' and r['input_generation']==g and r['index']==0)
        phase_rows=banks[str(g)]['banks557']
        tiles=[r for r in producers if r['generation']==g]
        final=tiles[-1]
        assert final['bytes']>0
        bound=final['producer']
        if group=='gap' and b['source_frame']==3362:
            assert all(not any((p/f'frame-{gen}.rgb').read_bytes()) for gen in (a['g'],g))
        gs=[(k,q,start,end) for generation,k,q,start,end in grants if generation==g]
        assert all(q<=start<end for _,q,start,end in gs)
        # Intersect with the interval under discussion. SPI overlaps these
        # waits and must not be added a second time.
        selected=[(k,max(q,confirmed),min(start,bound)) for k,q,start,_ in gs if q<bound and start>confirmed]
        assert all(x[2]<=y[1] for x,y in zip(selected,selected[1:]))
        ack=result['frames'][work.index(b)]['ACK_masterclock']
        r=dict(source=b['source_frame'],generation=g,input_blocks=len(pops),first_ready_ms=elapsed(first_source['ready']),
               first_positive_D0_ms=elapsed(offer['clock']),first_D1_ms=elapsed(first['clock']),
               last_data_D2_ms=elapsed(last['clock']),confirmed_ms=elapsed(confirmed),
               E9_seal_ms=[elapsed(s['seal']) for s in phase_rows],
               E9_mailbox_release_ms=[elapsed(s['release']) for s in phase_rows],
               jobs=[[s['token'],s['kind'],s['bytes'],elapsed(s['producer'])] for s in tiles],
               ready_after_input_ms=ms(bound-confirmed),grants=len(gs),
               waits_ms_by_kind=[ms(sum(e-s for k,s,e in selected if k==kind)) for kind in (0,1)],
               RGB=sha(p/f'frame-{g}.rgb'),map=sha(p/f'map-{g}.bin'),work=b,
               VBlanks=shows[g]['frame']-shows[a['g']]['frame'],
               reveal_ms=elapsed(shows[g]['clock']),ACK=ack)
        if returns:
            r['consumer_returns_ms']=[[s['token'],elapsed(returns[s['token']])] for s in tiles]
            assert all(s['producer']<=returns[s['token']]<=ack for s in tiles)
        rows.append(r)
    return dict(rows=rows,initial_clock=result['parameters']['start'],total_VBlanks=sum(r['VBlanks'] for r in rows),
                final_ACK=rows[-1]['ACK'],ROM_calendar_sha256=sha(temp/'nes-service509-rom03/fill1/rom.tsv'),
                sender_sha256=sha(w/f'sender-{group}/sender.json'))


def analyze(temp):
    w=temp/'nes-gap904'
    out=dict(original=original(temp,w),physical_input=sha(ROOT/'analysis/hardware903-results.json'),
             firmware=sha(ARM/'obj-nes-100/firmware.stm'),client=sha(CLIENT/'sink165.sfc'),replays={})
    for name in ('nes_chr_cache611.sv','nes_obj_capture611.sv'):
        assert sha(temp/'nes-trial816-board822held'/name)==sha(temp/'nes-trial816-board903'/name)
    for group,control in [('gap',''),('obj',''),('obj','ideal'),('obj','cold')]:
        for phase in (1,2):
            r=analyze_run(temp,w,group,phase,control)
            out['replays'][f'{group}-{phase}'+('-'+control if control else '')]=r
            if control:
                reference=out['replays'][f'{group}-{phase}']
                for a,b in zip(reference['rows'],r['rows'],strict=True):
                    for key in ('source','RGB','map','input_blocks','work'):assert a[key]==b[key]
                    if control=='ideal':
                        assert a['grants']==b['grants']
                        assert [s[:3] for s in a['jobs']]==[s[:3] for s in b['jobs']]
                    else:
                        assert b['grants']>=a['grants']
                        for kind in (0,1):
                            assert sum(s[2] for s in a['jobs'] if s[1]==kind)==sum(s[2] for s in b['jobs'] if s[1]==kind)
    return out


if __name__=='__main__':
    Path(sys.argv[2]).write_text(json.dumps(analyze(Path(sys.argv[1])),indent=2)+'\n',encoding='utf-8')
