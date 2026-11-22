"""Align input retirement, physical display and the next capture on one clock."""
import argparse
import json
from pathlib import Path

from analyze_nes_palette921 import batches, coverage, directory, read, read_csv, sha, summarize, tile_bytes
from nes_deadline922 import MODES, WORK, check_groups, image
from test_nes_raw506_joint import MASTER, PERIOD


def measure(folder, work):
    metrics, packets, _ = summarize(folder, work)
    events = read(folder/'events.json')
    window = read_csv(folder, 'window.csv')
    shown = {int(r['g']):int(r['frame']) for r in window if r['event']=='reveal'}
    gaps = [shown[g]-shown[g-1] for g in range(907,913)]
    assert sum(gaps)==metrics['intervals']
    sources = {e['generation']:e for e in events if e['event']=='source_begin'}
    frames = {}
    for g in range(908,913):
        src = sources[g]
        io = [e for e in events if e.get('input_generation')==g]
        pops = [round(e['clock']) for e in io if e.get('opcode')=='0xd2']
        commit = next(round(e['clock']) for e in io if e.get('opcode')=='0xd3')
        assert pops[-2]<commit<pops[-1]
        f = metrics['frames'][g]
        residual = [int(r['value']) for r in window if r['g']==str(g) and r['op']=='3' and r['event']=='ppu_dma']
        assert sum(residual)==f['DMA_bytes_after_SEAL']
        frames[g]=dict(capture_ready=round(src['capture_ready']),source_begin=round(src['clock']),
                       first_D1=next(round(e['clock']) for e in io if e.get('opcode')=='0xd1'),
                       data_D2=pops[-2],commit=commit,commit_D2=pops[-1],
                       D2_minus_nearest_capture=pops[-1]-round(pops[-1]/PERIOD)*PERIOD,
                       last_OBJ_return=f['last_OBJ_return'],clocks=f['masterclocks'],
                       VBlank=f['VBlank'],line=f['scanlines'],residual_DMA=residual,
                       preDMA=metrics['preDMA'][g])
        if g+1 in sources:
            captured=round(sources[g+1]['capture_ready'])-240*341*4
            assert captured-PERIOD<=pops[-1]<=captured
            frames[g]['next_capture_start']=captured
            frames[g]['clocks_to_next_capture']=captured-pops[-1]
    checks=dict(params=metrics['parameters'],tiles=tile_bytes(folder),batches=batches(folder),
                RGB=[sha(folder/f'frame-{g}.rgb') for g in packets],
                map=[sha(folder/f'map-{g}.bin') for g in packets],
                colors=[sha(folder/f'colors636-{g}.bin') for g in packets],
                sections=[f['section5_hash'] for f in metrics['frames'].values()])
    return dict(frames=frames,gaps=gaps,intervals=sum(gaps),display908=shown[908],
                final_ACK=metrics['final_ACK']),checks


def analyze(temp, modes):
    out=dict(master_Hz=MASTER,period=PERIOD,flash_limit=212992,variants={})
    for phase in (1,2):
        for cache in ('warm','cold'):
            key=f'{phase}-{cache}'
            base,checks=measure(directory(temp,phase,'920reference',cache),image('baseline'))
            for mode in ('915','921',*modes):
                work=image('baseline') if mode=='915' else image('compact') if mode=='921' else WORK/mode
                fw=work/'link/src/obj-nes-100/firmware.stm'
                variant=out['variants'].setdefault(mode, dict(firmware=sha(fw),flash=fw.stat().st_size,cases={}))
                if mode=='915':
                    row=base
                else:
                    tag='921compact' if mode=='921' else '922'+mode
                    row,actual=measure(directory(temp,phase,tag,cache),work)
                    assert checks==actual,(mode,key)
                ref_pre=coverage(base['frames'][912]['preDMA'])
                pre=coverage(row['frames'][912]['preDMA'])
                row['pre912_B']=len(pre)
                row['pre912_exact_addresses']=ref_pre.keys()==pre.keys()
                row['ACK_gain_clocks']=base['final_ACK']-row['final_ACK']
                row['interval_gain']=base['intervals']-row['intervals']
                variant['cases'][key]=row
    for variant in out['variants'].values():
        variant['qualifies']=variant['flash']<=212992 and all(
            r['interval_gain']>0 and r['ACK_gain_clocks']>0 and
            (r['pre912_exact_addresses'] and r['pre912_B']==496 if k.endswith('cold')
             else r['display908']<=out['variants']['921']['cases'][k]['display908'])
            for k,r in variant['cases'].items())
    for mode in ('group','idle','firstrow','suffix'):
        if mode not in modes:
            continue
        variant=out['variants'][mode]
        proof=WORK/mode/'proof'
        digest=variant['firmware']
        for file in ('loader.json','timer.json','menu.json'):
            assert read(proof/file)['firmware']==digest
        base=read(proof/'base/result.json')
        assert base['safe_return'] and base['firmware_sha256']==digest
        assert read(proof/'timer.json')['passed'] and read(proof/'menu.json')['rows']['normal']['released']
        rx=read(proof/'sram.json')['cases']
        assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
        guards=read(WORK/(mode+'-guards.json'))
        for case,status,commits in [('stop-copy',228,3),('descriptor',224,3),('duplicate',224,3),
                                    ('seal',224,4),('display_stop',228,4)]:
            assert guards[case]==dict(status=status,commits=commits)
        variant['recovery']=dict(guards=guards,SRAM_D0_sites=4,bad_CRC_rejected=True,menu=True)
        if mode!='idle':
            variant['group_packet_cases']=[check_groups(w) for w in (image('compact'),WORK/mode)]
    return out


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('output',type=Path)
    p.add_argument('--modes',nargs='+',choices=MODES,default=MODES)
    a=p.parse_args()
    a.output.write_text(json.dumps(analyze(a.temp,a.modes),indent=2)+'\n',encoding='utf8',newline='\n')
