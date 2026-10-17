# SPDX-License-Identifier: MIT
"""Byte-exact replay costs and bounded host-only joint delta counterfactual.

This is not a production protocol or a throughput benchmark. The fixture uses
an observed-game stimulus adapter, modeled source reads and display ACKs.
"""
from pathlib import Path
import argparse, csv, hashlib, json, statistics, struct
from build_nes_game164 import RGB

SIZES=(4096,512,544,3418)
NAMES=('map','cgram','oam','raster_bundle')


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def spans(old,new,granule=1,header=3,limit=240):
    """Changed granules, coalescing short gaps only when wire cost cannot grow."""
    assert len(old)==len(new)
    changed=[(i,min(i+granule,len(new))) for i in range(0,len(new),granule)
             if old[i:i+granule]!=new[i:i+granule]]
    runs=[]
    for a,b in changed:
        if runs and a-runs[-1][1]<=header and b-runs[-1][0]<=limit:
            runs[-1]=(runs[-1][0],b)
        else:runs.append((a,b))
    return [(a,new[a:min(a+limit,b)]) for x,b in runs for a in range(x,b,limit)]


def apply(old,ops):
    out=bytearray(old);end=0
    for at,data in ops:
        assert end<=at and data and at+len(data)<=len(out)
        out[at:at+len(data)]=data;end=at+len(data)
    return bytes(out)


def sections(b):
    assert len(b)==sum(SIZES)
    out=[];at=0
    for n in SIZES:out.append(b[at:at+n]);at+=n
    return out


def packets(b):
    at=0
    while at<len(b):
        assert at+2<=len(b);n=struct.unpack_from('<H',b,at)[0];at+=2
        assert 16<=n<=256 and at+n<=len(b)
        p=b[at:at+n];at+=n
        assert len(p)==16+struct.unpack_from('<H',p,12)[0]
        yield p
    assert at==len(b)


def summary(values):
    return dict(mean=statistics.mean(values),minimum=min(values),maximum=max(values))


def analyze(host,capture):
    evidence=json.loads((host/'result.json').read_text());assert evidence['passed']
    assert sha(host/'cost.csv')==evidence['cost_sha256'],'cost hash'
    for name,digest in evidence['evidence_files'].items():
        assert sha(host/name)==digest,('evidence hash',name)
    costs=list(csv.DictReader((host/'cost.csv').open()))
    banks=[[bytes([0xa5])*n for n in SIZES] for _ in range(2)]
    source=bytes(5741);source_id=None;rows=[];raw_pixel_checks=0
    for ix,c in enumerate(costs):
        c={k:int(v) for k,v in c.items()};f=c['frame'];target=ix%2
        desired=sections((host/f'frame{f}.metadata').read_bytes())
        before=banks[target].copy();wire=[0]*4;control=0;commands=0
        bundle_parts=dict(scroll=0,padding=0,raw_chr=0,patch_tables=0)
        for p in packets((host/f'frame{f}.packets').read_bytes()):
            op,k=p[:2];at=struct.unpack_from('<H',p,10)[0];data=p[16:]
            expanded=struct.unpack_from('<H',p,14)[0]
            if op in (1,3):control+=len(p)+3;continue
            assert 2<=k<=5 and op in (2,4,5,8)
            wire[k-2]+=len(p)+3;commands+=1
            if k==5:
                name='scroll' if at==0 else 'padding' if at<1121 else 'raw_chr' if at<3169 else 'patch_tables'
                bundle_parts[name]+=len(p)+3
            if op in (4,5,8):
                assert expanded%len(data)==0;data=data*(expanded//len(data))
            else:assert expanded==0
            assert at+len(data)<=SIZES[k-2]
            out=bytearray(banks[target][k-2]);out[at:at+len(data)]=data;banks[target][k-2]=bytes(out)
        assert banks[target]==desired,(f,'actual C packet reconstruction')
        assert control+sum(wire)==c['metadata_spi']
        # Counterfactual source geometry, fixed offsets and exact bytes. Raw rows
        # are always resent because required-bitmap enumeration aliases raw RAM.
        geometry=(host/f'frame{f}.geometry').read_bytes();assert len(geometry)==5741
        raw=(host/f'frame{f}.raw').read_bytes();assert len(raw)==c['patches']*256
        ops=spans(source,geometry) if ix else [(a,geometry[a:a+240]) for a in range(0,len(geometry),240)]
        assert apply(source,ops)==geometry
        payload=16+sum(3+len(b) for _,b in ops)+len(raw)+3*((len(raw)+239)//240)
        source_wire=payload+3*((payload+247)//248)
        if ix and source_id!=(f-1):raise AssertionError('source base identity')
        # Inactive bank, not last displayed frame. Packet envelope19 is the
        # actual E1 header16+command/CRC3. New coverage/dirty protocol required.
        delta=[];changed=[]
        for j in range(4):
            d=spans(before[j],desired[j],granule=16,header=19)
            assert apply(before[j],d)==desired[j]
            delta.append(min(wire[j],sum(19+len(b) for _,b in d)))
            changed.append(sum(a!=b for a,b in zip(before[j],desired[j])))
        raw_chr_changed=sum(a!=b for a,b in zip(before[3][1121:3169],desired[3][1121:3169]))
        # Demonstrate that omitting a required span or using the active-bank
        # base is unsafe. These are model observations, not protocol fault tests.
        if ix==2:
            assert source_id!=f-2
            assert ops and apply(source,ops[:-1])!=geometry
            assert any(before[j]!=banks[1-target][j] for j in range(4))
        # Collector raw rows must equal the same fixture's canonical RGB color
        # indices. Compared by the separate raw-validation stage, not guessed
        # from frame-end nametable data.
        raw_rows=[]
        for y in range(224):
            r=struct.unpack_from('<Q',geometry,3872+y*8)[0]
            if (r>>49)&1:raw_rows.append(dict(y=y+8,slot=(r>>50)&7))
        assert [x['y'] for x in raw_rows]==[193,194]
        rgb=(capture/f'frame-{f:04d}.rgb').read_bytes();assert len(rgb)==256*240*3
        for row in raw_rows:
            start=row['slot']*256
            actual=b''.join(bytes.fromhex(RGB[c]) for c in raw[start:start+256])
            assert actual==rgb[row['y']*768:(row['y']+1)*768],(f,'raw RGB mismatch')
            raw_pixel_checks+=256
        rows.append(dict(**c,section_spi=dict(zip(NAMES,wire)),control_spi=control,commands=commands,
                         raster_bundle_parts=bundle_parts,source_delta_model_spi=source_wire,
                         output_delta_model_spi=control+sum(delta),output_delta_sections=dict(zip(NAMES,delta)),
                         output_changed_bytes=dict(zip(NAMES,changed)),raw_rows=raw_rows,
                         raw_chr_changed_bytes=raw_chr_changed,
                         joint_delta_model_spi=source_wire+control+sum(delta)))
        source=geometry;source_id=f
    warm=rows[2:];assert len(warm)==69
    fields=['ingress_payload','metadata_spi','tile_bytes','plans','map_vram_bytes',
            'source_delta_model_spi','output_delta_model_spi','joint_delta_model_spi','raw_chr_changed_bytes']
    stats={k:summary([r[k] for r in warm]) for k in fields}
    by_section={k:summary([r['section_spi'][k] for r in warm]) for k in NAMES}
    parts={k:summary([r['raster_bundle_parts'][k] for r in warm]) for k in rows[0]['raster_bundle_parts']}
    return dict(passed=True,scope=__doc__,first=rows[0]['frame'],last=rows[-1]['frame'],frames=len(rows),warm_frames=len(warm),
                production_geometry_and_metadata_bytes_preserved=True,raw_rgb_pixel_checks=raw_pixel_checks,
                stats=stats,section_spi=by_section,raster_bundle_spi=parts,frames_detail=rows,
                spi_hz=2625000,spi_bytes_per_60hz=5468.75,
                joint_model_over_60hz_byte_budget=sum(r['joint_delta_model_spi']>5468.75 for r in warm),
                excluded=['D0-D3 status','E0 and E8 status/ACK polling','E8/E9 plans','CPU and SPI gaps','qualified PSRAM source reads','parallel tile aperture','SNES CPU/VRAM/VBlank'],
                source_model_control_bytes=16,source_model_header_bytes=3,output_model_header_bytes=19,
                physical=False,production_protocol_changed=False,full_core_equivalence=False,actual_snes_execution=False,
                host_result_sha256=sha(host/'result.json'),cost_sha256=sha(host/'cost.csv'),script_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser();p.add_argument('--host',type=Path,required=True);p.add_argument('--capture',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();r=analyze(a.host,a.capture)
    a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:r[k] for k in ('passed','frames','warm_frames','stats','section_spi','raster_bundle_spi','joint_model_over_60hz_byte_budget')},indent=2))


if __name__=='__main__':main()
