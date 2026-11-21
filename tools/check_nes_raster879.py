"""Check the fixed-prefix receiver experiment separately from the full ARM build."""
import argparse
import json
from pathlib import Path

from analyze_nes_credit876 import verified_commits
from analyze_nes_deadline875 import STRIDE, analyze, points
from analyze_nes_map830 import load
from check_nes_retire878 import trace, verify_retire_order
from check_nes_table877 import table_packets
from check_nes_scroll874 import receipt


def matched_output(reference, candidate):
    joint = load(candidate / 'joint.json')
    assert joint['passed'] and verified_commits(candidate) == joint['commits']
    assert load(candidate / 'ack861.json')['loads'] == load(reference / 'ack861.json')['loads']
    assert table_packets(candidate) == table_packets(reference)
    for frame in joint['frames']:
        gen = frame['generation']
        def view(folder):
            rgb = (folder / f'frame-{gen}.rgb').read_bytes()
            return rgb[7*STRIDE:231*STRIDE], (folder / f'map-{gen}.bin').read_bytes()
        assert view(reference) == view(candidate), gen
    return verify_retire_order(candidate)


def block_profile(row, marks):
    data, end, commit = row['input_service'][-3:]
    assert [b['wire_B'] for b in (data, end, commit)] == [120, 27, 15]
    stages = ['crc_begin', 'crc_end', 'packet_begin', 'run0_begin', 'run0_checked',
              'run0_end', 'run185_begin', 'run185_checked', 'run185_end', 'meta_begin', 'packet_end']
    clock = {name: round(marks[name]['clock']) for name in stages}
    clock.update(D1_end=data['D1_end'], D2_start=data['D2_start'], D2_end=data['D2_end'],
                 END_D1_end=end['D1_end'], END_D2_end=end['D2_end'], COMMIT_D2_end=commit['D2_end'])
    assert list(clock[k] for k in ['D1_end', *stages, 'D2_start', 'D2_end']) == sorted(
        clock[k] for k in ['D1_end', *stages, 'D2_start', 'D2_end'])
    spans = [('crc_begin','crc_end'), ('run0_checked','run0_end'), ('run185_checked','run185_end'),
             ('meta_begin','packet_end'), ('packet_begin','packet_end'), ('D1_end','D2_start'),
             ('D2_start','D2_end')]
    return dict(clock=clock, durations={a+'..'+b:clock[b]-clock[a] for a,b in spans},
                receiver_sha256=marks['packet_end']['state_sha256'])


def summary(row):
    return {k:row[k] for k in ('map950','gap950','show950','display950_ACK','last_data_D2','checked_E0_950','old_EA','D3','commit_D2',
                                'commit_minus_874_edge','display952','gap952','dense60','ACK','E0')}


def ack_polls(path, row):
    start = row['input_service'][-3]['D1_end']
    end = row['checked_E0_950']
    return [dict(start=round(e['start']),end=round(e['clock']),reply=e['reply'])
            for e in load(path/'events.json') if e.get('opcode')=='0xe0'
            and start<round(e['clock'])<=end]


def overlap_generations(path, sender):
    """Find other captured inputs that would take a generic post-SEAL fast path."""
    from collections import Counter
    seen=Counter()
    seals={}
    eligible=Counter()
    for e in load(path/'events.json'):
        g=e['generation'] if 'generation' in e else None
        if e.get('opcode')=='0xe1' and e['packet_opcode']==3:
            seals[g]=e['clock']
        if e.get('opcode')!='0xd1':continue
        new=e['input_generation']
        packet=bytes.fromhex(sender[str(new)][seen[new]]['wire'])
        seen[new]+=1
        assert len(packet)+3==e['bytes']
        if new==g or e['start']<seals.get(g,float('inf')):continue
        pos=0
        while pos<len(packet):
            tag=int.from_bytes(packet[pos:pos+2],'big')
            if tag==65535:break  # packed geometry occupies the rest of this block
            kind=tag>>13
            if tag&0xff00==0xfc00:eligible[new]+=1
            width=8 if kind==0 and tag&0x1000 else (2,1,7,4,7,1,2,8)[kind]
            pos+=4+width
            assert pos<=len(packet)
    return dict(sorted(eligible.items()))


def report(temp):
    root = Path(__file__).resolve().parents[2]
    work = root/'probes/nes-raster879'
    static = analyze(temp, root, work, '879-static')
    assert static['guards']['source_tag'] == '879-static'
    retire = load(work/'retire-guards.json')
    assert retire['ARM'] == static['ARM']
    static['retire_cases'] = len(retire['cases'])
    static['receiver951'] = load(work/'blocks951.json')
    for clip in ('opening', 'transition', 'demo'):
        for ph in (1,2):
            folder = temp/f'nes-tile821-{clip}-jointmirror-p{ph}-879-static'
            static['scenes'][f'{clip}-{ph}']['verified_retire_order'] = verify_retire_order(folder)
    result = dict(static=static, phases={})
    for ph in (1,2):
        def folder(tag):
            return temp/f'nes-tile821-demo-jointmirror-p{ph}-{tag}'
        edge = points(folder('874-drain'))['previous_capture_edge']
        ref = trace(folder('878-once'),edge)
        phase = dict(edge=edge, reference=summary(ref), MMC872=summary(trace(folder('872-final'),edge)))
        phase['post_SEAL_raster_runs'] = overlap_generations(folder('878-once'),
            load(temp/'nes-ack861/sender-demo/sender.json'))
        for tag in ('878-once','879-static'):
            rec=receipt(folder(tag),950)
            phase.setdefault('map_to_scroll_E0_flags',{})[tag]=[
                bytes.fromhex(e['reply'])[2] for e in load(folder(tag)/'events.json')
                if e.get('opcode')=='0xe0' and rec['map_E1_end']<=e['start']
                and e['clock']<=rec['scroll_E1_start']]
        for mode in ('original', 'run', 'retry96'):
            candidate = folder('879-'+mode)
            row = trace(candidate,edge)
            count = matched_output(folder('878-once'), candidate)
            cutoff = ref['input_service'][-3]['D1_end']
            def prefix(path):
                return [e for e in load(path/'events.json') if e.get('opcode') and round(e['clock'])<=cutoff]
            assert prefix(folder('878-once')) == prefix(candidate)
            if mode == 'original':
                assert row == ref
            phase[mode] = dict(timeline=summary(row), releases=count,
                               interval_changes_vs_878={g:[ref['intervals'][g],span]
                                   for g,span in row['intervals'].items() if ref['intervals'][g]!=span},
                               E0_polls=ack_polls(candidate,row),
                               profile=block_profile(row,load(work/f'{mode}-p{ph}.json')))
        assert len({phase[m]['profile']['receiver_sha256'] for m in ('original','run','retry96')})==1
        assert phase['run']['profile']['durations']==phase['retry96']['profile']['durations']
        combined=phase['retry96']['timeline']
        phase['fixed_gates']={
            'upstream_950':all(combined[k]==ref[k] for k in ('map950','show950','gap950'))
                           and bool(ref['map950']) and ref['gap950']==3,
            'first_capture':combined['commit_minus_874_edge']<0,
            'previous_952_VBlank':combined['display952']['frame']==(147 if ph==1 else 148)
                                  and combined['display952']['line']<=246 and combined['gap952']==2,
            'demo_vs_MMC872':all(combined[k]<phase['MMC872'][k] for k in ('dense60','ACK','E0'))}
        linked = trace(folder('879-static'),edge,work,ph)
        phase['static'] = dict(summary(linked),validated_END=linked['validated_END'],
                               END_minus_reveal=linked['END_minus_reveal'])
        static['gates'][f'demo-{ph}_publish'] = phase['static']['show950']['clock'] <= ref['show950']['clock']
        static['gates'][f'demo-{ph}_capture'] = phase['static']['commit_minus_874_edge'] < 0
        result['phases'][ph] = phase
    static['passed'] = all(static['gates'].values())
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    args = p.parse_args()
    args.out.write_text(json.dumps(report(args.temp),indent=2)+'\n')
