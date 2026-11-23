"""Match 909 grouped destinations, 910 input ownership and 911 capture to one clock."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

from analyze_nes_deadline947 import directory, read, ready_bytes, report
from nes_input949 import HELD, MODES, work


def timing(folder):
    events=read(folder/'events.json')
    window=list(csv.DictReader((folder/'window.csv').read_text().splitlines()))
    show=next(int(r['clock']) for r in window if r['g']=='909' and r['event']=='reveal')
    tiles=[]
    for line in (folder/'packets.jsonl').read_text().splitlines():
        packet=bytes.fromhex(json.loads(line)[2])
        if packet[:2]==bytes((7,1)) and int.from_bytes(packet[8:10],'little')==909:
            tiles.append([int.from_bytes(packet[10:12],'little'),int.from_bytes(packet[14:16],'little')])
    e9=[p['records'] for p in read(folder/'e9931.json') if p['g']==909]
    reads=[e for e in events if e.get('input_generation')==910 and e.get('opcode')=='0xd1']
    pops=[e for e in events if e.get('input_generation')==910 and e.get('opcode')=='0xd2']
    blocks=[[round(d['start']),round(d['clock']),round(p['start']),round(p['clock']),d['bytes']]
            for d,p in zip(reads,pops,strict=True)]
    assert len(blocks)==18 and all(a<b<c<d for a,b,c,d,_ in blocks)
    ea=next(round(e['clock']) for e in events if e.get('generation')==909 and e.get('opcode')=='0xea')
    commit=next(round(e['start']) for e in events if e.get('input_generation')==910 and e.get('opcode')=='0xd3')
    assert pops[-2]['clock']<commit<reads[-1]['start'] and show<ea<commit
    jobs=[json.loads(line) for line in (folder/'producer.jsonl').read_text().splitlines()]
    last=next(j for j in reversed(jobs) if j['generation']==909 and j['kind']==1)
    returned=dict(read(folder/'returns904.json'))[last['token']]
    seal=next(int(r['clock']) for r in window if r['g']=='909' and r['op']=='3' and r['event']=='load')
    offer=next(e for e in events if e.get('event')=='source_begin' and e['generation']==910)
    valid=next(e for e in events if e.get('opcode')=='0xe0' and e.get('generation')==909 and
               e['start']>=show and (bytes.fromhex(e['reply'])[2]&7)==2 and
               bytes.fromhex(e['reply'])[7:9]==bytes((1,3)) and
               int.from_bytes(bytes.fromhex(e['reply'])[15:17],'little')==909)
    hw_ack=next(int(r['clock']) for r in window if r['g']=='909' and r['op']=='3' and r['event']=='ack')
    assert show<hw_ack<=valid['clock']<ea
    return dict(held_tokens=offer.get('held_tokens649',[]),source_begin=round(offer['clock']),
                displayed_ACK=hw_ack,valid_E0_start=round(valid['start']),valid_E0_end=round(valid['clock']),
                last_OBJ_bytes=last['bytes'],last_OBJ_ready=last['producer'],bank_return=returned,
                bank_to_D1=blocks[0][0]-returned,seal_load=seal,
                D1_wire=sum(b-a for a,b,c,d,n in blocks),D1_end_to_D2_start=sum(c-b for a,b,c,d,n in blocks),
                D2_wire=sum(d-c for a,b,c,d,n in blocks),blocks=blocks,returned_before_show=sum(row[3]<show for row in blocks[:-1]),
                show=show,EA=ea,COMMIT=commit,tiles=tiles,E9=e9)


def compare(temp,modes):
    all_results=report(temp,modes,prefix='949',work=work)
    out=dict(master_Hz=all_results['master_Hz'],physical=False,consumer=all_results['ROM'],cases={},
             gates=all_results['gates'],safety=all_results['recovery'])
    out['controls']={}
    for case,metrics in all_results['cases'].items():
        cache,phase=case[:-1],int(case[-1])
        ref=directory(temp,phase,'948half_page',cache)
        original=timing(ref)
        ready=ready_bytes(ref)
        old_folder=directory(temp,phase,'935boundedfinal',cache)
        old=ready_bytes(old_folder)
        def last_ack(folder):
            frame=read(folder/'joint.json')['frames'][-1]
            assert frame['generation']==912
            return frame['ACK_masterclock']
        out['cases'][case]={'half_page':original}
        held_ref=directory(temp,phase,'949held_base',cache)
        held_old=directory(temp,phase,'949reference935',cache)
        held_946=directory(temp,phase,'949reference946',cache)
        out['controls'][case]={}
        for name,folder in [('original948',ref),('held948',held_ref),('original935',old_folder),
                            ('held935',held_old),('held946',held_946)]:
            end=read(folder/'joint.json')
            marks=[int(r['frame']) for r in csv.DictReader((folder/'window.csv').read_text().splitlines())
                   if r['event']=='reveal' and 906<=int(r['g'])<=912]
            assert end['passed'] and len(marks)==7
            out['controls'][case][name]=dict(firmware=end['firmware_SHA256'],consumer=end['client_SHA256'],
                ACK=last_ack(folder),six=marks[-1]-marks[0],D2=timing(folder)['blocks'][-1][3])
        assert out['controls'][case]['original935']['firmware']==out['controls'][case]['held935']['firmware']
        for mode in modes:
            folder=directory(temp,phase,'949'+mode,cache)
            times=timing(folder)
            r=metrics[mode]
            supplied=ready_bytes(folder)
            keys=[(910,1,i) for i in range(80*32,89*32)]
            supply_lag=max(supplied[k][1]-old[k][1] for k in keys)
            held=mode in HELD
            same_ref=held_ref if held else ref
            same_old=held_old if held else old_folder
            ready_control=ready_bytes(same_ref)
            before=timing(same_ref)
            advance=original['blocks'][-1][3]-times['blocks'][-1][3]
            out['cases'][case][mode]=dict(timing=times,Flash=r['Flash'],firmware=r['sha256'],
                D2_advance=advance,D2_advance_same_admission=before['blocks'][-1][3]-times['blocks'][-1][3],
                ACK_advance_same935=last_ack(same_old)-r['final_ACK'],
                ACK_advance_same948=last_ack(same_ref)-r['final_ACK'],
                ACK_advance_same946=last_ack(held_946)-r['final_ACK'] if held else r['advance_ACK'],
                same_groups_control=times['tiles']==before['tiles'] and times['E9']==before['E9'],
                OBJ288_minus_control=max(supplied[k][1]-ready_control[k][1] for k in keys),D2_minus_line=r['D2_minus_target911'],capture911=r['stages'][911]['capture'],six=r['total'],gaps=r['gaps'],
                ACK_advance_vs935=last_ack(old_folder)-r['final_ACK'],
                ACK_advance_vs948=last_ack(ref)-r['final_ACK'],ACK_advance_vs946=r['advance_ACK'],ACK=r['final_ACK'],same_909=times['E9']==original['E9'] and times['tiles']==original['tiles'],
                other_tiles=r['supply_vs935'],late=r['late_destinations'],OBJ288_minus935=supply_lag,
                OBJ288_minus948=max(supplied[k][1]-ready[k][1] for k in keys),
                prior_blank_B=r['prior_blank_B'],tail_grant=r['tail_grant'],
                prefetch909=r['stages'][909]['data_blocks_before_show'])
    for mode,gate in out['gates'].items():
        rows=[values[mode] for values in out['cases'].values()]
        gate['same_909']=all(r['same_909'] for r in rows)
        gate['input910_17']=all(r['timing']['returned_before_show']==17 for r in rows[2:])
        gate['supply288']=all(r['OBJ288_minus935']<=0 for r in rows[2:])
        gate['early_911']=all(r['D2_minus_line']<=0 and r['gaps'][-2]==2 for r in rows[2:])
        gate['supply288_vs948']=all(r['OBJ288_minus948']<=0 for r in rows[2:])
        gate['same_admission']=all(r['same_groups_control'] and r['ACK_advance_same935']>0
            and r['ACK_advance_same946']>=0 for r in rows) and all(r['OBJ288_minus_control']<=0 for r in rows[2:])
        gate['ACK_vs935']=all(r['ACK_advance_vs935']>0 for r in rows)
        gate['requested_schedule']=all(gate[k] for k in ('Flash','input17','input910_17','same_909','same_admission','supply288','supply288_vs948','ACK_vs935','early_911','cold_preDMA','warm13_cold14','no_later_ACK'))
        gate['checked_recovery']=mode in out['safety']
        gate['promote']=gate['requested_schedule'] and gate['checked_recovery'] and gate['other_tiles']
    out['passing']=[mode for mode,gate in out['gates'].items() if gate['promote']]
    if 'held_stage' in modes:
        out['post_ACK_profile']={}
        for phase in (1,2):
            folder=directory(temp,phase,'949held_stageaudit','cold')
            marks=read(folder/'handoff949.json')
            display=next(t for t,name in marks if name=='nes_budget210_display')
            retire=next(t for t,name in marks if name=='nes_plan200_retire')
            header=next(t for t,name in marks if name=='page905')
            end=next(t for t,name in marks if t>header and name=='nes_cost471_now')
            out['post_ACK_profile'][phase]=dict(events=marks,display_to_retire_clocks=retire-display,
                page_entry_to_next_timer_clocks=end-header)
        # The rejected full-report reorder is a link measurement only. The
        # ordinary linked program records COMMIT at planner entry; a diagnostic
        # snapshot taken after EA cannot assume the current input is its owner.
        attempt=work('report')/'link/src/obj-nes-100/firmware.stm'
        if attempt.is_file():
            image=attempt.read_bytes()
            out['deferred_report_link']=dict(firmware=hashlib.sha256(image).hexdigest(),
                Flash=len(image),Flash_limit=212992,over_limit=max(0,len(image)-212992),
                schedule_verified=False)
    rtl=temp/'nes-input949-held-rtl/result.json'
    if any(mode in HELD for mode in modes):
        out['held_RTL']=read(rtl)
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(compare(a.temp,a.modes),indent=2)+'\n',encoding='utf-8')
