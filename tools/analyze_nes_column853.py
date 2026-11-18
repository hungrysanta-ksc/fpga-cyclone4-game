"""Compare acquisitions from identical links and check every published frame against its NES pixels."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
from statistics import median

from analyze_nes_output852 import measure
from analyze_nes_input848 import CLOCK_MS
from analyze_nes_map830 import window,load
from prepare_nes_column853 import PROBE
from check_nes_game478 import sha


def packet_times(path,eligible):
    records=[bytes.fromhex(json.loads(line)[2]) for line in (path/'packets.jsonl').read_text().splitlines()]
    by_index=defaultdict(dict)
    for event in window(path):
        name=event['event']
        if name in ('load','ack','literal1814','accepted','column_write','column_service'):
            by_index[event['index']][name]=event['clock']
    counts=defaultdict(int)
    for i,p in enumerate(records,1):
        g=int.from_bytes(p[8:10],'little')
        at=int.from_bytes(p[10:12],'little')
        if g not in eligible or p[1]!=2 or p[0] not in (2,4,9) or not 2048<=at<3520: continue
        ts=by_index[i]
        counts['packets']+=1
        counts['wire_B']+=len(p)+3
        counts['load_to_ACK']+=ts['ack']-ts['load']
        if p[0]==9:
            assert 'column_write' in ts and 'column_service' in ts
            counts['write_check']+=ts['column_service']-ts['column_write']
        elif p[0]==2:
            counts['write_check']+=ts['accepted']-ts['literal1814']
        else:
            raise AssertionError('verify timing of additional opcode before inclusion')
    return {k:round(v/CLOCK_MS,4) if k in ('load_to_ACK','write_check') else v for k,v in counts.items()}


def selected_schedule(path,eligible):
    trace=window(path)
    stages=defaultdict(dict)
    for e in trace:
        g,op=e['g'],e['op']
        if e['event']=='reveal': stages[g]['display']=e['clock']
        if e['section']==2 and op in (2,4,9) and e['event']=='ack': stages[g]['map']=e['clock']
        if op==3 and e['event']=='load': stages[g]['seal']=e['clock']
    return {g:{k:round((stages[g][k]-stages[g-1]['display'])/CLOCK_MS,4)
               for k in ('map','seal','display')} for g in sorted(eligible)}


def verify_partial_stop(folder):
    canceled=(folder/'guard-stop/canceled.bin').read_bytes()
    reference=next(bytes.fromhex(json.loads(line)[2]) for line in (folder/'packets.jsonl').read_text().splitlines()
                   if bytes.fromhex(json.loads(line)[2])[:2]==bytes((9,2)))
    g=int.from_bytes(reference[8:10],'little')
    serial=int.from_bytes(reference[4:8],'little')
    bank=(serial-1)&1
    col=int.from_bytes(reference[20:22],'little')
    before=(folder/f'map-{g-2}.bin').read_bytes()
    active=(folder/f'map-{g-1}.bin').read_bytes()
    actual=canceled[bank*4096+2048:bank*4096+3520]
    expected=bytearray(before[2048:3520])
    assert expected[col:col+2]!=reference[22:24]
    expected[col:col+2]=reference[22:24]
    assert actual==expected and canceled[(1-bank)*4096:(2-bank)*4096]==active
    return dict(generation=g,target_bank=bank,partially_written_rows=1,other_rows_preserved=22,active_bank_preserved=True)


def compare(temp,experiment):
    data={}
    for clip in ('demo','opening','transition'):
        data[clip]={}
        for phase in (1,2):
            runs={};rows=None;eligible=None
            variants=[('849',''),('on',experiment),('off',experiment)]

            for name,tag in variants:
                policy=name.split('-')[-1]
                metrics,geometry,costs=measure(temp,clip,phase,policy,tag,column=True)
                run_tag=('850c0-849' if clip=='transition' else '851-849') if name=='849' else tag+'-'+policy
                linked=load(temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{run_tag}/joint.json')
                metrics['ARM_stack_clearance_B']=int(linked['observed_stack_low'],16)-int(linked['workspace_end'],16)
                assert metrics['ARM_stack_clearance_B']>=0
                metrics['first_packet_poll_clock']=linked['first_packet_poll_masterclock']
                if rows is not None: assert geometry==rows,(clip,name,phase)
                rows=geometry
                if clip=='demo' and name=='on':
                    eligible={g for (g,at,span),(op,duration) in costs.items() if op==9}
                    assert eligible and all((g,2048,1472) in costs for g in eligible)
                if clip=='demo' and eligible is not None:
                    folder=temp/f'nes-tile821-{clip}-jointmirror-p{phase}-{tag}-{policy}'
                    metrics['matched_23rows']=packet_times(folder,eligible)
                for field in ('changed_words_per_acknowledged_row','single_word_changes'): metrics.pop(field)
                runs[name]=metrics
            assert runs['on']['client']==runs['off']['client'] and runs['on']['arm']==runs['off']['arm']
            assert not runs['off']['map'].get('ref_packets',0)
            def delta(left,right):
                a,b=runs[left],runs[right]
                return dict(VBlank=b['display_VBlanks']-a['display_VBlanks'],
                            final_ACK_ms=round((b['final_ACK']-a['final_ACK'])/CLOCK_MS,4))
            data[clip][phase]=dict(runs=runs,on_vs_849=delta('849','on'),on_vs_off=delta('off','on'))
            fixture=temp/('nes-trans850-c0' if clip=='transition' else 'nes-comparison851')/clip/clip/'work.json'
            sources=[w['source_frame'] for w in load(fixture)][2:]
            assert len(sources)==len(runs['on']['gaps'])==len(runs['849']['gaps'])
            data[clip][phase]['changed_intervals_versus_849']=[
                [source,old,new] for source,old,new in zip(sources,runs['849']['gaps'],runs['on']['gaps']) if old!=new]
            if eligible:
                assert runs['on']['matched_23rows']['packets']==len(eligible)
                data[clip][phase]['eligible_generations']=sorted(eligible)
                paired={k:selected_schedule(temp/f'nes-tile821-demo-jointmirror-p{phase}-{experiment}-{k}',eligible)
                        for k in ('on','off')}
                data[clip][phase]['on_minus_off_median_ms_from_previous_display']={
                    k:round(median(paired['on'][g][k]-paired['off'][g][k] for g in eligible),4)
                    for k in ('map','seal','display')}
                sample={}
                for tag in ('853c',experiment):
                    path=temp/f'nes-tile821-demo-jointmirror-p{phase}-{tag}-on'
                    sample[tag]=packet_times(path,{914})
                    assert sample[tag]['packets']==1
                data[clip][phase]['first_column_scalar_and_grouped']=sample
    fw=PROBE/('link3' if experiment=='853d' else 'link5')/'src/obj-nes-100/firmware.stm'
    assert sha(fw)==runs['on']['arm'] and sha(PROBE/'fast/sink165.sfc')==runs['on']['client']
    data['resources']=dict(flash_B=fw.stat().st_size,ROM_free_B=load(PROBE/'fast/build.json')['physical_free_B'])
    data['guards']={case:load(PROBE/f'{experiment}-guard-{case}.json') for case in
                    ('cold','base','length','range','column','damage','prefix','stop','restart','arm-stop','arm-identity')}
    data['partial_stop']=verify_partial_stop(temp/f'nes-tile821-demo-jointmirror-p1-{experiment}-on')
    menu=load(PROBE/f'{experiment}-menu.json')
    base=load(PROBE/f'{experiment}-base/result.json')
    assert menu['firmware']==base['firmware_sha256']==sha(fw) and base['base_restored'] and base['safe_return']
    data['menu']=menu['rows']
    data['modeled_base_return']=base['scope']
    return data


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    a=p.parse_args()
    final=compare(a.temp,'853e')
    first=compare(a.temp,'853d')
    final['eager_comparison']={
        clip:{phase:{'intervals':row['runs']['on']['display_VBlanks'],
                     'on_vs_849':row['on_vs_849'],'on_vs_off':row['on_vs_off']}
              for phase,row in first[clip].items()} for clip in ('opening','transition','demo')}
    final['eager_resources']=first['resources']
    a.out.write_text(json.dumps(final,indent=2)+'\n')
