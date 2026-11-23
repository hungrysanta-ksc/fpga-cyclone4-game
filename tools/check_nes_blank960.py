"""Compare a full boot of the short-pair ROM to the two 959 controls."""
import argparse
import json
from pathlib import Path

from analyze_nes_ready958 import board_case
from analyze_nes_chr951 import board_cost, logtext
from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage
from check_nes_blank959 import directory, guard, read, rows, sha, summary
from nes_blank960 import PACKED, ROM, WORK, edits
from nes_companion952 import project
from test_nes_banks557 import MASTER


def analyze(temp):
    expected=bytearray((ROM/'body.bin').read_bytes())
    for at,old,new in edits('retry'):
        assert expected[at]==old
        expected[at]=new
    assert (PACKED/'body.bin').read_bytes()==expected
    boot=read(temp/'nes-blank960-boot/result.json')
    assert boot['passed'] and [r['kind'] for r in boot['cases']]==['restored','rejected']*2
    consumer=sha(PACKED/'sink165.sfc')
    assert all(r['ROM']==consumer for r in boot['cases'][2:])
    fw=sha(WORK/'link/src/obj-nes-100/firmware.stm')
    menu=read(PACKED.parent/'menu.json')
    base=read(PACKED.parent/'base/result.json')
    assert menu['firmware']==base['firmware_sha256']==fw and base['base_restored'] and base['safe_return']
    build=read(PACKED/'build.json')
    assert build['loader_B']+build['encoded_B']+64+build['physical_free_B']==5120
    board_dir=temp/'nes-trial816-board960'
    assert sha(board_dir/'sink-program.hex')==sha(PACKED/'sink-program.hex')
    result=dict(physical_reference='MMC955',firmware=fw,consumer=consumer,
                verified_WRAM=sha(PACKED/'body.bin'),bytes={k:build[k] for k in
                ('body_bytes','loader_B','encoded_B','physical_free_B','physical_ROM_B')},
                boot=boot['cases'],menu=menu,base_restore=base['config_paths'],phases={},
                board={name:board_cost(d) for name,d in
                       [('952',project(temp,'checked')),('960',board_dir)]})
    assert result['board']['960']['fit']
    for p in (1,2):
        folder=lambda tag: directory(temp,p,tag,'cold')
        control=folder('958closed')
        ref=summary(control,control)
        cases={}
        for tag in ('958closed','959retryseal','959orderedclosed','960static','960closed'):
            run=folder(tag)
            trial=summary(run,control)
            joint=read(run/'joint.json')
            assert joint['firmware_SHA256']==fw
            if tag.startswith('960'):
                assert joint['client_SHA256']==consumer
            cases[tag]={k:trial[k] for k in ('six','reveals','SEAL911','D2_before_911_reveal',
                        'seal','reveal','sealed906_DMA','VRAM_B','RGB','ACK912')}
            cases[tag]['ACK912_delta_ms']=round((trial['ACK912']-ref['ACK912'])*1000/MASTER,6)
        d=folder('960closed')
        board=board_case(d)
        assert board['polls'][1]==0 and board['body_B']==75 and board['checked_batch']==7
        e9=[e for e in read(d/'events.json') if e.get('generation')==906 and e.get('opcode')=='0xe9']
        assert len(e9)==7 and abs(e9[-1]['clock']-board['checked_seal'])<=2
        faults={}
        for name,status in [('bad-seal',224),('edge959-before',228),('edge959-after',228)]:
            out=d/('guard-'+name)
            r=read(out/'result.json')
            assert r['passed'] and r['commits']==1 and r['last_status']==status
            assert sha(out/'retained.rgb')==sha(d/'frame-905.rgb')
            faults[name]=status
        cases['RTL906']=board
        cases['RTL905_E8']=next(s.strip() for s in logtext(d/'gen905/timing958.log').splitlines()
                                if 'E8914 compared=' in s)
        frames=measure(d,WORK)[0]['frames']
        obj908=[r for r in rows(d/'window.csv') if (r['g'],r['op'],r['section'],r['event'])==
                ('908','7','1','load')][-1]
        cases['tail908']=dict(last_OBJ_load={k:int(obj908[k]) for k in ('frame','line','clock')},
                              clocks=frames[908]['clocks'],lines=frames[908]['line'],
                              residual_DMA=frames[908]['residual_DMA'])
        cases['input_D2_to_nearest_capture_us']={g:round(frames[g]['D2_minus_nearest_capture']*1e6/MASTER,3)
                                                 for g in (910,911,912)}
        frame=frames[912]
        pre=[r for r in frame['preDMA'] if r[3]==frame['VBlank'][3]-1]
        cases['preDMA912']=dict(bytes=len(coverage(pre)),ranges=pre)
        warm={}
        for tag in ('960control','960static'):
            item=summary(directory(temp,p,tag,'warm'),directory(temp,p,'960control','warm'))
            warm[tag]={k:item[k] for k in ('reveals','six','ACK912','D2_before_911_reveal')}
        warm['ACK912_delta_ms']=round((warm['960static']['ACK912']-warm['960control']['ACK912'])*1000/MASTER,6)
        cases['warm_supply_model']=warm
        cases['guards']=faults
        result['phases'][p]=cases
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('--phase',type=int,choices=(1,2))
    p.add_argument('--guard',choices=('before','after','identity'))
    a=p.parse_args()
    if a.guard:
        print(guard(a.temp,a.phase,a.guard,True,static_client=PACKED,tag='960closed'))
    else:
        print(json.dumps(analyze(a.temp),indent=2))
