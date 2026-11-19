"""Locate the first lost display deadline and bind it to the previous input pop."""
import argparse
import json
import sys
from pathlib import Path

from check_nes_progress870 import report
from analyze_nes_map830 import load, window


def milestones(folder):
    events=load(folder/'events.json')
    trace=window(folder)
    pops=[e for e in events if e.get('opcode')=='0xd2']
    grants=[e for e in events if e.get('opcode')=='0xd3']
    ready={e['generation']:e['capture_ready'] for e in events if e['event']=='source_begin'}
    rows={}
    for show in (e for e in trace if e['event']=='reveal'):
        g=show['g']
        frame=[e for e in trace if e['g']==g]
        seal=next(e for e in frame if e['event']=='load' and e['op']==3)
        maps=[e for e in frame if e['event']=='ack' and e['section']==2]
        earlier=[e for e in grants if e['generation']==g-1]
        pop=None
        commit_bus=None
        if earlier:
            grant=earlier[-1]
            # Early inbox polls can carry the previous output generation in
            # the trace. Correlate the COMMIT pop by bus order following D3.
            pop=next(e for e in pops if e['start']>=grant['clock'])
            commit_bus=[e['opcode'] for e in events if e.get('event')=='SPI'
                        and grant['start']<=e['start'] and e['clock']<=pop['clock']]
        rows[g]=dict(capture_ready=ready[g], previous_COMMIT_pop=round(pop['clock']) if pop else None,
                     previous_D3_to_pop_bus=commit_bus,
                     last_map_return=maps[-1]['clock'] if maps else None,
                     seal_accept=seal['clock'], seal_vblank_line=[seal['frame'],seal['line']],
                     reveal=show['clock'], reveal_vblank=show['frame'])
    return rows


def review(temp,work,tag):
    result=report(temp,work,tag)
    result['input_guards']=load(work/'input-guards.json')
    assert result['input_guards']['firmware']==result['ARM']
    timing={}
    for scene in ('opening','transition'):
        for ph in (1,2):
            prefix=f'nes-tile821-{scene}-jointmirror-p{ph}-'
            runs={v:milestones(temp/(prefix+v)) for v in ('866-on','870-g',tag)}
            base,old=runs['866-on'],runs['870-g']
            generations=list(base)
            first=next(g for g in generations if old[g]['reveal_vblank']>base[g]['reveal_vblank'])
            first_gap=next(g for prev,g in zip(generations[1:],generations[2:])
                           if old[g]['reveal_vblank']-old[prev]['reveal_vblank']>
                              base[g]['reveal_vblank']-base[prev]['reveal_vblank'])
            late=next(g for g in generations if old[g]['capture_ready']>base[g]['capture_ready'])
            fixture='nes-comparison851' if scene=='opening' else 'nes-trans850-c0'
            source={r['g']:r['source_frame'] for r in load(temp/fixture/scene/scene/'work.json')}
            rows={}
            for g in sorted({generations[1],first_gap,first,late,first-1,generations[-1]}):
                target=base[g]['capture_ready']-240*341*4
                rows[g]={'source_frame':source[g]}
                for v,frames in runs.items():
                    row=frames[g].copy()
                    if row['previous_COMMIT_pop'] is not None:
                        row['pop_vs_reference_capture_start']=row['previous_COMMIT_pop']-target
                    rows[g][v]=row
            later=[dict(g=g,source_frame=source[g],extra=runs[tag][g]['reveal_vblank']-base[g]['reveal_vblank'])
                   for g in generations if runs[tag][g]['reveal_vblank']>base[g]['reveal_vblank']]
            timing[f'{scene}-{ph}']=dict(first_late_publication=first,first_longer_interval=first_gap,
                                          first_late_capture=late,candidate_later_publications=later,rows=rows)
    result['deadlines']=timing
    scenes=result['scenes']
    for scene in ('opening','transition'):
        result['gate'][scene+'_intervals']=all(
            scenes[f'{scene}-{i}']['candidate']['after_two_VBlanks']<=
            scenes[f'{scene}-{i}']['reference']['after_two_VBlanks'] for i in (1,2))
        first_and_last=[]
        for phase in (1,2):
            clip=timing[f'{scene}-{phase}']
            rows=clip['rows']
            for generation in (clip['first_late_publication'],max(rows)):
                row=rows[generation]
                first_and_last.append(row[tag]['reveal_vblank']<=row['866-on']['reveal_vblank'])
        result['gate'][scene+'_first_and_last']=all(first_and_last)
    result['gate']['dense_141']=all(scenes[f'demo-{i}']['candidate']['after_two_VBlanks']<=141 for i in (1,2))
    result['gate']['936_two']=all(result['generation936'][i][tag]['gap']<=2 for i in (1,2))
    result['gate']['opening_759']=all(
        scenes[f'opening-{i}']['candidate']['opening_marks']['966'][0] <=
        scenes[f'opening-{i}']['reference']['opening_marks']['966'][0] for i in (1,2))
    result['meets_request']=all(result['gate'][k] for k in (
        'flash','opening_703','opening_759','opening_intervals','transition_intervals',
        'opening_first_and_last','transition_first_and_last','dense_141','936_two','dense_intervals_and_ACK'))
    return result


def summarize(probes,variants,detail):
    controls={}
    for variant in variants:
        row=load(probes/('nes-capture871-'+variant)/'summary.json')
        controls[variant]=dict(ARM=row['ARM'],flash_B=row['flash_B'],gate=row['gate'],
                               meets_request=row['meets_request'],scenes={})
        for clip,v in row['scenes'].items():
            controls[variant]['scenes'][clip]={k:v['candidate'][k] for k in
                ('after_two_VBlanks','last_ACK','opening_marks','warm_map_wire_B','observed_stack_clearance_B')}
    return dict(controls=controls, selected_detail=detail,
                detail=load(probes/('nes-capture871-'+detail)/'summary.json'))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    if sys.argv[1:2]==['summary']:
        p.add_argument('probes',type=Path)
        p.add_argument('detail')
        p.add_argument('output',type=Path)
        p.add_argument('variants',nargs='+')
        a=p.parse_args(sys.argv[2:])
        result=summarize(a.probes,a.variants,a.detail)
    else:
        p.add_argument('temp',type=Path)
        p.add_argument('work',type=Path)
        p.add_argument('tag')
        p.add_argument('output',type=Path)
        a=p.parse_args()
        result=review(a.temp,a.work,a.tag)
    a.output.write_text(json.dumps(result,indent=2)+'\n')
