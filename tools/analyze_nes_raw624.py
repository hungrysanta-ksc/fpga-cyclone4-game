# SPDX-License-Identifier: MIT
"""Reconcile the final ARM transaction, sealed DMA, beam decision and next ROM grant."""
import argparse
import json
from pathlib import Path

from analyze_nes_bank621 import Calendar, csv_groups, lanes, ms, one, read, schedule, sha, work
from analyze_nes_palette622 import detail
from check_nes_game478 import crc


def measure(folder, calendar, addresses):
    events=read(folder/'events.json')
    rows=csv_groups(folder/'window.csv')
    beam=csv_groups(folder/'seal528.csv')[922]
    result=schedule(folder,calendar,addresses)
    clocks={}
    for gen in (921,922):
        stream=[e for e in events if e['generation']==gen]
        sends=[e for e in stream if e.get('opcode')=='0xe1']
        assert sends[-1]['packet_opcode']==3
        seal=[r for r in rows[gen] if r['op']==3]
        stamps=dict(issue=sends[-1]['start'],push=sends[-1]['clock'])
        for event in ('load','seal','validate181','upload165_entry','final212','reveal','ack'):
            stamps[event]=one(seal,event)['clock']
        response=[e for e in stream if e.get('opcode')=='0xe0'][-1]
        status=bytes.fromhex(response['reply'])
        assert status[19]==crc(status[1:19],8,7,0) and status[3:5]==status[5:7]
        assert status[7:9]==bytes([1,3]) and int.from_bytes(status[15:17],'little')==gen
        stamps['final_status']=response['clock']
        stamps['ARM_return']=one(stream,'output_return531')['clock']
        stamps['EA_end']=next(e['clock'] for e in reversed(stream) if e.get('opcode')=='0xea')
        assert list(stamps.values())==sorted(stamps.values())
        clocks[gen]=stamps
    vram=[r for r in beam if r['event']=='dma' and r['port']==24]
    raw=one(beam,'raw_enter')['clock']
    final=one(beam,'final_credit')
    latch,=[r for r in beam if r['event']=='latch' and r['clock']>=final['clock']]
    rom=read(folder/'obj-phases.json')['923']['cache611'][0]
    kind,address,request,grant,response,mode=rom
    assert mode=='ROM' and kind==0 and calendar.select(request+1)==(grant,response)
    display=one([r for r in rows[922] if r['op']==3],'reveal')
    sealed=[r for r in rows[922] if r['op']==3 and r['event'] in ('ppu_dma','ppu_last')]
    assert len(sealed)%2==0
    for first,last in zip(sealed[::2],sealed[1::2]):
        assert (first['event'],last['event'])==('ppu_dma','ppu_last')
        assert first['frame']==last['frame'] and 225<=first['line']<=last['line']<262
    tail955=[{k:r[k] for k in ('event','frame','line','clock')} for r in rows[955] if r['op']==3
             and r['event'] in ('load','upload165_entry','wait169','final212','reveal','ack')]
    return dict(clocks=clocks,display922=display['frame'],line922=display['line'],
                beam={k:latch[k] for k in ('line','h','clock')},credit=final['bytes'],
                DMA=[{k:r[k] for k in ('dst','src','bytes','clock','line','h')} for r in vram],
                raw_B=[r['bytes'] for r in vram if r['clock']>=raw],raw_start=raw,
                raw_done=next(r['clock'] for r in beam if r['event']=='raw_done' and r['clock']>raw),
                ROM923=dict(address=address,request=request,grant=grant,response=response),
                last_ACK=result['last_ACK'],dense=result['dense_VB'],intervals=result['intervals'],tail955=tail955,
                wait957=result['final_wait_957'],map955=[result['first_map_955_B'],result['last_map_955_B']],
                ROM96=result['ROM96_in_first_window'],display906=result['g906']['display_VB'],
                same_blank957=detail(folder)['same_VBlank'],pins=result['pins'])


def compare(a):
    calendar=Calendar(a.calendar)
    addresses=[address for _,h in read(a.plans/'frame954/plans.json') for q in [bytes.fromhex(h)]
               if q[6]==0 for _,address in lanes(q)]
    phases=[]
    pinned=read(Path(__file__).resolve().parents[1]/'analysis/credit623-verification.json')
    for i in (1,2):
        dirs={k:a.traces/f'nes-{n}-{i}' for k,n in [('621','bank621-arm01'),('A','palette622-after-pack'),
              ('T','credit623-small-snapshots'),('A624','raw624-A'),('T624','raw624-T'),('621624','raw624-base')]}
        phase={k:measure(d,calendar,addresses) for k,d in dirs.items()}
        for n,key in [('A','A'),('T','small-snapshots')]:
            assert phase[n]['pins']==pinned['phases'][i-1][key]['pins']
        for n in ('621','A','T'):
            base,trial=dirs[n],dirs[n+'624']
            old,new=read(base/'joint.json'),read(trial/'joint.json')
            assert new['passed'] and new['commits']==53 and new['client_SHA256']==sha(a.client/'sink165.sfc')
            assert all(new[key]==old[key] for key in ('parameters','firmware_SHA256','ROM_read_allocations','vram_DMA_B'))
            assert work(base)==work(trial)
            for gen in range(905,958):
                for filename in (f'frame-{gen}.rgb',f'map-{gen}.bin'):
                    assert sha(base/filename)==sha(trial/filename)
            r=phase[n+'624']
            assert r['raw_B']==phase[n]['raw_B']==[64,64,64]
            if n!='621':
                fixed=read(a.traces/f'nes-raw624-probe-{n}-{i}/audit.json')
                assert fixed['reference']['ack']['clock']==phase[n]['clocks'][922]['ack']
                assert fixed['reference']['load']==fixed['candidate']['load'] and fixed['matched_prefix']>0
                r['fixed_arrivals']=fixed
            r['ACK_delta_ms']={k:ms(r['last_ACK']-phase[k]['last_ACK']) for k in ('A','T','621')}
            r['first_ROM_delta_ms']={k:ms(r['ROM923']['response']-phase[k]['ROM923']['response']) for k in ('A','T')}
            r['guards']=bool(r['display906']==9 and r['wait957']==0 and r['intervals'][952]==r['intervals'][954]==4
                             and r['map955']==[192,384] and r['ROM96']==96)
            r['recovered_vs_T']=bool(r['guards'] and r['display922']<=phase['A']['display922']
                                      and r['first_ROM_delta_ms']['T']<0 and r['ACK_delta_ms']['T']<0)
            r['ahead_of_controls']=r['recovered_vs_T'] and max(r['ACK_delta_ms'].values())<0
        phases.append(phase)
    edges=read(a.traces/'nes-raw624-edges/edges.json')
    assert {r['case'] for r in edges if r['grant']==0}>={'stop','head','both'}
    assert {(r['generation'],r['fault']) for r in edges if 'fault' in r}=={(g,f) for g in (906,907) for f in ('missing','duplicate')}
    stop=read(a.traces/'nes-raw624-stop-final/result.json')+read(a.traces/'nes-raw624-stop-banks/result.json')
    assert all(r['status']==0xe4 for r in stop)
    assert {(r['generation'],r['boundary']) for r in stop if r['boundary'].startswith('row624')}=={
        (g,f'row624_{j}') for g in (907,922) for j in range(3)}
    out=dict(phases=phases,priority=edges,STOP=stop,client=read(a.client/'build.json'))
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('traces','calendar','plans','client','out'):
        p.add_argument('--'+key,type=Path,required=True)
    compare(p.parse_args())
