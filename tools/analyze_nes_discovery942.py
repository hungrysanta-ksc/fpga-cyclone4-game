"""Compare the same 909 descriptor's SPI sampling, returns and display deadlines."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_chain935 as chain
from analyze_nes_oam937 import ordinary_packets
from analyze_nes_palette921 import directory, read, sha
from analyze_nes_input940 import timeline
from analyze_nes_head939 import first_bg
from analyze_nes_return930 import jobs
from analyze_nes_rows931 import job_times
from analyze_nes_wait936 import analyze
from nes_discovery942 import ROM, work, MODES


def discovery(folder):
    records=jobs(folder,(19,20,22,24),generation=909)
    entry=records[19]['clocks']
    ready=entry['ready']
    e8=entry['E8']
    spi=[e for e in read(folder/'events.json') if e['event']=='SPI' and e['generation']==909]
    before=max(i for i,e in enumerate(spi) if e['start']<=ready)
    after=next(i for i,e in enumerate(spi) if round(e['clock'])==e8 and e['opcode']=='0xe8')
    assert before<=after
    rows=[]
    for e in spi[max(0,before-1):after+3]:
        row=dict(op=e['opcode'],start=round(e['start']),end=round(e['clock']),size=e['bytes'])
        if e['opcode']=='0xe8':
            rx=bytes.fromhex(e['reply'])
            row.update(valid=rx[6],token=int.from_bytes(rx[14:18],'little'))
        rows.append(row)
    # Count only the portion on the shared bus between READY and the first
    # checked descriptor response. The remainder includes ARM work and pacing.
    busy=sum(max(0,min(e['clock'],e8)-max(e['start'],ready)) for e in spi[before:after+1])
    credit=next(e for e in reversed(spi[:after]) if e['opcode']=='0xe0')
    return dict(bus_clocks=round(busy),off_bus_clocks=e8-ready-round(busy),
                previous_credit=dict(start=round(credit['start']),end=round(credit['clock']),reply=credit['reply']),
                after_ready_E1=entry['E1']-ready,tiles={t:r['clocks'] for t,r in records.items()},SPI=rows,
                first_E8_after_ready=e8-ready,
                last_packet_before_ready=next(e for e in reversed(spi[:before+1]) if e['opcode']=='0xe1'))


def report(temp,modes):
    controls=('935boundedfinal','940handoffdecode','941prefix')
    report=dict(clock_Hz=21477272,physical=False,consumer=sha(ROM/'sink165.sfc'),modes={})
    cases=[(c,p) for c in ('warm','cold') for p in (1,2)]
    for mode in modes:
        arm=work(mode)
        fw=arm/'link/src/obj-nes-100/firmware.stm'
        result=report['modes'][mode]=dict(Flash=fw.stat().st_size,firmware=sha(fw),cases={})
        if (arm/'safety942.json').exists():
            result['safety']=read(arm/'safety942.json')
            assert result['safety']['consumer']==report['consumer'] and result['safety']['firmware']==sha(fw)
        for c,p in cases:
            ref,old,source=[directory(temp,p,tag,c) for tag in controls]
            current=directory(temp,p,'942'+mode,c)
            assert sha(current/'client.sfc')==report['consumer']
            assert ordinary_packets(current)==ordinary_packets(old)
            with patch.object(chain,'output',lambda _:ROM):
                checked=analyze(temp,mode,p,c,tag='942'+mode,arm=arm)
            key=c+str(p)
            times,base,previous,prefix=[job_times(d) for d in (current,ref,old,source)]
            assert times.keys()==base.keys()==previous.keys()==prefix.keys()
            late=[(k,t-base[k]) for k,t in times.items() if k[:2] not in ((912,32),(912,35)) and t>base[k]]
            assert checked['other_count']==37 and len(late)==checked['later_vs935']
            token=(906,8,1,64)
            objs=[(909,22,1,64),(909,24,1,352)]
            row=result['cases'][key]=dict(gaps=checked['gaps'],total=checked['total'],preDMA=checked['early912'],
                tail=bool(checked['tail']),capture=checked['capture_margin'],late=late,
                ACK=checked['ACK912'],ACK_delta=checked['ACK912']-read(ref/'joint.json')['frames'][-1]['ACK_masterclock'],
                token8_delta935=times[token]-base[token],token8_delta941=times[token]-prefix[token],
                OBJ_delta940=[times[k]-previous[k] for k in objs],OBJ_delta935=[times[k]-base[k] for k in objs])
            if mode in ('fastfit','handoff','borrow'):
                row['first_BG_delta935']={}
                for generation in (907,909):
                    x,y=first_bg(current,generation),first_bg(ref,generation)
                    delta={k:x[k]-y[k] for k in ('source_begin','planner','first_E9','ready')}
                    x,y=timeline(current,generation),timeline(ref,generation)
                    delta.update({k:x[k]-y[k] for k in ('previous_reveal','first_D1','data_D2','EA','COMMIT','commit_D2')})
                    row['first_BG_delta935'][generation]=delta
            if key in ('warm1','cold2'):
                generation=909 if key=='warm1' else 911
                now,baseline=[timeline(d,generation) for d in (current,old)]
                row['input_delta940']={k:now[k]-baseline[k] for k in ('begin_minus_show','first_D1','begin_to_planner','planner')}
            if key=='cold1':
                row['discovery']=discovery(current)
                if 'controls' not in report:
                    report['controls']={tag:discovery(d) for tag,d in zip(controls,(ref,old,source))}
        rows=list(result['cases'].values())
        result['gates']=dict(Flash=result['Flash']<=212992,
            token8=all(r['token8_delta935']<0 for r in rows),
            cold1_OBJ=max(rows[2]['OBJ_delta940'])<=0,
            all_OBJ=all(max(r['OBJ_delta940'])<=0 for r in rows),
            warm13=all(r['total']==13 for r in rows[:2]),
            cold15_496=all(r['total']==15 and r['preDMA']==496 and r['tail'] for r in rows[2:]),
            capture=all(r['capture']>=0 for r in rows),all_tiles=all(not r['late'] for r in rows),
            ACK=all(r['ACK_delta']<=0 for r in rows))
        result['qualified']=all(result['gates'].values()) and len(result.get('safety',{}).get('edge',{}))==4
    return report


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.modes),indent=2)+'\n',encoding='utf8')
