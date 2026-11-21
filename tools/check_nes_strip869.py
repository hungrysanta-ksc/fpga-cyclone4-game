"""Compare the linked consumer's publication, ACK and map traffic with MMC866."""
import argparse
import hashlib
import json
from pathlib import Path

from analyze_nes_map830 import load, packets, window
from analyze_nes_transition850 import STRIDE
from guard_nes_output852 import run as guard


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def metrics(folder):
    run = load(folder / 'joint.json')
    assert run['passed'] and run['last_status'] == 1
    events = window(folder)
    visible = [e for e in events if e['event'] == 'reveal']
    assert len(visible) == run['commits']
    final = [e['clock'] for e in events if e['event'] == 'ack' and e['op'] == 3]
    assert final == [f['ACK_masterclock'] for f in run['frames']]
    data = packets(folder)
    spi = [e for e in load(folder/'events.json') if e.get('opcode') == '0xe1']
    assert len(data) == len(spi)
    maps = [(b, tx) for b, tx in zip(data, spi, strict=True) if b[1] == 2 and b[0] in (2, 4, 5, 6, 9, 10)]
    warm=[pair for pair in maps if int.from_bytes(pair[0][8:10],'little')>906]
    blank=folder/'blank-interval.json'
    if blank.exists():
        assert load(blank)['source_frames']==12
    return dict(held_blank_VBlanks=visible[20]['frame']-visible[19]['frame']-1 if blank.exists() else None,
                pictures=len(visible), all_wire_B=run['wire_B'], ARM_instructions=run['ARM_instructions'],
                after_two_VBlanks=visible[-1]['frame']-visible[1]['frame'],
                last_ACK=final[-1], map_E1=len(maps), map_wire_B=sum(tx['bytes'] for _,tx in maps),
                warm_map_E1=len(warm), warm_map_wire_B=sum(tx['bytes'] for _,tx in warm),
                warm_map_SPI_clocks=round(sum(tx['clock']-tx['start'] for _,tx in warm)),
                observed_stack_clearance_B=int(run['observed_stack_low'],16)-int(run['workspace_end'],16),
                strips=sum(b[0]==10 for b,_ in maps),
                opening_marks={str(e['g']):[e['frame'],e['line']] for e in visible if e['g'] in (910,966) and 'opening' in folder.name})


def strips(folder, reference):
    def events(path):
        wire=packets(path)
        heads={v['index']:v for v in window(path) if v['event']=='load'}
        retire={v['index']:v for v in window(path) if v['event']=='ack'}
        return [(b,heads[i]['clock'],retire[i]['clock']) for i,b in enumerate(wire,1) if b[1]==2]
    old=events(reference)
    details=[]
    for b,first,ack in events(folder):
        if b[0]!=10:
            continue
        generation=int.from_bytes(b[8:10],'little')
        rows=[(a,st,en) for a,st,en in old if a[8:10]==b[8:10] and 2048<=int.from_bytes(a[10:12],'little')<3520]
        assert len(rows)==8 and all(a[0] in (2,4) for a,_,_ in rows)
        details.append(dict(generation=generation, payload_B=len(b)-16,
                            baseline_service_clocks=sum(en-st for _,st,en in rows),
                            candidate_service_clocks=ack-first,
                            last_map_ACK_delta_clocks=ack-max(en for _,_,en in rows)))
    return details


def publication_cost(folder):
    clocks=window(folder)
    frames=[r for r in clocks if r['event']=='reveal']
    ack={r['g']:r for r in clocks if r['event']=='ack' and r['op']==3}
    seal={r['g']:r for r in clocks if r['event']=='load' and r['op']==3}
    last_map={r['g']:r for r in clocks if r['event']=='ack' and r['section']==2}
    timeline=load(folder/'events.json')
    sends=[e for e in timeline if e.get('opcode')=='0xe1']
    capture={e['generation']:e['capture_ready'] for e in timeline if e['event']=='source_begin'}
    plan={e['generation']:e['clock'] for e in timeline if e['event']=='planner_enter'}
    rows={}
    for prev,now in zip(frames[1:-1],frames[2:]):
        g=now['g']
        obj=[v['clock'] for v in clocks if v['g']==g and v['op']==7 and v['section']==1 and v['event']=='ack']
        palette=[v['clock'] for v in clocks if v['g']==g and v['section']==3 and v['event']=='ack']
        split=None
        probes=[]
        if obj and palette:
            first=next(v for v in clocks if v['g']==g and v['section']==3 and v['event']=='load')
            tx=sends[first['index']-1]
            probes=[bytes.fromhex(e['reply'])[2] for e in timeline if e.get('opcode')=='0xe0'
                    and obj[-1]<=e['start'] and e['clock']<=tx['start']]
            split=[round(tx['start']-obj[-1]),round(tx['clock']-tx['start']),
                   round(first['clock']-tx['clock']),palette[0]-first['clock']]
        rows[g]=dict(E0_before_palette=len(probes), E0_with_DMA_progress=sum(bool(x&8) for x in probes),
                     OBJ_ACK_to_palette_issue_wire_load_retire=split,capture_ready_clock=capture[g], planner_clock=round(plan[g]),
                     map_ACK_to_SEAL=None if g not in last_map else seal[g]['clock']-last_map[g]['clock'],
                     last_OBJ_to_first_palette=palette[0]-obj[-1] if obj and palette else None,
                     gap=now['frame']-prev['frame'],
                     prior_show_to_capture_ready=round(capture[g]-prev['clock']),
                     prior_show_to_planner=round(plan[g]-prev['clock']),
                     prior_show_to_map=None if g not in last_map else last_map[g]['clock']-prev['clock'],
                     prior_show_to_SEAL=seal[g]['clock']-prev['clock'],
                     SEAL_to_show=now['clock']-seal[g]['clock'],
                     show_to_ACK=ack[g]['clock']-now['clock'])
    return rows


def compare(temp, work, tag):
    fw=work/'link-credit/src/obj-nes-100/firmware.stm'
    client=work/'client02/sink165.sfc'
    result=dict(ARM=digest(fw), flash_B=fw.stat().st_size, client=digest(client),
                client_ROM_free_B=load(work/'client02/build.json')['physical_free_B'], scenes={})
    menu=load(work/'menu869.json')
    assert menu['firmware']==result['ARM'] and menu['rows']['normal']['released']
    result['menu_release']={k:v['released'] for k,v in menu['rows'].items()}
    for clip in ('demo','opening','transition'):
        for phase in (1,2):
            prefix=f'nes-tile821-{clip}-jointmirror-p{phase}-'
            base=temp/(prefix+'866-on')
            candidate=temp/(prefix+tag)
            old=metrics(base)
            new=metrics(candidate)
            r=load(candidate/'joint.json')
            assert r['firmware_SHA256']==result['ARM'] and r['client_SHA256']==result['client']
            assert old['pictures']==new['pictures']
            for fr in r['frames']:
                name=f"frame-{fr['generation']}.rgb"
                a=(candidate/name).read_bytes()
                b=(base/name).read_bytes()
                assert len(a)==len(b) and a[7*STRIDE:231*STRIDE]==b[7*STRIDE:231*STRIDE],(clip,phase,name)
            assert r['parameters']==load(base/'joint.json')['parameters']
            gap_changes={}
            if clip=='demo':
                old_cost=publication_cost(base)
                new_cost=publication_cost(candidate)
                gap_changes={g:[old_cost[g],c] for g,c in new_cost.items() if c['gap']!=old_cost[g]['gap']}
                assert load(candidate/'ack861.json')['loads']==load(base/'ack861.json')['loads']
            result['scenes'][f'{clip}-{phase}']=dict(reference=old,candidate=new,
                gap_changes=gap_changes, strip_returns=strips(candidate,base) if clip=='demo' else [],
                ACK_delta_clocks=new['last_ACK']-old['last_ACK'])
    return result


def guards(temp, work, tag, client_name='client02'):
    folder=temp/f'nes-tile821-demo-jointmirror-p1-{tag}'
    result={}
    for name in ('cold','base','length','column','range','overlap','omitted','prefix','stop','late-stop','two-stop','restart'):
        seed=folder/'guard-two-stop/canceled.bin' if name=='restart' else None
        result[name]=guard(temp,folder,name,seed,column_client=work/client_name,column_op=10)
    packet=next(b for b in packets(folder) if b[:2]==bytes((10,2)) and len(b)==116)
    g=int.from_bytes(packet[8:10],'little')
    bank=(int.from_bytes(packet[4:8],'little')-1)&1
    col=int.from_bytes(packet[22:24],'little')
    before=(folder/f'map-{g-2}.bin').read_bytes()
    active=(folder/f'map-{g-1}.bin').read_bytes()
    saved=(folder/'guard-two-stop/canceled.bin').read_bytes()
    assert saved[(1-bank)*4096:(2-bank)*4096]==active
    expected=bytearray(before[2048:3520])
    for y in range(23):
        at=y*64+col
        expected[at:at+2]=packet[24+y*2:26+y*2]
    assert before[2048:3520]!=expected and saved[bank*4096+2048:bank*4096+3520]==expected
    return dict(client=digest(work/client_name/'sink165.sfc'), source_tag=tag, cases=result,
                two_column_cancel=dict(g=g,changed_columns_written=1,peer_intact=True))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('mode',choices=('compare','guards'))
    p.add_argument('temp',type=Path)
    p.add_argument('work',type=lambda s:Path(s).resolve())
    p.add_argument('tag')
    p.add_argument('out',type=Path)
    a=p.parse_args()
    result=(compare if a.mode=='compare' else guards)(a.temp,a.work,a.tag)
    a.out.write_text(json.dumps(result,indent=2)+'\n')
