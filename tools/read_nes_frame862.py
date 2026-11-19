"""Decode MMC862/863 hardware traces and decompose the matched mean in milliseconds."""
import argparse
import json
import struct
from collections import defaultdict
from pathlib import Path
from statistics import mean

KINDS=('BG','OBJ','map','raw','palette','OAM')
PERIOD=1000/60.0988
ROW=struct.Struct('<4I4H4B44s')
TICK=256/84000


def decode(path):
    data=path.read_bytes()
    magic,edition,n,dropped=struct.unpack_from('<4H',data)
    control=bool(edition&0x8000)
    edition &= 0x7fff
    if magic!=0x8621 or edition not in (862,863) or n>8192//ROW.size or len(data)!=8+n*ROW.size:
        raise ValueError('unrecognized or truncated trace')
    rows=[]
    for fields in ROW.iter_unpack(data[8:]):
        start,rx,finish,probe,tick,gen,bg,obj,dirty,seal,good,bank,wire=fields
        mask=wire[4]&63
        gaps=wire[4]>>6
        row=dict(tick=tick,gen=gen,BG=bg,OBJ=obj,map=dirty,bank=bank,seal_B=seal,
                 probe_ms=probe/84000,gaps=gaps)
        rows.append(row)
        if control:
            total=((finish-start)&0xffffffff)/84000
            e0=((rx-start)&0xffffffff)/84000
            if not (3500<=tick<4000 and good==1 and bank<2 and seal in (72,168) and not any(wire)
                    and not probe and 0<=e0<=total<65536*TICK):
                row['invalid']='incomplete control';continue
            row.update(total=total,E0=e0,parts=dict(to_E0=e0,after_E0=total-e0))
            continue
        if not (3500<=tick<4000 and good==1 and bank<2 and seal in (72,168)
                and wire[1:4]==b'\x86\x21\x0f' and int.from_bytes(wire[5:7],'little')==gen and mask):
            row['invalid']='window, incomplete capture, or generation';continue
        clocks=struct.unpack_from('<16H',wire,7)
        total=((finish-start)&0xffffffff)/84000
        e0=((rx-start)&0xffffffff)/84000
        # Clock origin is the checked ARM E0 completion. The board stamps its
        # trailing chip-select edge, before the fixed ARM return/cleanup path.
        def at(c):
            return e0-((clocks[3]-c)&65535)*TICK
        load,reveal,ack=map(at,clocks[:3])
        bands={k:(at(clocks[4+i*2]),at(clocks[5+i*2])) for i,k in enumerate(KINDS) if mask&(1<<i)}
        first=min(x for x,_ in bands.values())
        last=max(y for _,y in bands.values())
        if not (-0.02<=load<=first<=last<=reveal<=ack<=e0<=total<65536*TICK and
                all(x<=y for x,y in bands.values())):
            row['invalid']='timestamp order/wrap';continue
        def blank(t):
            delta=reveal-t
            v=round(delta/PERIOD)
            if abs(delta-v*PERIOD)>3.0:
                raise ValueError('DMA outside plausible NTSC VBlank')
            return -v
        try:
            row['DMA']={k:dict(first_ms=x,last_ms=y,first_relative_VBlank=blank(x),
                               last_relative_VBlank=blank(y)) for k,(x,y) in bands.items()}
        except ValueError as exc:
            row['invalid']=str(exc);continue
        gap=0.
        if gaps>1:
            row['invalid']='multiple DMA gaps; first gap only recorded';continue
        if gaps:
            x,y,kinds=struct.unpack_from('<HHB',wire,39)
            left,right=kinds>>3,kinds&7
            x,y=at(x),at(y)
            if max(left,right)>=6 or KINDS[left] not in bands or KINDS[right] not in bands or not first<=x<y<=last:
                row['invalid']='invalid DMA gap endpoints';continue
            gap=y-x
            row['boundary']=KINDS[left]+' -> '+KINDS[right]
            row['gap_endpoints_ms']=[x,y]
        if bool(gaps)!=(blank(first)!=blank(last)):
            row['invalid']='gap and VBlank disagree';continue
        row.update(total=total,SEAL=load,first=first,last=last,reveal=reveal,ack=ack,E0=e0,
                   parts=dict(to_SEAL=load,to_DMA=first-load,DMA_same_blank=last-first-gap,
                              DMA_interblank=gap,to_reveal=reveal-last,to_ACK=ack-reveal,
                              to_E0=e0-ack,after_E0=total-e0))
    return dict(edition=edition,control=control,dropped=dropped,rows=rows)


def compare(a,b,width,by_generation=False):
    if a['control']!=b['control']:raise ValueError('mismatched observation modes')
    def groups(report):
        d=defaultdict(list)
        for r in report['rows']:
            if 'invalid' not in r:
                d[((r['gen'] if by_generation else None),r['bank'],*(r[k]//w for k,w in zip(('BG','OBJ','map'),width)))].append(r)
        return d
    ga,gb=groups(a),groups(b)
    common={k:min(len(ga[k]),len(gb[k])) for k in ga.keys()&gb.keys()}
    n=sum(common.values())
    out=dict(width=width,matched_per_edition=n,strata=len(common))
    if not n:return out
    def avg(groups,fn):
        return sum(w*mean(fn(r) for r in groups[k]) for k,w in common.items())/n
    def diff(fn):
        return avg(gb,fn)-avg(ga,fn)
    names=ga[next(iter(common))][0]['parts']
    delta={k:diff(lambda r:r['parts'][k]) for k in names}
    labels={r['boundary'] for g in (ga,gb) for k in common for r in g[k] if 'boundary' in r}
    gap_by_kind={k:diff(lambda r:r['parts']['DMA_interblank'] if r.get('boundary')==k else 0) for k in sorted(labels)}
    assert abs(sum(delta.values())-diff(lambda r:r['total']))<1e-6
    assert abs(sum(gap_by_kind.values())-delta.get('DMA_interblank',0))<1e-6
    return dict(**out,total_delta_ms=diff(lambda r:r['total']),stage_delta_ms=delta,
                gap_delta_by_DMA_ms=gap_by_kind,mean_work={k:[avg(g,lambda r:r[k]) for g in (ga,gb)]
                for k in ('map','OBJ','BG')},mean_probe_ms=[avg(g,lambda r:r['probe_ms']) for g in (ga,gb)])


def same_screen(a,b):
    """Only pair unambiguous generation/bank identities with identical work."""
    def index(run):
        out=defaultdict(list)
        for row in run['rows']:
            if 'invalid' not in row:
                out[(row['gen'],row['bank'],row['map'],row['OBJ'],row['BG'])].append(row)
        return out
    left,right=index(a),index(b)
    rows=[]
    for key in sorted(left.keys()&right.keys()):
        if not len(left[key])==len(right[key])==1:continue
        x,y=left[key][0],right[key][0]
        rows.append(dict(generation=key[0],bank=key[1],map=key[2],OBJ=key[3],BG=key[4],
                         output_delta_ms=y['total']-x['total'],
                         DMA_crossing=[x.get('boundary'),y.get('boundary')],
                         stage_delta_ms={k:y['parts'][k]-v for k,v in x['parts'].items()}))
    return rows


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('a',type=Path);p.add_argument('b',type=Path)
    p.add_argument('--controls',nargs=2,type=Path,metavar=('CTL862','CTL863'))
    args=p.parse_args()
    a,b=map(decode,(args.a,args.b))
    if (a['edition'],b['edition'])!=(862,863):raise ValueError('expected MMC862 then MMC863')
    result=dict(same_generation_work=same_screen(a,b),exact=compare(a,b,(1,1,1)),
                invalid=[sum('invalid' in r for r in run['rows']) for run in (a,b)],
                near=compare(a,b,(8,4,2)),runs=[a,b])
    if args.controls:
        c,d=map(decode,args.controls)
        if (c['edition'],d['edition'])!=(862,863) or not (c['control'] and d['control']) or a['control'] or b['control']:
            raise ValueError('expected traced runs followed by matching control editions')
        # Use the same generation, bank and work in all four runs.
        def pairs(x,y):
            return {(r['generation'],r['bank'],r['map'],r['OBJ'],r['BG']):r['output_delta_ms']
                    for r in same_screen(x,y)}
        on,off=pairs(a,b),pairs(c,d)
        shared=sorted(on.keys()&off.keys())
        result['controls']=dict(exact=compare(c,d,(1,1,1)),same_generation_work=same_screen(c,d),
                                invalid=[sum('invalid' in r for r in run['rows']) for run in (c,d)],
                                dropped=[c['dropped'],d['dropped']],four_way_n=len(shared),
                                probe_effect_on_delta_ms=mean(on[k]-off[k] for k in shared) if shared else None)
    print(json.dumps(result,indent=2))
