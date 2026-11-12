"""Verify the executed 957 beam schedule and the preceding 52 commits."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_owner739 import csv_groups, ms, read, sha
from prepare_nes_longrun694 import optimal, codec
from replay_nes_beam741 import replacements
from replay_nes_gap740 import schedule


def records(path):
    with path.open() as stream:
        return [{k: (v if k == 'event' else int(v)) for k, v in r.items()}
                for r in csv.DictReader(stream)]


def measure(folder, base, ref, phase, feedback=False):
    rows = csv_groups(folder/'window.csv')
    audit = read(folder/'audit.json')
    assert audit['frames'] == read(folder/'result.json')['commits'] == 53
    assert all(sha(folder/f'frame-{g}.rgb') == sha(base/f'frame-{g}.rgb') for g in range(905, 958))
    actions = rows[957]
    def final(g, kind):
        return next(r for r in rows[g] if r['op'] == 3 and r['event'] == kind)
    def grants(g):
        data = rows[g]
        out = []
        for i, r in enumerate(data):
            if r['event'] == 'idle524':
                start = next(s for s in data[i+1:] if s['event'] == 'ppu_dma')
                end = next(s for s in data[i+1:] if s['event'] == 'ppu_last' and s['clock'] > start['clock'])
                assert start['frame'] == end['frame'] and 225 <= start['line'] <= end['line'] <= 261
                out.append(dict(offset=r['value'], size=start['value'], start=start['clock'],
                                end=end['clock'], lines=[start['line'], end['line']]))
        return out
    prefix = grants(957)
    assert any(x['offset'] == 65536+2048 and x['size'] == 1536 for x in grants(952))
    frames = {g: final(g,'reveal')['frame']-final(g-1,'reveal')['frame'] for g in (908,911,951,952,956,957)}
    assert frames == {908:2,911:2,951:3,952:3,956:3,957:3}
    assert final(951,'reveal')['line'] <= 246
    wait = sum(r['event']=='wait169' and r['clock']>final(957,'final212')['clock'] for r in actions)
    assert wait == 0
    ack = final(957,'ack')['clock']
    dense = ms(final(957,'reveal')['clock']-final(951,'reveal')['clock'])/6
    final_obj = [r for r in records(folder/'seal528.csv') if r['g']==957 and r['event']=='dma' and 19104<=r['src']<19392]
    assert len(final_obj)==1 and final_obj[0]['src']+final_obj[0]['bytes']==19392
    cutoff = ref['deadline_line247_start']
    oam_ack = next(r for r in actions if r['event']=='ack' and r['op']==9 and r['section']==4)
    proof = next(r for r in records(folder/'owner.csv') if r['event']=='proven635')
    assert proof['clock']<oam_ack['clock']<cutoff
    seen = [r for r in records(folder/'budget685.csv') if r['generation']==957 and r['range']==1536]
    long_map = next((r for r in prefix if r['offset']==67584 and r['size']==1536), None)
    arrivals = [line.split('\t') for line in (folder/'arrivals.tsv').read_text().splitlines()]
    scroll = next(int(t) for t,h,_ in arrivals if h!='FINISH' and bytes.fromhex(h)[1]==5
                  and int.from_bytes(bytes.fromhex(h)[8:10],'little')==957)
    result = dict(ACK_clock=ack, ACK_delta_us=1000*ms(ack-ref['last_ACK_clock']),
                  dense_ms=dense, dense_delta_us=1000*(dense-ref['dense_ms']), display_intervals=frames,
                  final_wait=wait, OAM_ACK_before_247_us=1000*ms(cutoff-oam_ack['clock']),
                  map_latch=[[r['line'],r['h'],r['bytes']] for r in seen],
                  prefix_after_OAM=[r for r in prefix if r['start']>oam_ack['clock']],
                  OBJ_prefix_B=288-final_obj[0]['bytes'], scroll_push=scroll,
                  passed=bool(long_map and dense<ref['dense_ms'] and ack<ref['last_ACK_clock']),
                  pins={p:sha(folder/p) for p in ('arrivals.tsv','window.csv','owner.csv','select741.csv','seal528.csv','budget685.csv')})
    if feedback:
        policy=schedule(base,phase,'first')
        pulse=int((folder/'pulse741.txt').read_text().splitlines()[0])
        timing=read(folder/'timing741.json')
        assert pulse==policy['pulse']+timing['pulse_shift']
        assert abs(scroll-pulse-policy['callback_masterclocks'])<=1
        lastmap_ack=max(r['clock'] for r in actions if r['event']=='ack' and r['clock']<proof['clock'] and r['section']==2)
        assert lastmap_ack<=policy['map_receipt']['start']
        assert long_map and scroll<long_map['end'] and result['OBJ_prefix_B']==0
        assert [b['size'] for b in result['prefix_after_OAM']]==[384,48,1536]
        assert result['prefix_after_OAM'][-1]['lines'][1]>257
        next_action=next(r for r in actions if r['clock']>long_map['end'] and r['event'] in ('load','ppu_dma'))
        assert next_action['event']=='load' and next_action['section']==5
        result['pins'].update({p:sha(folder/p) for p in ('pulse741.txt','timing741.json')})
        beam=next(b for b in seen if b['bytes']==1536)
        result.update(map_ACK=lastmap_ack, progress=pulse, scroll_before_map_end_us=ms(long_map['end']-scroll)*1000,
                      remaining_after_map_clocks=(262-beam['line'])*1364-beam['h']-(long_map['end']-beam['latch_clock']),
                      D0_advance_us=ms(timing['advance'])*1000)
    return result


def main(args):
    ref=read(Path('analysis/owner739-verification.json'))['phases']
    result={'stage':741,'reference':727,'selected':False,'phases':{}}
    for n in (1,2):
        base=args.temp/f'nes-pair727-a{n}'
        cases={}
        for case,calendar,variant,suffix in [
            ('control','first','control',''), ('BG','first','bg',''),
            ('dynamic','first','budget','-feedback'), ('D0_overlap','overlap','budget','-feedback'),
            ('early_upper_bound','issued','fragment','')]:
            folder=args.temp/f'nes-beam741-{calendar}-{variant}{n}-trace{suffix}'
            cases[case]=measure(folder,base,ref[str(n)]['ref'],n,'feedback' in suffix)
        assert all(not cases[k]['passed'] for k in ('dynamic','D0_overlap'))
        assert cases['early_upper_bound']['OBJ_prefix_B']==64
        result['phases'][n]=cases
    edge=args.temp/'nes-beam741-first-budget2-trace-edgeprobe'
    beam=[r for r in records(edge/'budget685.csv') if r['generation']==957 and r['range']==1536]
    assert read(edge/'audit.json')['frames']==53 and any(r['line']==250 and r['h']>=512 and r['bytes']==1152 for r in beam)
    result['late_latch']=[[r['line'],r['h'],r['bytes']] for r in beam]
    guards={}
    for name,code in [('first-budget1-stop-before',0),('issued-fragment1-stop-during',0),('first-budget1-stale-fault',224)]:
        f=args.temp/('nes-beam741-'+name)
        j=read(f/'result.json')
        assert j['passed'] and j['last_status']==code and j['commits']==52
        assert sha(f/'retained.rgb')==sha(args.temp/'nes-pair727-a1/frame-956.rgb')
        if 'stop' in name:
            fault=int((f/'fault741.txt').read_text())
            late=[r['event'] for r in csv_groups(f/'window.csv')[957] if r['clock']>fault and r['event'] in ('ppu_dma','ppu_last')]
            assert late==(['ppu_last'] if 'during' in name else [])
        guards[name]=code
    f=args.temp/'nes-beam741-first-budget1-trace-head'
    now,old=map(int,(f/'fault741.txt').read_text().split())
    rows=csv_groups(f/'window.csv')[957]
    next_event=next(r for r in rows if r['clock']>now and r['event'] in ('load','ppu_dma'))
    assert now<old and next_event['event']=='load' and next_event['section']==5 and read(f/'audit.json')['frames']==53
    guards['new_head_before_BG']=next_event['clock']
    for trial in (690,704):
        menu=read(args.probe/f'menu-{trial}.json')
        assert menu['marker_cases']==4 and len(menu['rows'])==5
        assert all(bool(v['released'])==(k=='normal') for k,v in menu['rows'].items())
        guards[f'menu_{trial}']=menu['firmware']
    result['guards']=guards
    body=bytearray((args.client/'body.bin').read_bytes())
    for addr,code in sorted(replacements(args.client,'budget').items()):
        start=addr-codec.DEST
        assert start<=len(body)
        body[start:start+len(code)]=code
    result['WRAM_body_B']=len(body)
    result['ROM_free_by_prefix']={p:codec.STORED-codec.BOOT-p-len(optimal(bytes(body),p)) for p in (512,384,256,128)}
    args.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','probe','client','out'):
        parser.add_argument('--'+key,type=Path,required=True)
    main(parser.parse_args())
