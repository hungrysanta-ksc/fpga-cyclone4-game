# SPDX-License-Identifier: MIT
"""Bind reset image, ARM E8 transaction, actual WRAM ranges, PPU writes and display ACK."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from analyze_nes_bg750 import counters
from analyze_nes_owner739 import csv_groups, ms, read, sha
from analyze_nes_receipt742 import whole


def phase(temp,variant,n):
    client=temp/f'nes-static751-{variant}'
    folder=temp/f'nes-static751-{variant}{n}'
    reference=temp/f'nes-obj749-page{n}'
    prior=read(Path('analysis/obj749-verification.json'))['phases'][str(n)]
    image=sha(client/'sink165.sfc')
    summary=whole(folder,temp/f'nes-pair727-a{n}',expected_client_sha=image)
    joint=read(folder/'joint.json')
    assert 'for i,v in ipairs({' not in (folder/'capture.lua').read_text(encoding='utf8')
    assert image==sha(folder/'client.sfc') and summary['firmware']==prior['page']['firmware']
    def query(d):
        return next(e for e in read(d/'events.json') if e.get('generation')==957 and
                    e.get('opcode')=='0xe8' and e['reply']==prior['page']['E8_reply'])
    old,new=query(reference),query(folder)
    e8_exact=(new['start'],new['clock'],new['reply'])==(old['start'],old['clock'],old['reply'])
    def before_query(d,query_event):
        events=[e for e in read(d/'events.json') if e.get('event')=='SPI' and e.get('generation')==957
                and e['clock']<=query_event['start']]
        return [{key:e.get(key) for key in ('opcode','packet_opcode','start','clock','bytes')} for e in events[-9:]]
    issuance={'static':before_query(folder,new),'749':before_query(reference,old)}
    windows=csv_groups(folder/'window.csv')
    def reveal(g):
        return next(r['clock'] for r in windows[g] if r['event']=='reveal')
    oldwin=csv_groups(reference/'window.csv')
    oldrev=next(e['clock'] for e in oldwin[956] if e['event']=='reveal')
    def public(rows,g):
        e=next(r for r in rows[g] if r['event']=='reveal')
        return {k:e[k] for k in ('frame','clock','line')}
    first_public={'749':public(oldwin,905),'static':public(windows,905)}
    frame_offsets={g:public(windows,g)['frame']-public(oldwin,g)['frame'] for g in windows if g in oldwin and g>=905 and g<=957}
    starts=counters(folder/'dma748.csv')
    def actual(g,src0,src1):
        rows=windows[g]
        seal=next(r['clock'] for r in rows if r['op']==3 and r['event']=='load')
        x=[]
        for r in starts:
            if r['g']!=g or not src0<=r['source']<src1:continue
            i=next(i for i,e in enumerate(rows) if e['event']=='ppu_dma' and e['clock']>=r['clock'])
            first=rows[i];last=next(e for e in rows[i+1:] if e['event']=='ppu_last')
            assert first['clock']-r['clock']<120 and first['value']==r['bytes']
            assert first['frame']==last['frame'] and 225<=r['line']<=last['line']<=261
            x.append(dict(**r,frame=first['frame'],last=last['clock'],end_line=last['line'],preseal=r['clock']<seal))
        return x
    groups={g:actual(g,src,src+1536) for g,src in ((952,0xd800),(957,0x5800))}
    longmaps={g:next((r for r in rows if r['bytes']==1536 and r['preseal']),None) for g,rows in groups.items()}
    assert all(bool(longmaps[g])==summary['long_map'][g] for g in groups)
    with (folder/'budget685.csv').open() as stream:
        grants=[{k:int(v) for k,v in row.items()} for row in csv.DictReader(stream)]
    latches={}
    for g,r in longmaps.items():
        if r:
            grant,=[e for e in grants if e['generation']==g and e['bytes']==1536 and 0<=r['clock']-e['clock']<400]
            latches[g]=grant['line']
    obj,=actual(957,0x4aa0,0x4aa1)
    bg,=actual(957,0x840,0x841)
    assert bg['bytes']==48 and obj['bytes']==288
    m=longmaps[957]
    same=bool(m and m['frame']==obj['frame'])
    margin=(258-obj['line'])*1364-obj['h'] if same else None
    order=bool(m and bg['last']<m['clock']<m['last']<obj['clock'])
    protected=(summary['public951']<=246 and summary['final_wait957']==0 and
               all(summary['intervals'][g]<=v for g,v in ((908,2),(911,2),(952,3))))
    safe=all(longmaps.values()) and all(line<=248 for line in latches.values()) and order and same and margin>0 and (n==2 or margin>=12) and protected
    metrics=summary['dense_delta_us']<0 and summary['ACK_delta_us']<0
    return dict(E8_start=new['start'],E8_end=new['clock'],E8_reply=new['reply'],E8_exact=e8_exact,E8_749_start=old['start'],E8_749_end=old['clock'],
                E8_delta_clocks=new['start']-old['start'],E8_delta_us=1000*ms(new['start']-old['start']),
                previous_SPI=issuance,
                E8_since956_delta_us=1000*ms(new['start']-reveal(956)-old['start']+oldrev),
                first_public=first_public,frame_offsets_749=frame_offsets,first_poll=joint['first_packet_poll_masterclock'],first_poll_749=read(reference/'joint.json')['first_packet_poll_masterclock'],
                map_latch_lines=latches,map_ranges=groups,long_map=summary['long_map'],BG=bg,OBJ=obj,order=order,
                margin_to_258=margin,line951=summary['public951'],final_wait957=summary['final_wait957'],
                intervals=summary['intervals'],dense_ms=summary['dense_ms'],dense_delta_us=summary['dense_delta_us'],
                ACK=summary['final_ACK'],ACK_727=prior['ref']['ACK'],ACK_delta=summary['final_ACK']-prior['ref']['ACK'],
                guarded_schedule=bool(safe),meets=bool(safe and metrics and e8_exact),
                pins=dict(**summary['pins'],MDMAEN=sha(folder/'dma748.csv'),script=sha(folder/'capture.lua')))


def analyze(a):
    j=dict(stage=751,reference=727,E8_reference=749,board='707D',variants={})
    for k in ('tail','shared','fused','fused512','sharedfast','fusedfast'):
        client=a.temp/f'nes-static751-{k}'
        build=read(client/'build.json')
        rom=(client/'sink165.sfc').read_bytes()
        assert bytes.fromhex((client/'sink-program.hex').read_text())==rom[:5056]+rom[-64:]
        assert len(rom)==32768 and build['physical_ROM_B']==5120 and build['physical_free_B']>=0
        j['variants'][k]=dict(ROM=sha(client/'sink165.sfc'),physical_SHA256=hashlib.sha256(rom[:5056]+rom[-64:]).hexdigest(),body=sha(client/'body.bin'),
            bytes={s:build[s] for s in ('body_bytes','physical_free_B','prefix_B','loader_B','encoded_B')},
            phases={n:phase(a.temp,k,n) for n in (1,2)})
    j['boot']=[read(a.temp/f'nes-boot751-{k}/result.json') for k in ('shared','fused','fast')]
    j['menu']=read(a.temp/'nes-static751-menu.json')
    assert len(j['menu']['rows'])==5 and j['menu']['marker_cases']==4
    assert j['menu']['firmware']==read(Path('analysis/bg750-verification.json'))['firmware']
    j['board_rebuilt']=False
    j['guards']={}
    for folder in sorted(a.temp.glob('nes-static751-guard-*')):
        if not (folder/'verified751.json').exists():
            continue
        evidence=read(folder/'verified751.json')
        assert evidence['client']==j['variants'][evidence['variant']]['ROM']
        j['guards'][folder.name]=evidence
    assert all(f'nes-static751-guard-{variant}{n}-{fault}' in j['guards']
               for variant in ('fused','sharedfast') for n in (1,2) for fault in ('before','during','head','stale'))
    assert all(r['passed'] for group in j['boot'] for r in group['cases'])
    j['scope']='Reset through 53 displays; linked Cortex-M4 / Mesen 65816, modeled SPI, IRQ and ROM contention with pinned 707D evidence.'
    j['legacy_codec_regression']=sha(a.temp/'nes-static751-legacy-regression/sink165.sfc')
    assert j['legacy_codec_regression']==sha(Path('../probes/nes-longrun694/client01/sink165.sfc'))
    j['same_body_fast_boot']={}
    for a1,a2 in (('shared','sharedfast'),('fused512','fusedfast')):
        v,w=[j['variants'][k] for k in (a1,a2)]
        assert v['body']==w['body']
        j['same_body_fast_boot'][a2]=a1
    j['passing']=[k for k,v in j['variants'].items() if all(r['meets'] for r in v['phases'].values())]
    j['timing_pass_allowing_earlier_E8']=[
        k for k,v in j['variants'].items()
        if all(r['guarded_schedule'] and r['E8_start']<=r['E8_749_start']
               and r['dense_delta_us']<0 and r['ACK_delta']<0 for r in v['phases'].values())]
    a.out.write_text(json.dumps(j,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
