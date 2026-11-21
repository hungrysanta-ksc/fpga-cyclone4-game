"""Compare whole displays, exact pre-SEAL address coverage and terminal receipts."""
import argparse
import json
from pathlib import Path

from analyze_nes_section909 import coverage, measure, read_csv
from analyze_nes_section910 import guards, ms
from analyze_nes_rows911 import stop_edges
from test_nes_service509_schedule import Calendar
from guard_nes_output852 import run
from nes_prefetch912 import BASE, OUT, once, peer
from nes_section910 import DIRECT


def cases(temp,mode):
    rows={}
    for phase in (1,2):
        for state in ('warm','cold'):
            def path(tag):
                return temp/f'nes-tile821-obj-jointmirror-p{phase}-{tag}-{state}-pair'
            names=('907','911ahead',mode)
            runs=[measure(path(tag),DIRECT if tag=='912bframed' else BASE) for tag in names]
            reference,packets=runs[0]
            candidate,stream=runs[-1]
            assert candidate['parameters']==reference['parameters']
            for g in packets:
                for tile in (True,False):
                    assert ([b for b in packets[g] if (b[0]==7)==tile] ==
                            [b for b in stream[g] if (b[0]==7)==tile])
                assert peer.sha(path(mode)/f'frame-{g}.rgb')==peer.sha(path('907')/f'frame-{g}.rgb')
            comparisons=[]
            for tag,(r,_) in zip(names,runs):
                focal=r['frames'][912]
                times=focal['masterclocks']
                accepted=focal['section5_pair'][-1]
                assert accepted['bytes']==240
                pre=coverage(r['preDMA'][912])
                prior=coverage(reference['preDMA'][912])
                if tag=='912bleading' and state=='cold':
                    assert len(pre)==496 and pre.keys()==prior.keys()
                    assert all(pre[k]<=prior[k] for k in prior)
                    assert r['intervals']==17 and r['final_ACK']<reference['final_ACK']
                    assert {(off,n) for kind,off,n,_ in r['preDMA'][912] if kind=='tile'} >= {(36000,288),(33856,32)}
                spans={}
                for g,f in r['frames'].items():
                    assert f['section5_hash']==reference['frames'][g]['section5_hash']
                    old=coverage(reference['preDMA'][g]);new=coverage(r['preDMA'][g])
                    spans[g]=dict(reveal=f['VBlank'][3],pre_bytes=len(new),lost=len(old.keys()-new.keys()),
                                  delayed=sum(new[k]>old[k] for k in old.keys()&new.keys()))
                window=read_csv(path(tag),'window.csv')
                focal_seal=[e for e in window if e['op']=='3' and e['g']=='912']
                beam={e['event']:[int(e['frame']),int(e['line']),int(e['clock'])] for e in focal_seal
                      if e['event'] in ('load','validate181','coverage212','wait169','final212','ack')}
                starts=[v for v in window if int(v['g'])>=906 and v['event']=='ppu_dma' and v['op'] in ('3','-1')]
                ends=[v for v in window if int(v['g'])>=906 and v['event']=='ppu_last' and v['op'] in ('3','-1')]
                assert len(starts)==len(ends)
                for a,b in zip(starts,ends):
                    assert (a['g'],a['op'],a['frame'])==(b['g'],b['op'],b['frame'])
                    assert 225<=int(a['line'])<=int(b['line'])<262,(tag,a,b)
                comparisons.append(dict(tag=tag,intervals=r['intervals'],ACK=r['final_ACK'],
                    beam=beam,seal_clock=times['SEAL'],reveal_clock=times['show'],
                    ACK_delta_ms=ms(r['final_ACK']-reference['final_ACK']),
                    E0_delta_ms=ms(times['E0_response']-reference['frames'][912]['masterclocks']['E0_response']),
                    table_to_SEAL_ms=ms(times['SEAL']-accepted['accept']),
                    SEAL_to_reveal_ms=ms(times['show']-times['SEAL']),
                    prior_early_addresses_preserved=len(prior.keys()&pre.keys()),preDMA=r['preDMA'][912],
                    active_DMA_pairs=len(starts),frames=spans))
            rows[f'{phase}-{state}']=comparisons
    return rows


def stop_test(temp,tag,client):
    trial=temp/f'nes-tile821-obj-jointmirror-p1-{tag}-warm-pair'
    def adapt(s,labels):
        s=once(s,"if not injected852 then","if not injected852 and packet and pb(0)==3 and pw(8)==909 then")
        s=once(s,"end,emu.callbackType.exec,"+str(labels['column_service'])+")",
               "end,emu.callbackType.exec,"+str(labels['group_wait912'])+")")
        return once(s,"  assert(captured==commits)","  assert(injected852);assert(captured==commits)")
    return run(temp,trial,'stop',column_client=client,select_packet=lambda b,g:g==909 and b[0]==3,
               adapt_lua=adapt,output_name='group-stop')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('tag')
    p.add_argument('output',type=Path)
    p.add_argument('--stop',action='store_true')
    p.add_argument('--bad-seal',action='store_true')
    p.add_argument('--matrix',action='store_true',
                   help='collect all four linked comparisons and the two completed guard runs')
    p.add_argument('--client',default='consumer')
    a=p.parse_args()
    trace=a.temp/f'nes-tile821-obj-jointmirror-p1-{a.tag}-cold-pair'
    if a.matrix:
        tags=['912bconsumer','912bjoint','912bleading','912bframed']
        result={}
        for tag in tags:
            for condition,group in cases(a.temp,tag).items():
                by_tag=result.setdefault(condition,{})
                for row in group:
                    if row['tag'] in by_tag:
                        assert by_tag[row['tag']]==row
                    by_tag[row['tag']]=row
        checks={}
        for name,status in [('group-stop',228),('bad-seal',224)]:
            directory=a.temp/'nes-tile821-obj-jointmirror-p1-912bleading-warm-pair'
            path=directory/('guard-'+name)
            record=json.loads((path/'result.json').read_bytes())
            assert record['passed'] and record['commits']==4 and record['last_status']==status
            assert peer.sha(path/'retained.rgb')==peer.sha(directory/'frame-908.rgb')
            checks[name]=dict(commits=4,status=status,screen_SHA256=peer.sha(path/'retained.rgb'))
        result=dict(comparisons=result,ARM=guards(BASE),direct_ARM=guards(DIRECT),guards=checks,
                    client_SHA256=peer.sha(OUT/'consumer/sink165.sfc'),
                    reader_STOP=stop_edges(a.temp/'nes-tile821-obj-jointmirror-p1-912bleading-cold-pair',
                                           Calendar(a.temp/'nes-service509-rom03')))
    elif a.stop:
        result=stop_test(a.temp,a.tag,OUT/a.client)
    elif a.bad_seal:
        trial=a.temp/f'nes-tile821-obj-jointmirror-p1-{a.tag}-warm-pair'
        def corrupt(b,g,case):
            if g!=909:
                return b,False
            # SEAL generation no longer matches the active packet ownership.
            b[8]^=1
            return b,True
        result=run(a.temp,trial,'bad-seal',column_client=OUT/a.client,edit_seal=corrupt)
    else:
        result=dict(replays=cases(a.temp,a.tag),ARM=guards(DIRECT if a.tag=='912bframed' else BASE),
                    reader_STOP=stop_edges(trace,Calendar(a.temp/'nes-service509-rom03')))
    a.output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
