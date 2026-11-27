"""Compare contiguous, LOAD-anchored FF3 field flight samples from the paired probes."""
import argparse
import json
import math
import statistics
import struct
from pathlib import Path

HEADER=struct.Struct('<6I4H')
ROW=struct.Struct('<I6H12s2B2x')
TICK_MS=65536/84000
FIELD_MS=1000/60.0988

def decode(path):
    data=path.read_bytes()
    magic,edition,slot,rom,serial,crc,used,start,done,misses=HEADER.unpack_from(data)
    if magic!=0x32354d46 or edition not in (1052,1053) or not 1<=slot<=4 or rom!=0x4be84aa7:
        raise ValueError(f'{path}: expected a restored FF3 movement recording')
    if not 2<=used<=218 or done!=1 or len(data)<HEADER.size+ROW.size*used:
        raise ValueError(f'{path}: incomplete window (rows={used}, status={done})')
    rows=[]
    for i in range(used):
        ack,tick,gen,x,y,bg,obj,p,footer,ack_ok=ROW.unpack_from(data,HEADER.size+i*ROW.size)
        if i==0 and not footer:
            continue
        if footer!=0x5a or p[0]!=0xd2 or gen!=int.from_bytes(p[1:3],'little') or not ack_ok:
            raise ValueError(f'{path}: missing/torn event at index {i}')
        flags=p[3]
        if i and flags&31!=17:
            raise ValueError(f'{path}: expected held RIGHT, got flags {flags:#x} at {i}')
        tile=p[4]+((p[8]&15)<<8)
        seal=p[5]+((p[8]>>4)<<8)
        show=p[6]+((p[9]&15)<<8)
        final=p[7]+((p[9]>>4)<<8)
        move=p[10]+((p[11]&15)<<8)
        rows.append(dict(index=i,tick=tick,gen=gen,x=x,y=y,bg=bg,obj=obj,show=show,final=final,
                         arm_ack=ack,move=move,tile=tile if flags&32 else None,seal=seal))
    if len({r['move'] for r in rows if r['index']})!=1:
        raise ValueError('movement origin changed during the sample')
    moving=[r for r in rows if r['index']]
    if ((moving[-1]['tick']-start)&65535)<400:
        raise ValueError('missing end of four-second window')
    # Direction can change between a PPU write and the 16-byte SPI read.
    # Keep that preceding publication as an anchor rather than adding a clock wrap.
    if dt(moving[0]['show'],moving[0]['move'])>1500:
        if dt(moving[0]['move'],moving[0]['show'])>20:
            raise ValueError('ambiguous first movement timestamp')
        moving[0]['index']=0
    return (slot,rom,serial,crc),edition,misses,rows

def dt(end,start):return ((end-start)&4095)*TICK_MS

def summary(rows):
    moving=[r for r in rows if r['index']]
    gaps=[];fields=[]
    for a,b in zip(moving,moving[1:]):
        gap=dt(b['show'],a['show'])
        arm_ms=((b['arm_ack']-a['arm_ack'])&0xffffffff)/84000
        if abs(gap-arm_ms)>10 or gap<=0:
            raise ValueError(f"ambiguous publication gap at generation {b['gen']}")
        gaps.append(gap)
        n=round(gap/FIELD_MS)
        fields.append(n if n>=1 and abs(gap-n*FIELD_MS)<4 else None)
    if not gaps:raise ValueError('no consecutive displays')
    stage=lambda k,j:[dt(r[k],r[j]) for r in moving if r[j] is not None]
    def stats(v):
        return dict(mean=round(statistics.mean(v),3),p95=round(sorted(v)[math.ceil(.95*len(v))-1],3),
                    max=round(max(v),3)) if v else None
    return dict(displays=len(moving),fps=round(len(gaps)*1000/sum(gaps),3),gap_ms=stats(gaps),
                vblank_intervals={str(n):fields.count(n) for n in set(fields)},
                tile_to_seal_ms=stats(stage('seal','tile')),seal_to_show_ms=stats(stage('show','seal')),
                show_to_final_ack_ms=stats(stage('final','show')),
                first_move_to_show_ms=dt(moving[0]['show'],moving[0]['move']),
                first_xy=[moving[0]['x'],moving[0]['y']])

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('page',type=Path);p.add_argument('group',type=Path);p.add_argument('--rows',action='store_true')
    args=p.parse_args()
    a,b=map(decode,(args.page,args.group))
    if a[0]!=b[0] or (a[1],b[1])!=(1052,1053):raise ValueError('different slot, ROM, serial, CRC or policy order')
    report={}
    for run in (a,b):
        report[run[1]]=dict(summary(run[3]),failed_probes_including_wait=run[2])
        if args.rows:report[run[1]]['rows']=run[3]
    base,trial=report[1052],report[1053]
    report['delta_1053_minus_1052']=dict(
        fps=round(trial['fps']-base['fps'],3),
        p95_gap_ms=round(trial['gap_ms']['p95']-base['gap_ms']['p95'],3),
        max_gap_ms=round(trial['gap_ms']['max']-base['gap_ms']['max'],3))
    def by_position(rows):
        bins={}
        for prev,row in zip(rows,rows[1:]):
            if prev['index'] and row['index']:
                bins.setdefault((row['x'],row['y']),[]).append(dt(row['show'],prev['show']))
        return bins
    old,new=(by_position(run[3]) for run in (a,b))
    shared=old.keys() & new.keys()
    report['common_scroll_positions']=len(shared)
    if shared:
        report['equal_position_mean_gap_delta_ms']=round(statistics.mean(
            statistics.mean(new[key])-statistics.mean(old[key]) for key in shared),3)
    print(json.dumps(report,indent=2))

if __name__=='__main__':main()
