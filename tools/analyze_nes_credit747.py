# SPDX-License-Identifier: MIT
"""Check exact map prefix, E0 authority and actual MDMAEN on coupled ARM/65816 runs."""
import argparse
import json
from pathlib import Path

from analyze_nes_bg745 import timeline
from analyze_nes_beam741 import records
from analyze_nes_owner739 import csv_groups, packets, read, sha
from check_nes_handoff678 import crc
from math import ceil
from test_nes_raw506_joint import MASTER


def analyze(a):
    rtl=read(a.rtl/'result.json')
    board=a.temp/'nes-bg707-board04'
    assert all(sha(board/k)==v for k,v in rtl['pins'].items())
    top=(board/'fxpak_nes_screen137_top.sv').read_text()
    core=(board/'nes_live_joint.sv').read_text()
    assert '.out_observe_ready(MCU_RDY)' in top and 'assign SNES_IRQ=0;' in top
    assert 'assign out_observe_ready=external_memory_ready;' in core
    rtl['top_pins']={f:sha(board/f) for f in ('board.qsf','fxpak_nes_screen137_top.sv','nes_live_joint.sv')}
    result=dict(stage=747,reference=727,board='707D',RTL=rtl,ARM={},phases={},faults={})
    for k in ('long','normal','foldlong','foldnormal','debtlong','debtnormal'):
        fw=a.probe/k/'src/obj-nes-100/firmware.stm'
        paths={g:a.probe/(f'{k}-scope.json' if g=='credit747' else f'{k}-{g}.json') for g in ('credit747','menu533','bg745','deadline719')}
        guards={g:read(path) for g,path in paths.items()}
        assert guards['credit747']['rejected_bits']==152 and guards['credit747']['scope_cases']==(3 if k.startswith('debt') else 4)
        assert all(g['firmware']==sha(fw) for g in guards.values())
        assert len(guards['credit747']['receipt'])==9 and len(guards['deadline719']['cases'])==17
        assert [r['budget'] for r in guards['credit747']['credit']]==[1,647,21504]
        assert len(guards['bg745']['cases'])==6
        if k.startswith('debt'):assert len(guards['credit747']['repayment'])==5
        menu=guards['menu533']; assert menu['marker_cases']==4 and len(menu['rows'])==5
        assert all(bool(r['released'])==(name=='normal') for name,r in menu['rows'].items())
        result['ARM'][k]=dict(bytes=fw.stat().st_size,free_B=212992-fw.stat().st_size,sha256=sha(fw),
            size=(a.probe/k/'size.log').read_text().splitlines()[-1].split()[:3],
            guards={g:sha(path) for g,path in paths.items()})
    for k in result['ARM']:
        files=a.probe/('patch-'+k)
        result['ARM'][k]['source']={f.name:sha(f) for f in files.iterdir() if f.is_file()}
        assert all(sha(a.probe/k/'src'/f)==digest for f,digest in result['ARM'][k]['source'].items())
    result['CRC']=read(a.probe/'fold.json')
    assert result['CRC']['transitions']==65536
    for n in (1,2):
        base=a.temp/f'nes-pair727-a{n}'
        variants=result['phases'][n]={}
        for k in ('ref','control','eager','measured','linked','fold','foldlink','debt','debtlink'):
            folder=base if k=='ref' else a.temp/(f'nes-oam746-matched{n}' if k=='control' else f'nes-credit747-{k}{n}')
            r=variants[k]=timeline(folder,base)
            if k=='ref':continue
            r['ACK_delta_clocks']=r['final_ACK']-variants['ref']['final_ACK']
            r['OBJ_offer_delta_clocks']=r['OBJ_push']-variants['ref']['OBJ_push']
            run=read(folder/'joint.json')
            r['stack_low']=run['observed_stack_low']
            ev=read(folder/'events.json')
            e0=[e for e in ev if e.get('event')=='SPI' and e['opcode']=='0xe0' and e['generation']==957
                and r['map_last_push']<e['start']<r['OBJ_push']]
            h=next(h for h,_,t in packets(folder)[957] if t==r['map_last_push'])
            # Earliest serial edge and a conservative in-model upper limit if
            # the entire measured mean non-wire driver allocation precedes SCK.
            edge_ns=max(row[4]-row[1] for rows in rtl['runs'].values() for row in rows)
            bound=ceil(MASTER*((1/2625000)+(edge_ns*1e-9)+run['parameters']['driver_extra_us']['0xe0']*1e-6))
            r['opcode_latch_upper_masterclocks']=bound
            r['credit_samples']=[]
            for e in e0:
                raw=bytes.fromhex(e['reply'])
                sent,retired=int.from_bytes(raw[3:5],'big'),int.from_bytes(raw[5:7],'big')
                assert raw[1]==0xf7 and crc(raw[1:19],8,7,0)==raw[19]
                if sent==retired:
                    assert raw[2]&2 and raw[7:19]==bytes((0,h[0]))+h[2:10]+bytes((0x65,0x9a))
                offset=round(e['start'])-r['map_last_ACK']
                r['credit_samples'].append(dict(offset=offset,may_cross_final_map_return=offset<5 and offset+bound>=0,pending=sent-retired,
                                                reply=raw.hex(),end=round(e['clock'])))
            assert [x['pending']==0 for x in r['credit_samples']]==[False]*(len(e0)-1)+[True]
            r['quiet_budget']=[e['budget'] for e in ev if e.get('event')=='E0_quiet747']
            if k in ('measured','eager','fold','debt'):
                assert r['quiet_budget'] and r['map_issue']['changed']==0
                assert all((b==0 if k=='eager' else 0<b<=21504) for b in r['quiet_budget'])
            if k in ('fold','debt'):assert len([e for e in ev if e.get('event')=='E0_fold747'])==1
            if k=='debtlink':assert r['firmware']==result['ARM']['debtlong']['sha256']
            if k=='debt':
                assert [e['event'] for e in ev if e.get('event') in ('hold_input747','repay_input747')]==['hold_input747','repay_input747']
            if k in ('debt','debtlink'):
                assert all(x['op']!='0xd0' for x in r['map_to_OBJ_SPI'])
                after=[e for e in ev if e.get('event')=='SPI' and e.get('generation')==957 and e['start']>r['OAM_push']]
                idx=next(i for i,e in enumerate(after) if e['opcode']=='0xd0')
                raw=bytes.fromhex(after[idx-1]['reply'])
                oam=next(h for h,b,t in packets(folder)[957] if t==r['OAM_push'])
                assert idx>0 and after[idx-1]['opcode']=='0xe0' and raw[3:5]==raw[5:7]
                assert raw[7:19]==bytes((0,9))+oam[2:10]+bytes((0x65,0x9a)) and raw[19]==crc(raw[1:19],8,7,0)
                r['input_after_OAM']=dict(checked=round(after[idx-1]['clock']),D0=round(after[idx]['start']),reply=raw.hex())
            if k=='foldlink':assert r['firmware']==result['ARM']['foldlong']['sha256']
            if k=='linked':assert r['firmware']==result['ARM']['long']['sha256']
            m=r['order957']['long_map']
            if m:r['after_map']=next(e for e in csv_groups(folder/'window.csv')[957] if e['clock']>m['end'] and e['event'] in ('load','ppu_dma'))
            for fault in ('stop','stale','pre','during','head'):
                d=a.temp/f'nes-credit747-{k}{n}-{fault}'
                if not d.exists():continue
                outcome=read(d/'result.json')
                assert outcome['passed'] and outcome['commits']==(53 if fault=='head' else 52)
                if fault!='head':assert sha(d/'retained.rgb')==sha(base/'frame-956.rgb')
                tiles=[x['n'] for x in records(d/'dma745.csv') if x['g']==957 and x['src']==19104]
                if fault in ('pre','during','head'):
                    assert tiles=={'pre':[],'during':[64],'head':[288]}[fault]
                if fault=='head':
                    tick=int((d/'fault745.txt').read_text())
                    head=next(e for e in csv_groups(d/'window.csv')[957] if e['clock']>tick and e['event'] in ('load','ppu_dma'))
                    assert head['event']=='load' and head['section']==5
                result['faults'][f'{k}{n}-{fault}']=dict(commits=outcome['commits'],status=outcome['last_status'],OBJ_DMA=tiles,trace=sha(d/'window.csv'))
    required={f'measured{n}-{fault}' for n in (1,2) for fault in ('pre','during','head','stop','stale')}
    for n in (1,2):
        for k in ('fold','debt','debtlink'):
            required.update(f'{k}{n}-{fault}' for fault in ('stop','stale'))
            if result['phases'][n][k]['OBJ_MDMAEN']:
                required.update(f'{k}{n}-{fault}' for fault in ('pre','during','head'))
    assert required<=result['faults'].keys()
    result['debt_probe']=sha(a.probe/'debt.elf')
    a.out.write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for k in ('temp','probe','rtl','out'):p.add_argument('--'+k,type=Path,required=True)
    analyze(p.parse_args())
