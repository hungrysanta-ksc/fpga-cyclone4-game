"""Correlate wire order and returned banks against identical 935 and 943 workloads."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from analyze_nes_sealed943 import (boundary, chain, directory, job_times, jobs,
                                   ordinary_packets, read, read_csv, sha)
from analyze_nes_wait936 import analyze
from nes_oam944 import MODES, prev, work


def trace(folder):
    wire=iter(json.loads(line) for line in (folder/'packets.jsonl').read_text().splitlines())
    spi=read(folder/'events.json')
    for event in spi:
        if event.get('opcode')!='0xe1':
            continue
        b=bytes.fromhex(next(wire)[2])
        if b[:2]==bytes((8,4)) and int.from_bytes(b[8:10],'little')==909:
            fill=event
            break
    else:
        raise AssertionError('missing repeated OAM packet')
    heads=[r for r in read_csv(folder,'window.csv') if r['g']=='909' and r['op']=='8']
    loaded,returned=[next(int(r['clock']) for r in heads if r['event']==kind) for kind in ('load','ack')]
    by_token={k:v['clocks'] for k,v in jobs(folder,(15,16,17,18),generation=909).items()}
    bg=boundary(folder)
    return dict(jobs=by_token,fill_start=round(fill['start']),fill_end=round(fill['clock']),
        fill_load=loaded,fill_ACK=returned,BG=bg['first_BG'],sealed_reads=bg['reads_before_show'],
        near_fill=[(e['opcode'],round(e['start']),round(e['clock']),e.get('reply',''))
            for e in spi if e.get('opcode') and fill['start']-12000<e['clock']<=fill['clock']],
        OBJ_first=by_token[15]['E1']<=fill['start'] and by_token[15]['load']<loaded)


def report(temp,modes):
    out=dict(links={},cases={},physical=False,master_Hz=21477272)
    out['consumer_sha256']=sha(prev.prior.ROM/'sink165.sfc')
    out['receiver_schedule_sha256']=sha(prev.work('capclass')/'link/src/nes_native_runtime165.c')
    for m in modes:
        assert sha(work(m)/'link/src/nes_native_runtime165.c')==out['receiver_schedule_sha256']
        fw=work(m)/'link/src/obj-nes-100/firmware.stm'
        link=out['links'][m]=dict(firmware=sha(fw),Flash=fw.stat().st_size)
        s=work(m)/'safety944.json'
        if s.exists():
            link['safety']=read(s)
            assert link['safety']['firmware']==link['firmware'] and link['safety']['consumer']==sha(prev.prior.ROM/'sink165.sfc')
            link['frozen']=read(work(m)/'frozen944.json')
            for name in ('dispatch938','decode940'):
                check=read(work(m)/(name+'.json'))
                assert check['firmware']==link['firmware']
                link[name]=check
    for cache in ('warm','cold'):
        for phase in (1,2):
            group=out['cases'][f'{cache}{phase}']={}
            ref,base=[directory(temp,phase,name,cache) for name in ('935boundedfinal','943capclass')]
            reference=job_times(ref)
            ack935=read(ref/'joint.json')['frames'][-1]['ACK_masterclock']
            group['935'],group['943']=trace(ref),trace(base)
            for m in modes:
                tag='944'+m
                folder=directory(temp,phase,tag,cache)
                joint=read(folder/'joint.json')
                assert joint['passed'] and joint['firmware_SHA256']==out['links'][m]['firmware']
                assert joint['client_SHA256']==sha(prev.prior.ROM/'sink165.sfc')
                assert ordinary_packets(folder)==ordinary_packets(base)
                times=job_times(folder)
                assert times.keys()==reference.keys()
                row=group[m]=trace(folder)
                with patch.object(chain,'output',lambda _:prev.prior.ROM):
                    stats=analyze(temp,m,phase,cache,tag=tag,arm=work(m))
                late=[(k,v-reference[k]) for k,v in times.items() if k[:2] not in ((912,32),(912,35)) and v>reference[k]]
                assert stats['other_count']==37 and len(late)==stats['later_vs935']
                row.update(BG_delta935=row['BG']-group['935']['BG'],capture=stats['capture_margin'],
                    total=stats['total'],intervals=stats['gaps'],preDMA=stats['early912'],tail=bool(stats['tail']),
                    ACK=stats['ACK912'],ACK_delta=stats['ACK912']-ack935,late=late,
                    supply_delta935=[row['jobs'][t]['ready']-group['935']['jobs'][t]['ready'] for t in (17,18)])
    for m,link in out['links'].items():
        rows=[g[m] for g in out['cases'].values()]
        cold=rows[2:]
        link['gates']=dict(flash=link['Flash']<=212992,first_BG=cold[0]['BG_delta935']<0,
            first_BG_no_later_943=cold[0]['BG']<=out['cases']['cold1']['943']['BG'],
            input17=cold[0]['sealed_reads']==17,first_OBJ_before_OAM=all(r['OBJ_first'] for r in rows),
            other_jobs=all(not r['late'] for r in rows),both_followups=all(max(r['supply_delta935'])<=0 for r in rows),
            warm13=all(r['total']==13 for r in rows[:2]),cold15_496=all(r['total']==15 and r['preDMA']==496 and r['tail'] for r in cold),
            capture=all(r['capture']>=0 for r in rows),ACK=all(r['ACK_delta']<=0 for r in rows))
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.modes),indent=2)+'\n',encoding='utf8')
