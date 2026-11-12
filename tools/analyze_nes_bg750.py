# SPDX-License-Identifier: MIT
"""Verify fixed and live schedules against the 727 clocks and the matched 749 workload."""
import argparse
from collections import defaultdict
import csv
import json
from hashlib import sha256
from pathlib import Path

from analyze_nes_owner739 import csv_groups, ms, packets, read, sha
from analyze_nes_receipt742 import cpu_frame, whole
from prepare_nes_longrun694 import codec, optimal
from replay_nes_bg750 import edits


def counters(path):
    with path.open() as f:
        return [{k:int(v) for k,v in r.items()} for r in csv.DictReader(f)]


def measure(folder, reference, fixed):
    windows=csv_groups(folder/'window.csv')
    starts=counters(folder/'dma748.csv')
    assert read(folder/'result.json')['commits']==53
    for g in range(905,958):
        assert sha(folder/f'frame-{g}.rgb')==sha(fixed/f'frame-{g}.rgb')
    def event(g,name):
        return next(r for r in windows[g] if r['op']==3 and r['event']==name)
    def transfer(g,source,size):
        row,=[r for r in starts if (r['g'],r['source'],r['bytes'])==(g,source,size)]
        i=next(i for i,e in enumerate(windows[g]) if e['event']=='ppu_dma' and e['clock']>=row['clock'])
        first=windows[g][i]
        assert first['value']==size and first['clock']-row['clock']<120
        end=next(e for e in windows[g][i+1:] if e['event']=='ppu_last')
        assert first['frame']==end['frame'] and 225<=row['line']<=end['line']<=261
        return dict(clock=row['clock'],line=row['line'],h=row['h'],frame=first['frame'],
                    last_write=end['clock'],end_line=end['line'])
    map952=transfer(952,0xd800,1536)
    bg=transfer(957,0x0840,48)
    longmap=transfer(957,0x5800,1536)
    obj=transfer(957,0x4aa0,288)
    assert map952['last_write']<event(952,'load')['clock'] and longmap['last_write']<event(957,'load')['clock']
    grants=counters(folder/'budget685.csv')
    budget,=[r for r in grants if r['generation']==957 and r['bytes']==1536 and r['clock']<=longmap['clock'] and longmap['clock']-r['clock']<500]
    assert 225<=budget['line']<=248 and budget['range']==1536
    seal=cpu_frame(folder,957)
    reveal=event(957,'reveal')['clock']
    ack=event(957,'ack')['clock']
    dense=ms(reveal-event(951,'reveal')['clock'])/6
    intervals={g:event(g,'reveal')['frame']-event(g-1,'reveal')['frame'] for g in (908,911,952,953,954,955,956,957)}
    assert event(951,'reveal')['line']<=246 and intervals[908]==intervals[911]==2 and intervals[952]==3 and seal['final_wait']==0
    ordered=bg['last_write']<longmap['clock']<longmap['last_write']<obj['clock']
    same=ordered and obj['frame']==longmap['frame'] and obj['line']<=257
    return dict(map952=map952,BG=bg,map957=longmap,map_grant=budget,OBJ=obj,order=ordered,by257=same,
                margin_to_258_clocks=(258-obj['line'])*1364-obj['h'] if obj['frame']==longmap['frame'] else None,
                dense_ms=dense,dense_delta_us=(dense-reference['dense_ms'])*1000,ACK=ack,
                ACK_delta=ack-reference['ACK'],intervals=intervals,final_wait957=seal['final_wait'],
                line951=event(951,'reveal')['line'],trace=sha(folder/'window.csv'))


def guards(folder,n,group):
    proof={}
    for mode in ('stopbefore','stopduring','stalenone','tracehead'):
        d=folder/f'nes-bg750-{group}{n}-{mode}'
        result=read(d/'result.json')
        window=csv_groups(d/'window.csv')[957]
        if mode=='tracehead':
            edge,index,op,sec=map(int,(d/'guard750.txt').read_text().split())
            nxt=next(r for r in window if r['clock']>edge and r['event'] in ('load','ppu_dma'))
            assert (nxt['event'],nxt['index'],nxt['op'],nxt['section'])==('load',index,op,sec)
            assert result['commits']==53 and result['last_status']==1
            proof[mode]=dict(edge=edge,first_load=nxt['clock'],op=op,section=sec)
        else:
            assert result['commits']==52 and result['last_status']==(224 if mode=='stalenone' else 0)
            assert sha(d/'retained.rgb')==sha(folder/f'nes-obj749-page{n}/frame-956.rgb')
            assert not any(r['op']==3 and r['event']=='ack' for r in window)
            dmas=counters(d/'dma748.csv')
            obj=[r for r in dmas if r['g']==957 and r['source']==19104]
            assert sum(r['bytes'] for r in obj)==(0 if mode=='stopbefore' else 288)
            if mode=='stopduring':
                edge=int((d/'guard750.txt').read_text())
                assert obj[0]['clock']<edge<=window[-1]['clock'] and window[-1]['event']=='ppu_last'
            proof[mode]=dict(status=result['last_status'],OBJ_bytes=sum(r['bytes'] for r in obj),retained=956)
    return proof


def best_prefix(body):
    # All prefixes share a suffix parse. Minimize literals (1..127) and legal
    # backreferences (3..66) separately; overlapping copies are allowed.
    matches=defaultdict(list)
    limits=[]
    for i in range(len(body)):
        short=far=0
        key=body[i:i+3]
        for j in reversed(matches[key]):
            size=3
            while i+size<len(body) and size<66 and body[i+size]==body[j+size]:
                size+=1
            far=max(far,size)
            if i-j<=255:
                short=max(short,size)
            if far==66 and (short==66 or i-j>255):
                break
        limits.append((short,far))
        matches[key].append(i)
    cost=[0]*(len(body)+1)
    cost[-1]=1  # terminator
    for i in reversed(range(len(body))):
        end=min(127,len(body)-i)
        best=min(1+n+cost[i+n] for n in range(1,end+1))
        for overhead,maxrun in zip((2,3),limits[i]):
            if maxrun>=3:
                best=min(best,overhead+min(cost[i+3:i+maxrun+1]))
        cost[i]=best
    size,prefix=min((codec.BOOT+i+cost[i],i) for i in range(2,len(body)+1,2))
    assert size==codec.BOOT+prefix+len(optimal(body,prefix))
    return dict(prefix=prefix,free=codec.STORED-size)


def run(a):
    prior=read(Path('analysis/obj749-verification.json'))
    out=dict(stage=750,board='707D',firmware=prior['ARM']['page']['sha'],phases={},ROM={})
    for n in (1,2):
        fixed=a.temp/f'nes-obj749-page{n}'
        ref=prior['phases'][str(n)]['ref']
        rows=out['phases'][n]={}
        for v in ('control','bg','full','chain','compact','tail'):
            d=a.temp/f'nes-bg750-{v}{n}-trace'
            assert read(d/'audit.json')['frames']==53
            rows[v]=measure(d,ref,fixed)
            assert sha(d/'arrivals.tsv')==sha(a.temp/f'nes-bg750-control{n}-trace/arrivals.tsv')
        rows['fixed_guards']=guards(a.temp,n,'tail')
        rows['live_guards']=guards(a.temp,n,'coupled')
        live=a.temp/f'nes-bg750-live{n}'
        r=whole(live,a.temp/f'nes-pair727-a{n}')
        assert r['firmware']==out['firmware']
        measured=rows['live']=measure(live,ref,fixed)
        def e8(folder):
            return next(e for e in read(folder/'events.json') if e.get('generation')==957 and e.get('opcode')=='0xe8'
                        and e['reply']==prior['phases'][str(n)]['page']['E8_reply'])
        old,new=e8(fixed),e8(live)
        assert old==new
        baseline_offers=packets(fixed)[957]
        live_offers=packets(live)[957]
        assert [(h,b) for h,b,_ in live_offers]==[(h,b) for h,b,_ in baseline_offers]
        measured['retimed_packets']=[dict(index=i,op=h[0],section=h[1],delta=t-old_t)
                                     for i,((h,_,t),(_,_,old_t)) in enumerate(zip(live_offers,baseline_offers))
                                     if t!=old_t]
        measured.update(E8_start=new['start'],E8_end=new['clock'],E8_reply=new['reply'],
                        ARM_instructions=r['ARM_instructions'],wire_B=r['wire_B'],live_events=sha(live/'events.json'),
                        joint=sha(live/'joint.json'),MDMAEN=sha(live/'dma748.csv'),script=sha(live/'capture.lua'))
    for v in ('control','bg','full','chain','compact','tail'):
        body=bytearray((a.client/'body.bin').read_bytes())
        for site,data in sorted(edits(a.client,v).items()):
            at=site-codec.DEST
            assert at<=len(body)
            body[at:at+len(data)]=data
        out['ROM'][v]=dict(body=len(body),sha256=sha256(body).hexdigest(),best=best_prefix(bytes(body)),free={prefix:codec.STORED-codec.BOOT-prefix-len(optimal(bytes(body),prefix))
                                               for prefix in (512,96,2)})
    menu=read(a.temp/'nes-bg750-menu.json')
    assert menu['firmware']==out['firmware'] and len(menu['rows'])==5 and menu['marker_cases']==4
    out['menu']=menu
    out['schedule_pass']=all((v:=r['live'])['by257'] and v['dense_delta_us']<0 and v['ACK_delta']<0 for r in out['phases'].values())
    out['production_selected']=False
    a.out.write_text(json.dumps(out,indent=2)+'\n',encoding='utf8',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('temp','client','out'):
        p.add_argument('--'+key,type=Path,required=True)
    run(p.parse_args())
