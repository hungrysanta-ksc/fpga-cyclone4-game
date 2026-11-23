"""Compare actual E0 snapshots with head retirement and the next bank handoff."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

from analyze_nes_handoff945 import analyze, chain, directory, job_times, ordinary_packets, read, sha, tile_jobs, trace
from nes_credit946 import BASE, MODES, ROM, work
from nes_reply946 import image


def observe(folder):
    banks = {k: v['clocks'] for k, v in tile_jobs(folder, (33, 34, 36), generation=912).items()}
    start = banks[33]['E1']
    end = banks[34]['E8']
    polls = [e for e in read(folder/'events.json') if e.get('opcode') == '0xe0'
             and e['start'] > start and e['clock'] < end]
    # E0 carries big-endian 16-bit accepted and retired counters. Verify the
    # head was still pending on the previous snapshot and retired on the last.
    snapshots=[bytes.fromhex(e['reply']) for e in polls]
    assert len(snapshots)>=2 and all(len(r)==20 and r[1]==0xf7 for r in snapshots)
    counters=[(int.from_bytes(r[3:5],'big'),int.from_bytes(r[5:7],'big')) for r in snapshots]
    assert counters[-2][0]!=counters[-2][1] and counters[-1][0]==counters[-1][1]
    return dict(banks=banks, counters=counters, polls=[dict(start=round(e['start']), end=round(e['clock']), reply=e['reply'])
                                    for e in polls],
                sixth_minus_head=round(polls[5]['start']-banks[33]['head_ACK']) if len(polls)>=6 else None)


def collect(temp, modes):
    result = dict(master_Hz=21477272, hardware=False, links={}, cases={})
    baseline943=read(Path(__file__).resolve().parents[1]/'analysis/oam944-results.json')['cases']['cold1']['943']
    for cache in ('warm','cold'):
        for phase in (1,2):
            case = cache+str(phase)
            ref = directory(temp, phase, '935boundedfinal', cache)
            before = job_times(ref)
            ref_ack = read(ref/'joint.json')['frames'][-1]['ACK_masterclock']
            for mode in ['945',*modes]:
                arm = BASE if mode in ('packed','945') else work(mode)
                rom = image(mode) if mode=='packed' else ROM
                tag = '945warm_header' if mode=='945' else '946'+mode
                folder = directory(temp, phase, tag, cache)
                if not (folder/'joint.json').is_file():
                    continue
                joint=read(folder/'joint.json')
                fw=arm/'link/src/obj-nes-100/firmware.stm'
                assert joint['passed'] and sha(fw)==joint['firmware_SHA256'] and sha(rom/'sink165.sfc')==joint['client_SHA256']
                link=result['links'].setdefault(mode,dict(Flash=fw.stat().st_size, firmware=sha(fw), consumer=joint['client_SHA256']))
                receipt=work(mode)/'receipt945.json'
                if receipt.is_file():
                    link['receipt']=read(receipt)
                safety=work(mode)/'safety946.json'
                if safety.is_file():
                    link['safety']=read(safety)
                    assert link['safety']['firmware']==sha(fw) and link['safety']['consumer']==joint['client_SHA256']
                    for name in ('decode940','dispatch938'):
                        evidence=read(work(mode)/(name+'.json'))
                        assert evidence['firmware']==sha(fw)
                        link[name]=evidence
                assert ordinary_packets(folder)==ordinary_packets(ref)
                times=job_times(folder)
                assert before.keys()==times.keys()
                with patch.object(chain,'output',lambda _:rom):
                    stats=analyze(temp,mode,phase,cache,tag=tag,arm=arm)
                schedule=trace(folder)
                row=dict(gaps=stats['gaps'], total=stats['total'], preDMA=stats['early912'],
                         tail=bool(stats['tail']), capture=stats['capture_margin'], reads=schedule['sealed_reads'],
                         OBJ_first=schedule['OBJ_first'], BG=schedule['BG'], ACK=stats['ACK912'], ACK_delta=stats['ACK912']-ref_ack,
                         following=[times[k]-before[k] for k in ((909,17,1,384),(909,18,1,64))],
                         late=[(k,v-before[k]) for k,v in times.items()
                               if k[:2] not in ((912,32),(912,35)) and v>before[k]])
                assert len(row['late'])==stats['later_vs935'] and stats['other_count']==37
                if case=='cold1':
                    refbank=observe(ref)
                    result.setdefault('reference935',refbank)
                    details=observe(folder)
                    row.update(detail=details, credit_count=len(details['polls']), sixth=details['sixth_minus_head'],
                               return_delta=details['banks'][34]['returned']-refbank['banks'][34]['returned'],
                               ready_delta=details['banks'][36]['ready']-refbank['banks'][36]['ready'])
                result['cases'].setdefault(case,{})[mode]=row
                print(case,mode,link['Flash'],row['total'],row['preDMA'],row['capture'],row['reads'],
                      row['ACK_delta'],len(row['late']),row.get('sixth'),row.get('ready_delta'),flush=True)
    for mode, link in result['links'].items():
        cases=[result['cases'].get(case,{}).get(mode) for case in ('warm1','warm2','cold1','cold2')]
        if any(r is None for r in cases):
            continue
        target=cases[2]
        link['gates']=dict(flash=link['Flash']<=212992, input17=all(r['reads']==17 for r in cases[2:]),
            handoff=target['credit_count']==6 and target['sixth']>0 and target['return_delta']<=0 and target['ready_delta']<=0,
            intervals=[r['total'] for r in cases]==[13,13,15,15], capture=all(r['capture']>=0 for r in cases),
            preDMA=all(r['preDMA']==496 and r['tail'] for r in cases[2:]), other37=all(not r['late'] for r in cases),
            first_BG=target['BG']<=baseline943['BG'], followup=all(max(r['following'])<=0 for r in cases),
            order=all(r['OBJ_first'] for r in cases), ACK=all(r['ACK_delta']<0 for r in cases))
    if 'formats' in result['links']:
        cases=result['cases']
        result['format_control_identical']=all('formats' in rows and rows['formats']==rows['945']
                                               for rows in cases.values()) and len(cases)==4
    final=result['links'].get('objguard',{})
    if 'safety' in final and 'gates' in final:
        safety=final['safety']
        final['gates']['recovery']=bool(safety['menu'] and safety['CRC_rejected'] and safety['SRAM_D0_sites']==4
             and set(safety['edge'])=={'1-head','1-stop','2-head','2-stop'} and final['receipt']['stop_before_begin'])
        result['selected']='objguard' if all(final['gates'].values()) else None
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('temp',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('modes',nargs='+',choices=(*MODES,'packed'))
    args=parser.parse_args()
    args.out.write_text(json.dumps(collect(args.temp,args.modes),indent=2)+'\n',encoding='utf-8')
