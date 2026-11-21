"""Read same-generation hardware timestamps and compare the two Adventure Island IV runs."""
import argparse
import json
import math
import struct
from pathlib import Path

HEADER=struct.Struct('<8H')
ROW=struct.Struct('<6H4B26s')
TICK=512/84000
PERIOD=1000/60.0988
BLANK=2.45  # conservative NTSC blank duration, includes variation in reveal scanline
ORDER=('input','map_head','tile_head','map_retired','tile_retired','SEAL','DMA_end','show','ACK','E0')


def read_trace(path):
    data=path.read_bytes()
    magic,edition,mode,count,d0,d1,size,capacity=HEADER.unpack_from(data)
    if not (magic==0x9001 and edition in (900,901) and mode<=3 and size==ROW.size
            and capacity==194 and count<=capacity and len(data)==16+size*count):
        raise ValueError(f'{path}: invalid or truncated log')
    rows=[]
    for tick,g,bg,ia,ea,probe,obj,dirty,valid,bank,wire in ROW.iter_unpack(data[16:]):
        window=30 if 3000<=tick<3500 else 55 if 5500<=tick<6000 else None
        row=dict(window=window,tick=tick,generation=g,bank=bank,map=dirty,OBJ=obj,BG=bg,probe_ms=probe*TICK)
        rows.append(row)
        if not window or valid&3!=3 or bank>1:
            row['invalid']='window/input/ACK';continue
        if mode==3:
            if valid!=3 or any(wire):row['invalid']='control unexpectedly queried'
            continue
        flags=wire[2]
        if not (valid==7 and wire[1]==0x90 and int.from_bytes(wire[3:5],'little')==g and
                flags&0x3c==0x3c and flags&3==flags>>6 and wire[25]==0):
            row['invalid']='FPGA identity, event coverage or collision';continue
        stamps=struct.unpack_from('<10H',wire,5)
        # All FPGA values use one free-running clock. ARM times are measured before the
        # query. Its opcode reaches the FPGA somewhere within the measured probe duration.
        age=lambda i:((stamps[9]-stamps[i])&65535)*TICK
        t={key:-age(i) for i,key in enumerate(('map_head','tile_head','SEAL','DMA_end','show',
                                                'ACK','previous_show','map_retired','tile_retired'))
           if i not in (0,1,7,8) or flags & (1 if i in (0,7) else 2)}
        if not(t['previous_show']<t['show']<=t['ACK'] and t['DMA_end']<=t['show'] and t['SEAL']<=t['show']
               and all(t[k+'_head']<=t[k+'_retired']<=t['SEAL'] for k in ('map','tile') if k+'_head' in t)):
            row['invalid']='out of order or stale stamps';continue
        span=t['show']-t['previous_show']
        gaps=round(span/PERIOD)
        if gaps<1 or abs(span-gaps*PERIOD)>BLANK:
            row['invalid']='unresolved display interval';continue
        row['VBlanks']=gaps
        # Elapsed times use previous display as zero; retain anchor uncertainty for both ARM events.
        prev=t['previous_show']
        bounds={k:[round(v-prev,3)]*2 for k,v in t.items()}
        for key,a in [('input',ia),('E0',ea)]:
            bounds[key]=[round(-(a+probe+2)*TICK-prev,3),round(-max(0,a-1)*TICK-prev,3)]
        row['elapsed_ms']=bounds
        vb={}
        for key,(lo,hi) in bounds.items():
            if key in ('show','previous_show'):vb[key]=[gaps if key=='show' else 0]*2
            elif key=='DMA_end' and abs(span-lo-round((span-lo)/PERIOD)*PERIOD)<=BLANK:
                vb[key]=[gaps-round((span-lo)/PERIOD)]*2
            else:
                vb[key]=[math.floor(lo/PERIOD),math.floor((hi+BLANK)/PERIOD)]
        row['VBlank_from_previous_show']=vb
    return dict(edition=edition,mode=mode,dropped=[d0,d1],rows=rows)


def compare(a,b):
    if [a['edition'],b['edition']]!=[900,901] or 3 in (a['mode'],b['mode']):
        raise ValueError('expected MMC900 then MMC901 measurement files')
    def keyed(run):
        out={}
        for r in run['rows']:
            if 'invalid' in r:continue
            key=tuple(r[k] for k in ('window','generation','bank','map','OBJ','BG'))
            if key in out:raise ValueError(f'ambiguous generation {key}')
            out[key]=r
        return out
    x,y=keyed(a),keyed(b)
    pairs=[]
    for key in sorted(x.keys()&y.keys()):
        old,new=x[key],y[key]
        cuts=[]
        for k in ORDER:
            u=old['VBlank_from_previous_show'].get(k);v=new['VBlank_from_previous_show'].get(k)
            if u and v and v[0]>u[1]:cuts.append(k)
        pairs.append(dict(key=key,VBlanks=[old['VBlanks'],new['VBlanks']],definitely_later=cuts,
                          reference=old['elapsed_ms'],candidate=new['elapsed_ms']))
    # Report only unique workload matches among the remaining rows. A similar
    # workload at another generation does not establish identical screen content.
    remaining=[]
    for own,other in ((x,y),(y,x)):
        groups={}
        for k in own.keys()-other.keys():
            groups.setdefault(k[:1]+k[2:],[]).append(own[k])
        remaining.append(groups)
    left,right=remaining
    work=[]
    for k in sorted(left.keys()&right.keys()):
        if len(left[k])==len(right[k])==1:
            l,r=left[k][0],right[k][0]
            work.append(dict(work=k,generations=[l['generation'],r['generation']],
                             VBlanks=[l['VBlanks'],r['VBlanks']]))
    return dict(paired=len(pairs),unmatched=[len(x)-len(pairs),len(y)-len(pairs)],pairs=pairs,
                unique_workload_only=work)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('files',type=Path,nargs='+')
    a=p.parse_args()
    runs=[read_trace(f) for f in a.files]
    print(json.dumps(dict(runs=runs,comparison=compare(*runs) if len(runs)==2 else None),indent=2))
