# SPDX-License-Identifier: MIT
"""Compare whole boot schedules with two frozen-arrival controls for nine-slot OBJ admission."""
import argparse
import json
from pathlib import Path

from replay_nes_gap740 import schedule
from analyze_nes_receipt742 import cpu_frame, csv_groups, ms, read, records, sha, whole


def probe(folder):
    taps = records(folder/'owner.csv')
    descriptor = [r for r in taps if r['event'] == 'descriptor742']
    bulk = [r for r in taps if r['event'] == 'bulk742']
    assert sorted(r['value'] for r in descriptor) == list(range(0x6040, 0x604c))
    assert [r['value'] for r in bulk] == [0, 1, 287]
    release = next(r for r in taps if r['event'] == 'bank_release' and r['value'] == 120)
    assert descriptor[-1]['clock'] < bulk[0]['clock'] < bulk[-1]['clock'] < release['clock']
    obj = [r for r in records(folder/'tile532.csv') if r['g'] == 957 and 19104 <= r['src'] < 19392]
    final = [r for r in records(folder/'seal528.csv') if r['g'] == 957 and r['event'] == 'dma' and 19104 <= r['src'] < 19392]
    assert sum(r['n'] for r in obj) + sum(r['bytes'] for r in final) == 288
    frames = {g: cpu_frame(folder,g) for g in (951,952,957)}
    prefix = frames[957]['prefix']
    dma = [next(x for x in prefix if x['start'] >= r['clock']) for r in obj]
    assert all(x['size'] == r['n'] for x,r in zip(dma,obj))
    dense = ms(frames[957]['reveal']['clock']-frames[951]['reveal']['clock']) / 6
    result = dict(descriptor_last=descriptor[-1]['clock'], bulk_first=bulk[0]['clock'], bulk_last=bulk[-1]['clock'],
                  pre_read_us=ms(bulk[0]['clock']-descriptor[-1]['clock'])*1000,
                  mark_to_append_us=ms(next(r['clock'] for r in taps if r['event']=='append212')-
                                       next(r['clock'] for r in taps if r['event']=='mark212'))*1000,
                  bank_release=release['clock'], OBJ_before_SEAL_B=sum(r['n'] for r in obj), OBJ_DMA=dma,
                  final_B=sum(r['bytes'] for r in final), final_ACK=frames[957]['ACK'], dense_ms=dense,
                  final_wait=frames[957]['final_wait'], public951=frames[951]['reveal']['line'],
                  long_map={g:next(x for x in frames[g]['prefix'] if x['size']==1536 and x['offset']==67584) for g in (952,957)},
                  pins={k:sha(folder/k) for k in ('arrivals.tsv','owner.csv','window.csv','tile532.csv','seal528.csv')})
    if dma:
        # Select/grant carry a directly sampled horizontal clock. MDMAEN is a
        # different event. Both timestamps must be in the same blanking period.
        grant = next(r for r in records(folder/'select741.csv') if r['event']=='grant524' and r['src']==19104)
        start = dma[0]['start']
        cutoff = grant['clock']-grant['h']+(258-grant['line'])*1364
        assert grant['clock'] <= start and (start-cutoff)//1364 == dma[0]['first_line']-258
        result['clocks_from_line258'] = start-cutoff
        result['map_end_to_OBJ_start_us'] = ms(start-result['long_map'][957]['end'])*1000
    return result


def analyze(a):
    out = dict(stage=743, retained=727, phases={})
    original = a.original
    clients = {'base':original,'control':a.probe/'control96','live':a.probe/'client'}
    assert sha(clients['control']/'body.bin') == sha(original/'body.bin')
    out['images'] = {}
    for key,folder in clients.items():
        meta = read(folder/'build.json')
        out['images'][key] = {k:meta[k] for k in ('physical_ROM_B','body_bytes','loader_B','prefix_B','encoded_B','physical_free_B')}
        assert meta['physical_ROM_B'] == (folder/'sink-program.hex').read_text().count('\n') == 5120
        out['images'][key].update(body_SHA256=sha(folder/'body.bin'),client_SHA256=sha(folder/'sink165.sfc'))
    assert read(a.temp/'nes-bitmap743-ranges/cases.json') == 2508
    out['range_cases'] = 2508
    for n in (1,2):
        base = a.temp/f'nes-pair727-a{n}'
        def run_path(key):
            return a.temp/f'nes-bitmap743-{key}{n}'
        fixed = {}
        for k,f in [('baseline',run_path('baseline')),('mask',run_path('fixed')),
                    ('early_baseline',a.temp/f'nes-receipt742-poll-original{n}-ranges'),('early_mask',run_path('early'))]:
            assert read(f/'audit.json')['frames']==53
            fixed[k] = probe(f)
        assert fixed['baseline']['pins']['window.csv']==sha(base/'window.csv')
        for before,after in [('baseline','mask'),('early_baseline','early_mask')]:
            b,c = fixed[before],fixed[after]
            assert b['pins']['arrivals.tsv']==c['pins']['arrivals.tsv'] and b['descriptor_last']==c['descriptor_last']
            c.update(first_read_delta_us=ms(c['bulk_first']-b['bulk_first'])*1000,
                     ACK_delta_us=ms(c['final_ACK']-b['final_ACK'])*1000,dense_delta_us=(c['dense_ms']-b['dense_ms'])*1000)
        scroll_run = run_path('scroll')
        assert read(scroll_run/'audit.json')['frames']==53
        pulse = int((scroll_run/'pulse741.txt').read_text().splitlines()[0])
        scroll_offer = next(int(t) for t,header,_ in (line.split('\t') for line in (scroll_run/'arrivals.tsv').read_text().splitlines())
                            if header!='FINISH' and (h:=bytes.fromhex(header))[1]==5 and int.from_bytes(h[8:10],'little')==957)
        assert abs(scroll_offer-pulse-schedule(base,n,'first')['callback_masterclocks'])<=1
        feedback = probe(scroll_run)
        long_map = feedback['long_map'][957]
        assert long_map['start']<scroll_offer<long_map['end']
        following = next(r for r in csv_groups(scroll_run/'window.csv')[957] if r['clock']>long_map['end'] and r['event'] in ('load','ppu_dma'))
        assert following['event']=='load' and following['section']==5
        fixed['first_scroll']=dict(**feedback,first_map_pulse=pulse,scroll_offer=scroll_offer,following=following)
        priced = read(run_path('early')/'receipt742.json')['E0_starts']
        ack = max(r['clock'] for r in csv_groups(run_path('early')/'window.csv')[957] if r['event']=='ack' and r['section']==2)
        assert priced[-1]>ack and all(t<=ack for t in priced[:-1])
        live = {}
        for k,f in [('base',base),('control',run_path('control')),('live',run_path('live'))]:
            j = read(f/'joint.json')
            data = whole(f,base,expected_client_sha=out['images'][k]['client_SHA256'])
            assert data['firmware']==read(base/'joint.json')['firmware_SHA256']
            data.update(first_poll=j['first_packet_poll_masterclock'],cold_ACK=cpu_frame(f,905)['ACK'],
                        rendezvous=int((f/'startup-clock.txt').read_text().split()[0]))
            data['protected'] = all(data['intervals'][g]==v for g,v in [(908,2),(911,2),(952,3)]) and data['public951']<=246 and data['final_wait957']==0 and all(data['long_map'].values())
            live[k] = data
        out['phases'][n] = dict(frozen=fixed, linked=live)
    for k,code in [('stop',0),('mid',0),('stale',224)]:
        f=a.temp/f'nes-bitmap743-{k}1'
        j=read(f/'result.json')
        assert j['passed'] and j['last_status']==code and j['commits']==52
        assert sha(f/'retained.rgb')==sha(a.temp/'nes-pair727-a1/frame-956.rgb')
        out[k] = dict(commits=52,status=code,retained_SHA256=sha(f/'retained.rgb'))
        if k=='mid':
            at=int((f/'fault741.txt').read_text())
            chunk=cpu_frame(a.temp/'nes-bitmap743-early1',957)['prefix'][-1]
            actual=[r for r in csv_groups(f/'window.csv')[957] if r['event']=='ppu_dma' and r['clock']>=chunk['start']]
            assert chunk['start']<=at<=chunk['end'] and len(actual)==1 and actual[0]['value']==64
            out[k].update(held_STOP=at,inflight_B=64)
    stopped=a.temp/'nes-bitmap743-quiet1'
    assert sha(stopped/'window.csv')==sha(a.temp/'nes-bitmap743-mid1/window.csv')
    snapshot=(stopped/'aborted-banks.bin').read_bytes()
    assert len(snapshot)==472 and any(snapshot[:464]) and snapshot[464:466]==snapshot[468:470]==bytes(2)
    reboot=a.temp/'nes-bitmap743-reboot1'
    assert read(reboot/'audit.json')['frames']==53
    assert sha(reboot/'window.csv')==sha(a.temp/'nes-bitmap743-live1/window.csv')
    out['cold_recovery']=dict(restored_WRAM_B=len(snapshot),snapshot_SHA256=sha(stopped/'aborted-banks.bin'),
                              commits=53,trace_SHA256=sha(reboot/'window.csv'))
    f=a.temp/'nes-bitmap743-head1'
    at,old=map(int,(f/'fault741.txt').read_text().split())
    first=next(r for r in csv_groups(f/'window.csv')[957] if r['clock']>at and r['event'] in ('load','ppu_dma'))
    assert at<old and first['event']=='load' and first['section']==5 and read(f/'audit.json')['frames']==53
    out['new_head_first']=first
    out['menu']={}
    for trial in (690,704):
        g=read(a.probe/f'menu-{trial}.json')
        assert len(g['rows'])==5 and g['marker_cases']==4 and all(bool(v['released'])==(k=='normal') for k,v in g['rows'].items())
        out['menu'][trial] = dict(firmware=g['firmware'],cases=list(g['rows']),markers=g['marker_cases'])
    assert out['menu'][690]['firmware']==out['phases'][1]['linked']['live']['firmware']
    out['meets_both_phases']=all(x['linked']['live']['meets'] and x['linked']['live']['protected'] for x in out['phases'].values())
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('temp','probe','original','out'):
        p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
