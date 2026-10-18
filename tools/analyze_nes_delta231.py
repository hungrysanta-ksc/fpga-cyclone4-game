# SPDX-License-Identifier: MIT
"""231 byte preservation + shared-wire sensitivity and SNES upload model.

Actual C output packets; input framing/ready polls and sparse SNES DMA are
explicit models. Neither FPGA source timing nor actual65816 is executed here.
"""
from pathlib import Path
import argparse,csv,json,struct
from analyze_nes_geometry230 import analyze,packets,summary
from nes_delta231 import sha,BASE


def merge(ranges,gap):
    out=[]
    for kind,at,n in ranges:
        if out and out[-1][0]==kind:
            k,a,size=out[-1];space=at-(a+size)
            if 0<=space<=(gap if kind in (2,5) else 0) and at+n-a<=(4096 if kind in (2,5) else 2048):
                out[-1]=(k,a,at+n-a);continue
        out.append((kind,at,n))
    return out


def input_records(b,raw):
    count,logical=struct.unpack_from('<HH',b);at=4;lengths=[28]
    for _ in range(count):
        n=b[at+2]
        size=3+n if n else 13 if b[at+3]==1 else 7
        lengths.append(size);at+=size
    assert at==len(b)
    lengths.extend(3+min(240,raw-i) for i in range(0,raw,240))
    blocks=0;used=0
    for n in lengths:
        assert n<=248
        if used+n>248:blocks+=1;used=0
        used+=n
    return sum(lengths),blocks+bool(used)


def main():
    p=argparse.ArgumentParser();p.add_argument('--host',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    baseline=BASE/'probes/nes-geometry230/host06'
    verified=analyze(a.host,BASE/'probes/nes-geometry230/capture02');rows=[]
    for c in csv.DictReader((a.host/'cost.csv').open()):
        c={k:int(v) for k,v in c.items()};f=c['frame']
        for ext in ('geometry','raw','metadata'):
            assert (a.host/f'frame{f}.{ext}').read_bytes()==(baseline/f'frame{f}.{ext}').read_bytes(),(f,ext)
        pp=list(packets((a.host/f'frame{f}.packets').read_bytes()))
        plan=[]
        for line in (a.host/f'frame{f}.plans').read_text().splitlines():
            k,slot,n=map(int,line.split(','));plan.append((k,slot*n,n))
        chunks=merge(plan,0);assert len(plan)==c['plans'] and sum(n for _,_,n in plan)==c['tile_bytes']
        metadata=[]
        for p in pp:
            if p[0] not in (2,4,5,8):continue
            k=p[1];at,n,expanded=struct.unpack_from('<HHH',p,10);size=n if p[0]==2 else expanded
            if k==2:metadata.append((2,at,size))
            if k==5 and 1121<=at<3169:
                # Raw CHR only, excluding the following mode/HDMA tables.
                size=min(size,3169-at);metadata.append((5,at-1121,size))
        ranges=chunks+metadata;naive=merge(ranges,0);joined=merge(ranges,96)
        def charge(q):return sum(n+96 for _,_,n in q)+1568
        payload,blocks=input_records((a.host/f'frame{f}.delta').read_bytes(),c['patches']*256)
        assert payload==c['source_delta_payload']
        core=payload+3*blocks+c['metadata_spi']
        # Readiness scenarios, not runtime upper bounds. Status can repeat
        # arbitrarily until its production deadline if the consumer is slow.
        batches=(c['plans']+6)//7  # conservative32B plans,240B batch ceiling
        plan_wire=32*c['plans']+3+8*batches
        fixed=16*blocks+32 + plan_wire +20*batches+20*len(chunks)+60+7+23*len(chunks)
        data=len(pp)-2
        ready4=core+fixed+80+40*len(chunks)+20*((data+3)//4)
        ready1=core+fixed+80+40*len(chunks)+20*data
        rows.append(dict(**c,source_blocks_model=blocks,source_spi_model=payload+3*blocks,
                         core_wire_model=core,ready4_wire_model=ready4,ready1_wire_model=ready1,
                         metadata_packets=len(pp),pattern_chunks_model=len(chunks),
                         naive_sparse_vblank_charge=charge(naive),merged_vblank_charge=charge(joined),
                         merged_vram_commands=len(joined),merged_vram_bytes=sum(n for _,_,n in joined)))
    warm=rows[2:];fields=['source_spi_model','metadata_spi','core_wire_model','ready4_wire_model','ready1_wire_model',
                        'metadata_packets','naive_sparse_vblank_charge','merged_vblank_charge','merged_vram_commands','merged_vram_bytes']
    result=dict(passed=True,scope=__doc__,frames=71,warm_frames=69,metadata_equals_227=True,geometry_equals_227=True,
                stats={k:summary([r[k] for r in warm]) for k in fields},
                over_5468_75={k:sum(r[k]>5468.75 for r in warm) for k in ('core_wire_model','ready4_wire_model','ready1_wire_model')},
                over_vblank4192={k:sum(r[k]>4192 for r in warm) for k in ('naive_sparse_vblank_charge','merged_vblank_charge')},
                frame_results=rows,source_control_reserve_bytes=28,source_block_model='whole records, max248B +3 CRC/command',
                vblank_model='changed raw only; merge same-section inactive-WRAM gaps<=96B and total<=4096, DMAsetup96, final1568; NOTimplemented65816',
                gaps_require_valid_destination_base=True,full_runtime_approved=False,physical=False,actual_snes_execution=False,
                host_result_sha256=sha(a.host/'result.json'),analyzer_sha256=sha(Path(__file__)),
                verified_raw_rgb_pixels=verified['raw_rgb_pixel_checks'])
    a.out.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps({k:result[k] for k in ('passed','stats','over_5468_75','over_vblank4192')},indent=2))


if __name__=='__main__':main()
