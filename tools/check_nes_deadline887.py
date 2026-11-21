"""Compare ACK snapshots, capture lines and whole-scene displays on matched input."""
import argparse
import csv
import json
from pathlib import Path

from analyze_nes_deadline875 import arm_ack
from analyze_nes_map830 import load, window
from analyze_nes_transition850 import STRIDE
from check_nes_oam882 import capture
from check_nes_retire878 import verify_retire_order
from check_nes_strip869 import digest, metrics
from prepare_nes_deadline887 import BASE, WORK


def breakdown(path, gen, target):
    cap = capture(path, gen)
    ack = cap['prior_display_ACK']
    transactions = [e for e in load(path/'events.json') if e.get('opcode')
                    and ack-6000 <= e['clock'] <= cap['D2']+1]
    return dict(**cap, target=target, margin=target-cap['D2'],
                ack_to_valid_E0=cap['valid_E0']-ack,
                valid_E0_to_last_D2=cap['D2']-cap['valid_E0'],
                transactions=[[e['opcode'],round(e['start']-ack),round(e['clock']-ack)]
                              for e in transactions])


def evaluate(temp):
    client = digest(WORK/'client02/sink165.sfc')
    fw = WORK/'link-credit/src/obj-nes-100/firmware.stm'
    guard = load(WORK/'retire.json')
    menu = load(WORK/'menu.json')
    cold_stop = load(WORK/'guards.json')
    assert guard['ARM'] == menu['firmware'] == digest(fw)
    assert cold_stop['client'] == client and menu['rows']['normal']['released']
    assert fw.stat().st_size <= 212992
    assert client == digest(BASE.parent/'nes-coverage886/client02/sink165.sfc')
    result = dict(firmware=digest(fw), client=client, flash=fw.stat().st_size,
                  menu=menu, retire=guard, cold_stop=cold_stop, scenes={})
    for clip, gen in [('opening',918), ('transition',None), ('demo',947)]:
        rows = result['scenes'][clip] = {}
        for phase in (1,2):
            prefix = f'nes-tile821-{clip}-jointmirror-p{phase}-'
            original = temp/(prefix+'886-static')
            original_run = load(original/'joint.json')
            tags = ['886-static','887-seal']
            if phase == 2 and gen is not None:
                tags.append('887-local')
            if gen is not None:
                target = capture(temp/(prefix+'883-shared'),gen)['ready'] - 240*341*4
            for tag in tags:
                d = temp/(prefix+tag)
                run = load(d/'joint.json')
                assert run['client_SHA256'] == client and run['parameters'] == original_run['parameters']
                assert run['firmware_SHA256'] == (digest(fw) if tag == '887-seal' else original_run['firmware_SHA256'])
                assert run['passed'] and verify_retire_order(d) == run['commits'] == original_run['commits']
                for f in original_run['frames']:
                    g = f['generation']
                    a,b = [(x/f'frame-{g}.rgb').read_bytes() for x in (d,original)]
                    assert len(a) == len(b) and a[7*STRIDE:231*STRIDE] == b[7*STRIDE:231*STRIDE]
                    assert (d/f'map-{g}.bin').read_bytes() == (original/f'map-{g}.bin').read_bytes()
                m = metrics(d)
                r = rows[f'{phase}-{tag}'] = {k:m[k] for k in
                    ('after_two_VBlanks','last_ACK','opening_marks','held_blank_VBlanks','all_wire_B')}
                r['final_E0'] = arm_ack(d,m['last_ACK'])
                r['E0_transactions'] = run['wire_B']['0xe0']//20
                r['wire_bytes'] = sum(run['wire_B'].values())
                def show(p):
                    return [(e['g'],e['frame']) for e in window(p) if e['event']=='reveal']
                shows, base_shows = show(d), show(original)
                r['changed_intervals'] = []
                for i in range(2,len(shows)):
                    g,new_end = shows[i]
                    previous = base_shows[i][1] - base_shows[i-1][1]
                    actual = new_end - shows[i-1][1]
                    if previous != actual:
                        r['changed_intervals'].append([g,previous,actual])
                if gen is not None:
                    r['capture'] = breakdown(d,gen,target)
                if tag == '887-local':
                    first = load(d/'calls887.json')[0]
                    def prefix_events(p):
                        return [e for e in load(p/'events.json') if e.get('opcode') and e['clock']<=first]
                    before = prefix_events(original)
                    assert before and before == prefix_events(d)
                    r['identical_prior_SPI'] = len(before)
                if clip == 'demo':
                    assert load(d/'ack861.json')['loads'] == load(original/'ack861.json')['loads']
                    w = window(d)
                    r['959'] = {e['event']:[e['frame'],e['line']] for e in w
                        if e['op']==3 and e['g']==959 and e['event'] in ('load','wait169','final_upload212_same_blank212','reveal','ack')}
                    if tag == '887-seal':
                        def writes(variant):
                            out = temp/f'nes-mapwait880-consumer-{phase}-{variant}-g959'
                            observations = window(temp/(prefix+variant))
                            expected = next(e for e in observations if e['g']==959 and e['op']==3 and e['event']=='ack')
                            assert load(out/'summary.json')['final_ACK']['clock'] == expected['clock']
                            with (out/'idle-vram.csv').open() as fd:
                                return [v for v in csv.reader(fd) if 24576 <= int(v[1]) < 25344]
                        before = writes('886-static')
                        after = writes(tag)
                        assert len(before)==768
                        r['959_map_bytes'] = len(after)
                        r['959_map_matches'] = before == after
    return result


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    a = p.parse_args()
    a.output.write_text(json.dumps(evaluate(a.temp),indent=2)+'\n', encoding='utf8',newline='\n')
