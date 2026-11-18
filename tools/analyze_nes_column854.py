"""Audit identical dot-zero captures and compare complete reveal and receipt schedules."""
import argparse
import json
from pathlib import Path
from statistics import mean,median

from analyze_nes_map830 import load,window
from analyze_nes_column853 import selected_schedule
from analyze_nes_output852 import measure,CLOCK_MS
from prepare_nes_column854 import ROOT


def matched(path,eligible):
    # Collect physical load and ACK for each selected 1472-byte rectangle,
    # including all eight ordinary packets when the command is disabled.
    packets=[bytes.fromhex(json.loads(s)[2]) for s in (path/'packets.jsonl').read_text().splitlines()]
    spans={}
    ticks={}
    for e in window(path):
        if e['event'] in ('load','ack'):
            ticks[e['index'],e['event']]=e['clock']
    for i,b in enumerate(packets,1):
        g=int.from_bytes(b[8:10],'little')
        if g not in eligible or b[1]!=2 or b[0] not in (2,4,9):continue
        at,n,expanded=(int.from_bytes(b[j:j+2],'little') for j in (10,12,14))
        if 2048<=at<3520:
            span=1472 if b[0]==9 else n if b[0]==2 else expanded
            spans.setdefault(g,[]).append((at,span,ticks[i,'ack']-ticks[i,'load']))
    out={}
    for g in eligible:
        cursor=2048
        for at,span,_ in sorted(spans[g]):
            assert at==cursor
            cursor+=span
        assert cursor==3520
        out[g]=round(sum(t for _,_,t in spans[g])/CLOCK_MS,5)
    return out


def analyze(temp,variant,clips):
    prior=load(Path(__file__).resolve().parents[1]/'analysis/column853-results.json')
    data={}
    for clip in clips:
        data[clip]={}
        for p in (1,2):
            by_policy={};shape=None
            for policy,tag in [('849',''),('off','854'+variant),('on','854'+variant)]:
                metrics,geometry,_=measure(temp,clip,p,policy,tag,column=True)
                if shape is not None:assert shape==geometry
                shape=geometry
                for key in ('changed_words_per_acknowledged_row','single_word_changes'):metrics.pop(key)
                suffix=(('850c0-849' if clip=='transition' else '851-849') if policy=='849' else tag+'-'+policy)
                path=temp/f'nes-tile821-{clip}-jointmirror-p{p}-{suffix}'
                j=load(path/'joint.json')
                metrics['first_poll']=j['first_packet_poll_masterclock']
                metrics['stack_clearance_B']=int(j['observed_stack_low'],16)-int(j['workspace_end'],16)
                assert metrics['stack_clearance_B']>=0
                if clip=='demo':
                    eligible=prior[clip][str(p)]['eligible_generations']
                    if policy=='on':assert metrics['map']['ref_packets']==len(eligible)
                    metrics['matched_23rows']=matched(path,eligible)
                by_policy[policy]=metrics
            on,off,ref=[by_policy[k] for k in ('on','off','849')]
            assert on['arm']==off['arm'] and on['client']==off['client'] and not off['map'].get('ref_packets',0)
            def diff(x):
                return dict(VBlanks=on['display_VBlanks']-x['display_VBlanks'],
                            ACK_ms=round((on['final_ACK']-x['final_ACK'])/CLOCK_MS,5))
            row=dict(runs=by_policy,on_minus_off=diff(off),on_minus_849=diff(ref))
            if clip=='demo':
                sample={}
                path=temp/f'nes-tile821-demo-jointmirror-p{p}-854{variant}-on'
                trace=window(path)
                for g in (921,934,944,959):
                    seal=[e for e in trace if e['g']==g and e['op']==3]
                    sample[g]=[[e['event'],e['frame'],e['line'],e['clock'],e['value']]
                               for e in seal if e['event'] in ('load','coverage212','upload165_entry','wait169',
                                         'wait_return_5781','ppu_dma','reveal','ack')]
                row['seal_trace']=sample
                schedules={pol:selected_schedule(temp/f'nes-tile821-demo-jointmirror-p{p}-{suffix}',eligible)
                           for pol,suffix in [('on','854'+variant+'-on'),('off','854'+variant+'-off'),('849','851-849')]}
                row['eligible_median_ms_from_previous_display']={pol:{key:round(median(v[key] for v in seq.values()),5)
                    for key in ('map','seal','display')} for pol,seq in schedules.items()}
            if clip=='demo':
                old_ms=matched(temp/f'nes-tile821-demo-jointmirror-p{p}-853e-on',eligible)
                gains=[old_ms[g]-on['matched_23rows'][g] for g in eligible]
                row['reduction_from_853_ms']=dict(minimum=round(min(gains),5),mean=round(mean(gains),5),
                    maximum=round(max(gains),5),meeting_2_3=sum(x>=2.3 for x in gains),bundles=len(gains))
            data[clip][p]=row
    return data


def opening_cross(temp):
    rows={}
    for key,policy,tag in [('849/815','849',''),('849/853','off','854-arm849'),
                           ('853/815','off','854-rom815'),('853/853','on','853e'),
                           ('849/815-delay','off','854-delay849'),('853/815-delay','off','854-delay853')]:
        m,_,_=measure(temp,'opening',1,policy,tag,column=True)
        suffix='851-849' if policy=='849' else tag+'-'+policy
        j=load(temp/f'nes-tile821-opening-jointmirror-p1-{suffix}/joint.json')
        rows[key]=dict(first_poll=j['first_packet_poll_masterclock'],intervals=m['display_VBlanks'],
                       final_ACK=m['final_ACK'],eligible=m['map'].get('ref_packets',0))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('temp',type=Path);p.add_argument('variant');p.add_argument('output',type=Path)
    p.add_argument('--final',action='store_true')
    p.add_argument('--clips',nargs='+',default=['demo','opening','transition'])
    a=p.parse_args()
    data=analyze(a.temp,a.variant,a.clips)
    data['opening_phase_1_cross']=opening_cross(a.temp)
    data['client']=load(ROOT/f'client-{a.variant}/build.json')
    if a.final:
        from nes_raw506 import sha
        assert a.variant in ('d','e') and set(a.clips)=={'opening','transition','demo'}
        data['client']={k:data['client'][k] for k in ('body_bytes','physical_ROM_B','prefix_B','loader_B','encoded_B','physical_free_B')}
        firmware=ROOT/'link-b/src/obj-nes-100/firmware.stm'
        data['ARM_flash_B']=firmware.stat().st_size
        assert data['ARM_flash_B']<=212992
        data['variant']='854'+a.variant.upper()
        data['scope']='Dot-zero adjacent source captures and actual linked Cortex-M4 and 65816 code; modeled IRQ dispatch, shared SPI, ROM calendar and peripheral timing. No physical play or new board STA.'
        data['references']={k:sha(Path(__file__).resolve().parents[1]/'analysis'/k) for k in ('comparison851-results.json','column853-results.json')}
        data['boot']=load(a.temp/f'nes-boot854{a.variant}/result.json')
        data['guards']={k:load(ROOT/f'854{a.variant}-guard-{k}.json') for k in (
            'cold','base','length','range','column','damage','omitted','overlap','tail-last','prefix','stop','late-stop','restart','arm-stop','arm-identity')}
        menu=load(ROOT/'b-menu.json');base=load(ROOT/'b-base/result.json')
        assert base['firmware_sha256']==menu['firmware']==sha(firmware)==data['demo'][1]['runs']['on']['arm']
        assert base['safe_return'] and base['base_restored']
        data['menu']=menu['rows'];data['base']=base['scope']
        data['intermediate']={}
        for variant in 'abcde'[:'abcde'.index(a.variant)]:
            v=load(ROOT/f'analysis-{variant}.json')
            data['intermediate'][variant]={clip:{p:{'VBlanks':r['runs']['on']['display_VBlanks'],
                'final_ACK':r['runs']['on']['final_ACK'],'off_VBlanks':r['runs']['off']['display_VBlanks'],
                'matched':r.get('reduction_from_853_ms')} for p,r in v[clip].items()} for clip in a.clips}
    a.output.write_text(json.dumps(data,indent=2)+'\n')
