"""Join the physical OBJ token, checked E8, queued E1, SNES load and consume."""
import argparse
import json
from pathlib import Path

from analyze_nes_deadline922 import measure
from analyze_nes_palette921 import coverage, directory, read, read_csv, sha
from nes_deadline922 import image
from nes_obj923 import BASE, MODES, WORK, client
from test_nes_raw506_joint import MASTER, crc


def tiles(folder):
    events=read(folder/'events.json')
    heads=[(e,bytes.fromhex(e['reply'])) for e in events if e.get('generation')==909 and e.get('opcode')=='0xe8']
    e1=[e for e in events if e.get('generation')==909 and e.get('packet_opcode')==7]
    packets=[p for row in (folder/'packets.jsonl').read_text().splitlines()
             if (p:=bytes.fromhex(json.loads(row)[2]))[0]==7 and int.from_bytes(p[8:10],'little')==909]
    jobs=[j for row in (folder/'producer.jsonl').read_text().splitlines() if (j:=json.loads(row))['generation']==909]
    returns=dict(read(folder/'returns904.json'))
    loads=[r for r in read_csv(folder,'window.csv') if r['g']=='909' and r['op']=='7' and r['event']=='load']
    out=[]
    for j,p,issue,load in zip(jobs,packets,e1,loads,strict=True):
        token=int.from_bytes(p[16:20],'little')
        assert j['token']==token
        desc=bytes((1,p[1]))+p[14:16]+p[10:12]+p[8:10]+p[16:20]
        polled,rx=next((e,b) for e,b in heads if b[6:18]==desc)
        assert crc(rx[1:19],8,7,0)==rx[19] and rx[1:3]==bytes((0xd7,4))
        times=[round(j['producer']),round(polled['clock']),round(issue['clock']),int(load['clock']),returns[token]]
        assert times==sorted(times) and (not out or times[1]>=out[-1]['clocks'][-1])
        out.append(dict(token=token,section=p[1],offset=int.from_bytes(p[10:12],'little'),bytes=j['bytes'],clocks=times))
    return out


def analyze(temp,modes):
    result=dict(master_Hz=MASTER,token_clocks=['ready','first_valid_E8','E1_end','SNES_load','physical_return'],variants={})
    for phase in (1,2):
        for cache in ('warm','cold'):
            key=f'{phase}-{cache}'
            control,workload=measure(directory(temp,phase,'920reference',cache),image('baseline'))
            for name in ('922',*modes):
                arm=BASE if name=='922' else WORK/name
                tag='922firstrow' if name=='922' else '923'+name
                folder=directory(temp,phase,tag,cache)
                row,check=measure(folder,arm)
                # Batching may move distinct slots across E9 boundaries. Every
                # destination byte, scene image and section must still match.
                assert all(check[k]==workload[k] for k in workload if k!='batches')
                assert all(0<count<=15 for batch in check['batches'].values() for count in batch)
                jobs=tiles(folder)
                f=row['frames']
                pre=coverage(f[912]['preDMA'])
                fw=arm/'link/src/obj-nes-100/firmware.stm'
                v=result['variants'].setdefault(name,dict(firmware=sha(fw),flash=fw.stat().st_size,cases={}))
                v['cases'][key]=dict(jobs909=jobs,batches909=check['batches']['909'],gaps=row['gaps'],
                    display908=row['display908'],intervals=row['intervals'],ack912=row['final_ACK'],
                    dma912_B=len(pre),same912=pre.keys()==coverage(control['frames'][912]['preDMA']).keys(),
                    ack_gain=control['final_ACK']-row['final_ACK'],interval_gain=control['intervals']-row['intervals'],
                    begin910=f[910]['source_begin'],D1_910=f[910]['first_D1'],last_D2_910=f[910]['commit_D2'],
                    D2_capture_offset=f[910]['D2_minus_nearest_capture'],capture911=f[911]['capture_ready'],
                    seal911=f[911]['clocks']['SEAL'],display911=f[911]['VBlank'][3],
                    data_D2_910=f[910]['data_D2'],ack909=f[909]['clocks']['ACK'],e0_909=f[909]['clocks']['E0_response'],
                    residual909=f[909]['residual_DMA'],early909=f[909]['preDMA'])
                # A merged token can return two original 32-byte destinations.
                # Compare at equal addresses even when token numbers change.
                slot_returns={offset:j['clocks'][-1] for j in jobs if j['section']==1
                              for offset in range(j['offset'],j['offset']+j['bytes'],32)}
                baseline=result['variants']['922']['cases'][key]['jobs909']
                v['cases'][key]['small_OBJ_return_gain']={
                    j['offset']:j['clocks'][-1]-slot_returns[j['offset']]
                    for j in baseline if j['section']==1 and j['bytes']==32}
    for v in result['variants'].values():
        v['passes']=v['flash']<=212992 and all(
            r['interval_gain']>0 and r['ack_gain']>0 and
            (r['same912'] and r['dma912_B']==496 if k.endswith('cold')
             else r['display908']<=result['variants']['922']['cases'][k]['display908'])
            for k,r in v['cases'].items())
        v['warm_faster_cold_held']=v['flash']<=212992 and all(
            r['ack_gain']>0 and (r['intervals']<=16 and r['same912'] and r['dma912_B']==496
            if k.endswith('cold') else r['interval_gain']>0 and r['display908']<=result['variants']['922']['cases'][k]['display908'])
            for k,r in v['cases'].items())
    return result


def recovery(mode,work=WORK,*,trial=None):
    trial=trial or work/mode
    proof=trial/'proof'
    digest=sha(trial/'link/src/obj-nes-100/firmware.stm')
    assert all(read(proof/f)['firmware']==digest for f in ('loader.json','menu.json','timer.json'))
    base=read(proof/'base/result.json')
    assert base['safe_return'] and base['firmware_sha256']==digest
    assert read(proof/'menu.json')['rows']['normal']['released'] and read(proof/'timer.json')['passed']
    rx=read(proof/'sram.json')['cases']
    assert len(rx['normal']['d0_sites'])==4 and rx['normal']['checked_retire'] and not rx['bad-crc']['checked_retire']
    faults=read(work/f'{mode}-guards.json')
    assert faults=={name:dict(status=status,commits=n) for name,status,n in
                    [('stop-copy',228,3),('descriptor',224,3),('duplicate',224,3),('seal',224,4),('display_stop',228,4)]}
    stops=read(work/f'{mode}-stops.json')
    assert stops=={str(n):dict(status=228,commits=4) for n in (32,352)}
    return dict(firmware=digest,consumer=sha(client('first')/'sink165.sfc'),SRAM_D0_sites=4,
                CRC_rejected=True,STOP=faults,last_byte_STOP=stops,menu=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('--modes',choices=MODES,nargs='+',default=MODES)
    p.add_argument('--recovery',choices=MODES,nargs='*',default=[])
    args=p.parse_args()
    if not set(args.recovery)<=set(args.modes):
        p.error('--recovery must name variants included in --modes')
    results=analyze(args.temp,args.modes)
    for mode in args.recovery:
        results['variants'][mode]['recovery']=recovery(mode)
    args.out.write_text(json.dumps(results,indent=2)+'\n',encoding='utf8',newline='\n')
