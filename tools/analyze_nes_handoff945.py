"""Locate receipt polling and first BG service on the same ARM/65816 clock."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from analyze_nes_oam944 import (analyze, boundary, chain, directory, job_times, ordinary_packets,
                                read, read_csv, sha, trace, jobs as tile_jobs)
from analyze_nes_head939 import first_bg
from nes_handoff945 import MODES, base, work


def handoff(folder, generation):
    b = boundary(folder, generation)
    first = first_bg(folder, generation)
    sample = next(row for row in b['E0s'] if row['valid'])
    transitions=[e for e in read(folder/'events.json') if e['event']=='SPI'
                 and b['commit_D2'] < e['start'] < b['planner']]
    begin=next(i for i,e in enumerate(transitions) if e['opcode']=='0xe1')
    return dict(pre_BEGIN=[e['opcode'] for e in transitions[:begin]],
                post_BEGIN=[e['opcode'] for e in transitions[begin+1:]],input_D2=b['data_D2'], show=b['show'], snes_ACK=b['ack'],
                E0_start=round(b['show'] + sample['start']), E0=b['E0'], EA=b['EA'],
                COMMIT=b['commit'], commit_D2=b['commit_D2'], planner=b['planner'],
                E9=first['first_E9'], BG=first['ready'], E0s=b['E0s'])


def compare(temp, modes):
    rom = base.prev.prior.ROM / 'sink165.sfc'
    data = dict(clock_Hz=21477272, hardware=False, ROM=sha(rom), ROM935=sha(chain.output('bounded')/'sink165.sfc'), links={}, cases={})
    for mode in modes:
        arm = work(mode)
        fw = arm / 'link/src/obj-nes-100/firmware.stm'
        link = data['links'][mode] = dict(Flash=fw.stat().st_size, firmware=sha(fw))
        for key,file in (('index','index945.json'),('receipt','receipt945.json')):
            if (arm/file).is_file():
                link[key]=read(arm/file)
        safety = arm/'safety945.json'
        if safety.is_file():
            link['safety'] = read(safety)
            assert link['safety']['firmware'] == link['firmware'] and link['safety']['consumer']==data['ROM']
    for cache in ('warm', 'cold'):
        for phase in (1, 2):
            group = data['cases'][cache+str(phase)] = {}
            ref = directory(temp, phase, '935boundedfinal', cache)
            jobs = job_times(ref)
            ack = read(ref/'joint.json')['frames'][-1]['ACK_masterclock']
            before = ordinary_packets(ref)
            for name in ('935', '944', *modes):
                tag = {'935':'935boundedfinal', '944':'944smallbg'}.get(name, '945'+name)
                folder = directory(temp, phase, tag, cache)
                joint = read(folder/'joint.json')
                assert joint['passed'] and joint['client_SHA256'] == data['ROM935' if name=='935' else 'ROM']
                times = job_times(folder)
                assert times.keys() == jobs.keys() and ordinary_packets(folder) == before
                row = group[name] = dict(handoff={g:handoff(folder,g) for g in (907,912)})
                window=read_csv(folder,'window.csv')
                row['frame906']=[dict(event=r['event'],frame=int(r['frame']),line=int(r['line']),value=int(r['value']))
                    for r in window if r['g']=='906' and (r['event'] in ('reveal','ppu_dma') or
                        (r['op']=='3' and r['event']=='load'))]
                if cache=='cold' and phase==1:
                    row['bank_912']={token:job['clocks'] for token,job in tile_jobs(folder,(33,34,36),generation=912).items()}
                    bank=row['bank_912']
                    credit=[e for e in read(folder/'events.json') if e['event']=='SPI' and e['opcode']=='0xe0'
                            and bank[33]['E1']<e['start'] and e['clock']<bank[34]['E8']]
                    row['credit_before_34']=[dict(start=round(e['start']),end=round(e['clock']),reply=e['reply'])
                                             for e in credit]
                if name in ('935','944'):
                    continue
                assert joint['firmware_SHA256'] == data['links'][name]['firmware']
                with patch.object(chain, 'output', lambda _:base.prev.prior.ROM):
                    metrics = analyze(temp, name, phase, cache, tag=tag, arm=work(name))
                stages = trace(folder)
                row.update(OBJ_first=stages['OBJ_first'], received=stages['sealed_reads'],
                    first_BG909=stages['BG'], gaps=metrics['gaps'], intervals=metrics['total'],
                    early=metrics['early912'], tail=bool(metrics['tail']), capture=metrics['capture_margin'],
                    ACK_delta=metrics['ACK912']-ack,
                    following=[times[key]-jobs[key] for key in ((909,17,1,384),(909,18,1,64))],
                    later=[(k,v-jobs[k]) for k,v in times.items()
                           if k[:2] not in ((912,32),(912,35)) and v>jobs[k]])
                assert len(row['later']) == metrics['later_vs935'] and metrics['other_count']==37
    baseline=read(Path(__file__).resolve().parents[1]/'analysis/oam944-results.json')
    for mode in modes:
        rows=[group[mode] for group in data['cases'].values()]
        cold=rows[2:]
        data['links'][mode]['gates']=dict(
            flash=data['links'][mode]['Flash']<=212992,
            cold17=all(r['received']==17 for r in cold),
            cold_first_BG=cold[0]['first_BG909']<=baseline['cases']['cold1']['943']['BG'],
            OBJ_order=all(r['OBJ_first'] for r in rows),
            following=all(max(r['following'])<=0 for r in rows),
            warm13=all(r['intervals']==13 for r in rows[:2]),
            cold15_496=all(r['intervals']==15 and r['early']==496 and r['tail'] for r in cold),
            capture=all(r['capture']>=0 for r in rows),
            other37=all(not r['later'] for r in rows),
            ACK=all(r['ACK_delta']<=0 for r in rows))
    return data


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(compare(a.temp,a.modes),indent=2)+'\n',encoding='utf-8')
