"""Decode the MMC927 physical capture. Event times are relative to the same FPGA query."""
import argparse
from collections import defaultdict
import json
import struct
from pathlib import Path

ROW=struct.Struct('<6H4B24s6I')
CAP=118
BINS=16+CAP*ROW.size
DISPLAYED=BINS+12*(8+1)*4
PORTS=('VRAM-low','VRAM-high','CGRAM','OAM')
MS=512/84000


def decode(path):
    raw=path.read_bytes()
    if len(raw)!=DISPLAYED+4+48+56:
        raise ValueError('invalid MMC927 log size')
    magic,n,mode,count,early_drop,late_drop,size,cap=struct.unpack_from('<8H',raw)
    if (magic,n,size,cap)!=(0x9001,927,ROW.size,CAP) or mode>3 or count>CAP:
        raise ValueError('wrong capture or ABI')
    shown,available=struct.unpack_from('<HH',raw,DISPLAYED)
    bins=[]
    for i in range(12):
        values=struct.unpack_from('<8I',raw,BINS+32*i)
        front,=struct.unpack_from('<I',raw,BINS+384+i*4)
        prefetch,=struct.unpack_from('<I',raw,DISPLAYED+4+i*4)
        bins.append(dict(start_s=i*5,front_cycles=front,prefetch_cycles=prefetch,
                         foreground=values[:4],prefetch=values[4:]))
    rows=[]
    for i in range(count):
        tick,gen,bg,ia,ea,probe,obj,dirty,valid,bank,wire,*cost=ROW.unpack_from(raw,16+i*size)
        row=dict(tick=tick,generation=gen,BG=bg,OBJ=obj,map=dirty,bank=bank,
                 valid=valid,probe_ms=round(probe*MS,3))
        rows.append(row)
        if (bank>1 or not (3000<=tick<3500 if mode==1 else 5500<=tick<6000)
            or valid&3!=3 or ea>ia or ia>=65472):
            row['invalid']='window or ARM identity';continue
        row['input_to_E0_ms']=round((ia-ea)*MS,3)
        if valid&8:row.update(foreground_cycles=cost[:3],prefetch_cycles=cost[3:])
        if mode==3:continue
        flags=wire[4]
        if not valid&4 or wire[1]!=0x97 or int.from_bytes(wire[2:4],'little')!=gen or flags&0xe2!=0x62:
            row['invalid']='FPGA generation, collision or incomplete SEAL/reveal/ACK';continue
        tile,seal,first,last,show,ack,anchor,pre=struct.unpack_from('<8H',wire,8)
        prev,=struct.unpack_from('<H',wire,6)
        def stamp(v):return -round(((anchor-v)&65535)*MS,3)
        def port(v,code):return [stamp(v),PORTS[code&3]]
        first_post=port(first,wire[5]) if flags&8 else None
        last_post=port(last,wire[5]>>2) if flags&16 else first_post
        row.update(last_tile=stamp(tile) if flags&1 else None,seal=stamp(seal),
                   first_dma=port(pre,wire[5]>>4) if flags&4 else first_post,
                   first_post_seal=first_post,last_post_seal=last_post,
                   reveal=stamp(show),ACK=stamp(ack),previous_reveal=stamp(prev),
                   ARM_E0_bounds=[-round((ea+probe+2)*MS,3),-round(ea*MS,3)])
        row['last_dma']=last_post or (port(last,wire[5]>>2) if wire[5]&64 else row['first_dma'])
        ordered=[row['seal'],*(v[0] for v in (first_post,last_post) if v),row['reveal'],row['ACK']]
        if ordered!=sorted(ordered):row['invalid']='timestamp order or wrap'
    return dict(mode=mode,rows=rows,displayed55=shown,dropped=[early_drop,late_drop],
                DWT_available=available,bins=bins,late_pairs=late_pairs(rows),
                input_30_60=cycle_totals(bins[6:]) if available else None)


def cycle_totals(bins):
    totals={}
    for name,elapsed in (('foreground','front_cycles'),('prefetch','prefetch_cycles')):
        d1,restore,retire,blocks=map(sum,zip(*(b[name] for b in bins)))
        total=sum(b[elapsed] for b in bins)
        totals[name]=dict(blocks=blocks,D1=d1,CRC_restore=restore,D2_D0=retire,
                          total=total,other=total-d1-restore-retire)
    return totals


def late_pairs(rows):
    # Adjacent gaps in an NTSC run differ by about 16.64 ms per VBlank.
    # Match in the same bank and compare durations; FPGA anchors differ by generation.
    groups=defaultdict(list)
    for row in rows:
        if row.get('invalid') or row.get('last_tile') is None or row['tick']<5500:
            continue
        gap=row['reveal']-row['previous_reveal']
        if not 0 < gap < 390:
            continue
        groups[row['BG'],row['OBJ'],row['map'],row['bank']].append((row,gap))
    pairs=[]
    for workload,group in groups.items():
        for slow,gap in group:
            for fast,reference in group:
                tail=(slow['reveal']-slow['last_tile'])-(fast['reveal']-fast['last_tile'])
                if abs(gap-reference-16.64)<1.5 and tail>8:
                    pairs.append(dict(longer=slow['generation'],shorter=fast['generation'],
                                      BG_OBJ_map_bank=workload,extra_gap_ms=round(gap-reference,3),
                                      extra_tile_to_reveal_ms=round(tail,3)))
    return pairs


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('log',type=Path)
    print(json.dumps(decode(p.parse_args().log),indent=2))
