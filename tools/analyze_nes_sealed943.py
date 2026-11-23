"""Match the D2 end of data, final E0/EA, commit and first BG on one clock."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import analyze_nes_chain935 as chain
from analyze_nes_head939 import first_bg
from analyze_nes_input940 import timeline
from analyze_nes_oam937 import ordinary_packets
from analyze_nes_palette921 import directory, read, read_csv, sha
from analyze_nes_rows931 import job_times
from analyze_nes_return930 import jobs
from analyze_nes_wait936 import analyze
from check_nes_sram897 import crc
from nes_sealed943 import MODES, prior, work


def boundary(folder,generation=909):
    source=timeline(folder,generation)
    show=source['previous_reveal']
    head=next(r for r in read_csv(folder,'window.csv') if r['event']=='ack' and
              int(r['g'])==generation-1 and int(r['op'])==3)
    ack=int(head['clock'])
    spi=[e for e in read(folder/'events.json') if e['event']=='SPI']
    ea=next(e for e in spi if e['opcode']=='0xea' and e['generation']==generation-1)
    inputs=[e for e in spi if e.get('input_generation')==generation]
    reads=[e for e in inputs if e['opcode']=='0xd1']
    pops=[e for e in inputs if e['opcode']=='0xd2']
    statuses=[e for e in spi if e['generation']==generation-1 and e['opcode']=='0xe0'
              and show-6000<e['clock']<=ea['start']]
    def receipt(e):
        b=bytes.fromhex(e['reply'])
        assert crc(b[1:-1],8,7,0)==b[-1]
        return (b[2]&7)==2 and b[3:5]==b[5:7] and b[7:9]==bytes((1,3)) and int.from_bytes(b[15:17],'little')==generation-1 and b[17:19]==bytes((0x65,0x9a))
    valid=next(e for e in statuses if receipt(e))
    commit=next(e for e in inputs if e['opcode']=='0xd3')
    assert show<=ack<=valid['clock']<ea['start'] and ea['clock']<commit['start']
    confirmed=next(e for e in inputs if e['opcode']=='0xd0' and pops[-2]['clock']<=e['start'])
    assert reads[-2]['clock']<=pops[-2]['start'] and confirmed['clock']<source['COMMIT']<source['commit_D2']<=source['planner']
    return dict(show=show,ack=ack,E0=round(valid['clock']),EA=source['EA'],last_data_B=reads[-2]['bytes']-3,
        last_data_D1=round(reads[-2]['clock']),data_D2=source['data_D2'],confirmed_D0=round(confirmed['clock']),
        commit=source['COMMIT'],commit_D2=source['commit_D2'],planner=source['planner'],
        first_BG=first_bg(folder,generation)['ready'],
        reads_before_show=sum(e['clock']<show for e in reads),blocks=len(reads)-1,
        E0s=[dict(start=e['start']-show,end=e['clock']-show,reply=e['reply'],valid=receipt(e)) for e in statuses])


def following_obj(folder):
    grants=[row for row in read(folder/'grants904.json') if row[:2]==[909,1]]
    tokens={token:job['clocks'] for token,job in jobs(folder,(15,16,17,18),generation=909).items()}
    heads=read_csv(folder,'window.csv')
    prior=max((h for h in heads if int(h['g'])==909 and h['event']=='ack' and
               int(h['clock'])<tokens[15]['load']),key=lambda h:int(h['clock']))
    begin=next(h for h in heads if h['event']=='load' and h['index']==prior['index'] and h['g']==prior['g'])
    return dict(first_request_grant_reply=grants[0][2:],tokens=tokens,
        head_before_token15=dict(op=int(prior['op']),section=int(prior['section']),
                                 load=int(begin['clock']),ACK=int(prior['clock'])))


def report(temp,modes):
    result=dict(clock_Hz=21477272,physical=False,consumer=sha(prior.ROM/'sink165.sfc'),cases={},links={})
    for mode in modes:
        arm=work(mode)
        fw=arm/'link/src/obj-nes-100/firmware.stm'
        link=result['links'][mode]=dict(Flash=fw.stat().st_size,firmware=sha(fw))
        frozen=arm/'frozen943.json'
        if frozen.exists():
            link['frozen_geometry']=read(frozen)
        proof=arm/'safety943.json'
        if proof.exists():
            safety=link['safety']=read(proof)
            assert safety['firmware']==sha(fw) and safety['consumer']==result['consumer']
            for name in ('dispatch938','decode940'):
                check=read(arm/(name+'.json'))
                assert check['firmware']==link['firmware']
                link[name]=check
    for cache in ('warm','cold'):
        for phase in (1,2):
            cases=result['cases'][cache+str(phase)]={}
            ref,old,base=[directory(temp,phase,tag,cache) for tag in ('935boundedfinal','940handoffdecode','942fastfit')]
            reference,old_times,prior_times=map(job_times,(ref,old,base))
            cases['935']=boundary(ref)
            cases['942']=boundary(base)
            if cache=='cold' and phase==1:
                for tag,folder in (('935',ref),('942',base)):
                    cases[tag]['following_OBJ']=following_obj(folder)
            for mode in modes:
                arm=work(mode)
                tag='943'+mode
                folder=directory(temp,phase,tag,cache)
                assert sha(folder/'client.sfc')==result['consumer'] and ordinary_packets(folder)==ordinary_packets(base)
                with patch.object(chain,'output',lambda _:prior.ROM):
                    stats=analyze(temp,mode,phase,cache,tag=tag,arm=arm)
                times=job_times(folder)
                assert reference.keys()==times.keys() and stats['other_count']==37
                late=[(k,t-reference[k]) for k,t in times.items() if k[:2] not in ((912,32),(912,35)) and t>reference[k]]
                assert len(late)==stats['later_vs935']
                marks=boundary(folder)
                if cache=='cold' and phase==1:
                    marks['following_OBJ']=following_obj(folder)
                objs=[(909,22,1,64),(909,24,1,352)]
                tile=(906,8,1,64)
                cases[mode]=dict(boundary=marks,bg_delta=marks['first_BG']-cases['935']['first_BG'],
                    token8=times[tile]-reference[tile],token8_vs942=times[tile]-prior_times[tile],
                    OBJ_vs940=[times[k]-old_times[k] for k in objs],OBJ_vs942=[times[k]-prior_times[k] for k in objs],
                    capture=stats['capture_margin'],preDMA=stats['early912'],tail=bool(stats['tail']),gaps=stats['gaps'],
                    total=stats['total'],late=late,ACK=stats['ACK912'],
                    ACK_delta=stats['ACK912']-read(ref/'joint.json')['frames'][-1]['ACK_masterclock'])
    for mode,link in result['links'].items():
        rows=[group[mode] for group in result['cases'].values()]
        link['gates']=dict(flash=link['Flash']<=212992,token8=all(r['token8']<0 for r in rows),
            OBJ_earlier_than_940=all(max(r['OBJ_vs940'])<0 for r in rows),
            OBJ_no_later_than_942=all(max(r['OBJ_vs942'])<=0 for r in rows),BG=rows[2]['bg_delta']<5176,
            warm13=all(r['total']==13 for r in rows[:2]),cold496_15=all(r['total']==15 and r['preDMA']==496 and r['tail'] for r in rows[2:]),
            capture=all(r['capture']>=0 for r in rows),tiles=all(not r['late'] for r in rows),
            ACK=all(r['ACK_delta']<=0 for r in rows))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('modes',choices=MODES,nargs='+')
    a=p.parse_args()
    a.out.write_text(json.dumps(report(a.temp,a.modes),indent=2)+'\n',encoding='utf8')
