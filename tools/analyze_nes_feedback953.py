"""Compare feedback on the ARM SPI wire with the subsequent board and PPU traces."""
import csv
import json
import sys
from pathlib import Path

from analyze_nes_chr951 import (logtext, ROOT, MASTER, RELEASE, ROM, Calendar, coverage, directory,
                                inspect, port_log, read, sha, timing)
from analyze_nes_companion952 import preceding
from nes_feedback953 import BASE
from nes_companion952 import project
from test_nes_banks557 import host_after


def spi(row):
    return [round(row['start']), row['opcode'], row.get('packet_opcode')]


def feedback_events(folder, original):
    log=folder/'feedback953.jsonl'
    entries=[json.loads(s) for s in log.read_text().splitlines()] if log.exists() else []
    before=read(original/'events.json')
    after=read(folder/'events.json')
    results=[]
    for gen, clock, model, rtl in entries:
        def bus(events):
            rows=[e for e in events if e.get('generation')==gen and e.get('event')=='SPI']
            # Match a moved transaction to its nearest 952 E8 in the same lease.
            i=min((i for i,e in enumerate(rows) if e['opcode']=='0xe8'),
                  key=lambda i:abs(round(host_after(rows[i]['start']+7.5*MASTER/2625000,3))-clock))
            jobs=(json.loads(s) for s in (folder/'producer.jsonl').read_text().splitlines())
            token=next(j['token'] for j in reversed(list(jobs)) if j['generation']==gen and j['kind']==1)
            index=next(j for j in range(i,len(rows)) if rows[j]['opcode']=='0xe8'
                       and rows[j]['reply'][12:14]=='01'
                       and int.from_bytes(bytes.fromhex(rows[j]['reply'])[14:18],'little')==token)
            bulk=next(e for e in rows[index+1:] if e['opcode']=='0xe1' and e['packet_opcode']==7)
            return dict(sample=round(host_after(rows[i]['start']+7.5*MASTER/2625000,3)),
                        response=rows[i]['reply'],next_spi=spi(rows[i+1]),descriptor_E8=spi(rows[index]),
                        tile_E1=spi(bulk))
        a,b=bus(before),bus(after)
        assert b['sample']==clock and b['response']==rtl
        results.append(dict(g=gen,clock=clock,model=model,rtl=rtl,before=a,after=b,
                            tile_E1_delta=b['tile_E1'][0]-a['tile_E1'][0]))
    return results


def compare(temp,tag,p,cache):
    folder=directory(temp,p,tag,cache)
    original=directory(temp,p,BASE,cache)
    cal=Calendar(temp/'nes-service509-rom03')
    m,q=inspect(folder,RELEASE,cal)
    old,ref=inspect(original,RELEASE,cal)
    assert all(q[k]==ref[k] for k in ('map','tiles','colors','RGB','sections'))
    case=cache+str(p)
    baseline=read(ROOT/'analysis/header950-results.json')['cases'][case]['bound']
    margin=baseline['final_D2']+baseline['capture_line_margin']-m['capture_D2']
    gain=baseline['final_ACK']+baseline['ACK_advance_vs935']-m['final_ACK']
    blocks=timing(folder)['returned_before_show']
    initial=lambda d:[e for e in read(d/'events.json') if e.get('generation',999)<=907]
    assert initial(folder)==initial(original)
    for g in range(905,908):
        name=f'e9wire914-{g}.jsonl'
        assert sha(folder/name)==sha(original/name)
    same=coverage(preceding(m)).keys()==coverage(preceding(old)).keys()
    stages={}
    for g in (908,909,910,911,912):
        def select(a):
            return {k:a['stages'][g][k] for k in ('first_E9','last_return','commit_D2','SEAL','DMA','show','ACK','frame','line')}
        a,b=select(old),select(m)
        stages[g]=dict(original=a,feedback=b,delta={k:b[k]-a[k] for k in a})
    def display_wait(d,g):
        with (d/'window.csv').open() as f:
            return {r['event']:[int(r[k]) for k in ('clock','frame','line')] for r in csv.DictReader(f)
                    if r['g']==str(g) and r['op']=='3' and r['event'] in
                    ('load','coverage212','upload165_entry','wait169','wait_return_5781','reveal')}
    def target_dma(d,g,count):
        with (d/'seal528.csv').open() as f:
            row,=[r for r in csv.DictReader(f) if r['g']==str(g) and r['event']=='dma'
                  and r['port']=='24' and r['bytes']==str(count)]
        return {k:int(row[k]) for k in ('clock','line','h','port','dst','bytes')}
    for g,count in (((908,544),(910,320)) if cache=='cold' else ()):
        a,b=(target_dma(d,g,count) for d in (original,folder))
        assert a['dst']==b['dst']
        stages[g]['wait_before']=display_wait(original,g)
        stages[g]['wait_after']=display_wait(folder,g)
        stages[g]['OBJ_DMA']=dict(before=a,after=b,delta_clocks=b['clock']-a['clock'])
    def dma_trace(d):
        with (d/'window.csv').open() as f:
            return [[int(r[k]) for k in ('g','value','clock','frame','line')] for r in csv.DictReader(f)
                    if r['event']=='ppu_dma' and r['g'] in ('908','910','912')]
    rtl={}
    for g in ((908,909,910,911,912) if cache=='cold' else (909,912)):
        d=folder/f'gen{g}' if g!=912 else folder
        path=d/'port952-checked.log'
        if path.exists():
            r=port_log(path)
            rtl[g]={k:r[k] for k in ('polls','log','error','chunks_bytes_hits_grants','first_E8_mismatch')}
    gate=(blocks==17 and margin>=0 and m['total']==(13 if cache=='warm' else 14)
          and m['prior_blank_B']==496 and same and m['tail_grant'] and gain>0)
    return dict(blocks=blocks,margin_us=round(margin*1e6/MASTER,3),margin_clocks=margin,
                prior_DMA=m['prior_blank_B'],same_DMA_ranges=same,tail_grant=m['tail_grant'],
                gaps=m['gaps'],intervals=m['total'],ack=m['final_ACK'],ack_delta_952=m['final_ACK']-old['final_ACK'],
                gain_vs935_ms=round(gain*1000/MASTER,6),linked_pass=gate,stages=stages,rtl=rtl,
                feedback=feedback_events(folder,original),DMA=dict(original=dma_trace(original),feedback=dma_trace(folder)),
                joint_sha=sha(folder/'joint.json'))


if __name__=='__main__':
    temp=Path(sys.argv[1])
    selected=sys.argv[2]
    cases={c+str(p):compare(temp,('953feedback' if c=='warm' or p==1 else selected),p,c)
           for c in ('warm','cold') for p in (1,2)}
    safety=temp/'nes-safety953'
    ref=read(ROOT/'analysis/companion952-results.json')['safety']
    assert read(safety/'proof/base/result.json')['base_restored'] and read(safety/'proof/menu.json')['rows']['normal']['released']
    assert read(safety/'proof/menu.json')['firmware']==ref['firmware'] and read(safety/'consumer.json')==ref['STOP']
    assert read(safety/'proof/timer.json')['passed'] and read(safety/'proof/sram.json')['cases']['normal']['checked_retire']
    loader=read(safety/'proof/loader.json')['cases']
    assert loader['original']['program'] and not loader['damaged']['program']
    assert sha(ROM/'sink165.sfc')==ref['consumer']
    all_match=all(len(c['rtl'])==(2 if name.startswith('warm') else 5)
        and all(r['polls'] and r['polls'][0]>0 and r['polls'][1]==0 and r['error'] is None
                and r['chunks_bytes_hits_grants'] for r in c['rtl'].values()) for name,c in cases.items())
    board=project(temp,'checked')
    previous_board=read(ROOT/'analysis/companion952-results.json')['variants']['checkedrows']['board']
    assert sha(board/'output_files/board.sof')==previous_board['reports']['board.sof']
    guards={}
    for file,marker in [('guards951.log','PASS914 checked'),('row951.log','PASS951 lease'),('row952.log','PASS952 16 actual')]:
        assert marker in logtext(board/file)
        guards[file]=sha(board/file)
    shots=[[e['g'] for e in cases[k]['feedback']] for k in ('warm1','warm2','cold1','cold2')]
    assert shots==[[],[],[908],[908,910]]
    sampled=sum(v['polls'][0] for c in cases.values() for v in c['rtl'].values())
    result=dict(board_sof=previous_board['reports']['board.sof'],board_guards=guards,E8_samples=sampled,
                verified=dict(schedule=all(c['linked_pass'] for c in cases.values()),all_resampled_E8=all_match),
                cases=cases,physical=False,firmware=ref['firmware'],consumer=ref['consumer'],master_Hz=MASTER,
                selected=selected,isolated_910=compare(temp,'953only910',2,'cold'),
                initial_phase2=compare(temp,'953feedback',2,'cold'),
                safety={str(f.relative_to(safety)):sha(f) for f in [*sorted((safety/'proof').rglob('*.json')),safety/'consumer.json']})
    (ROOT/'analysis/feedback953-results.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    assert all(result['verified'].values()),result['verified']
