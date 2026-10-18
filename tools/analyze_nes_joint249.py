# SPDX-License-Identifier: MIT
"""Joint source replacement and unified range/coverage ownership review.

Actual encoder execution/MAP is separate from Python receipt/schedule models.
The remaining allowance belongs to ALL unmeasured work, not ARM alone.
"""
from pathlib import Path
import argparse,csv,json,struct,shutil,copy
from nes_delta231 import ROOT,BASE,sha
from nes_block249 import encode,decode,RANGES
from analyze_nes_relocation247 import project
from analyze_nes_path236 import variant
from analyze_nes_source234 import blocks
from analyze_nes_schedule248 import simulate,replace_map_packets
from analyze_nes_spantrade247 import spans,encode as map_encode
from analyze_nes_mapjoint247 import bitmap
from analyze_nes_validation247 import manifest_wire

MASTER=21477.270


def mark(memory,bank,start,count):
    if bank not in (0,1) or start<0 or count<=0 or start+count>1328:raise ValueError('range')
    # This model validates complete range before committing its bytes.
    for bit in range(start,start+count):
        at,mask=divmod(bit,8)
        if memory[332+at]&(1<<mask):raise ValueError('duplicate')
    for bit in range(start,start+count):
        at,bit=divmod(bit,8);memory[332+at]|=1<<bit;memory[bank*166+at]|=1<<bit


def coverage(memory,bank,seal):
    if len(seal)!=206:raise ValueError('seal length')
    raw=int.from_bytes(seal[38:40],'little')
    if raw>=8:raise ValueError('raw count')
    if not raw:
        for b in (0,1):memory[b*166+148:b*166+166]=bytes(18)
    for i,used in enumerate(seal[40:184]):
        if used&~memory[bank*166+i]:raise ValueError('pattern coverage')
    size=22 if raw else 4
    if memory[332+144:332+144+size]!=seal[184:184+size]:raise ValueError('metadata receipt')
    if memory[bank*166+144:bank*166+144+size]!=bytes([255])*size:raise ValueError('metadata valid')


def map_receipt(memory,ranges):
    end=0
    for at,n in ranges:
        if at<end or at%2 or n%2 or not 0<n<=64 or at+n>4096:raise ValueError('map range')
        for w in range(at//2,(at+n)//2):
            pos=498+w//8;bit=1<<(w%8)
            if memory[pos]&bit:raise ValueError('map duplicate')
            memory[pos]|=bit
        end=at+n


def guards():
    checks=0
    for start,count in [(-1,1),(0,0),(1328,1),(1327,2)]:
        try:mark(bytearray(1024),0,start,count)
        except ValueError:checks+=1
        else:raise AssertionError('range accepted')
    ram=bytearray(1024);mark(ram,0,7,18)
    for start,count in [(7,1),(8,16),(24,1)]:
        before=ram[:]
        try:mark(ram,0,start,count)
        except ValueError:checks+=1
        else:raise AssertionError('duplicate accepted')
        assert ram==before
    for rr in [[(1,2)],[(4094,4)],[(0,0)],[(0,66)],[(0,4),(2,2)],[(4,2),(0,2)]]:
        try:map_receipt(bytearray(1024),rr)
        except ValueError:checks+=1
        else:raise AssertionError('bad map accepted')
    return checks


def codec_guards():
    a=bytes(4398);b=bytes((i*13+9)&255 for i in range(4398));rr=encode(a,b,b'',1,1);checks=0
    cases=[rr[:-1],rr+rr[-1:],rr[:2]+rr[1:],rr[:1]+rr[2:]]
    for pos in (0,1,len(rr)-2,len(rr)-1):
        bad=list(rr);q=bytearray(bad[pos]);q[-1]^=1;bad[pos]=bytes(q);cases.append(bad)
    for bad in cases:
        try:decode(bad,a,1,1)
        except (ValueError,IndexError):checks+=1
        else:raise AssertionError('bad codec stream accepted')
    # Both shift directions, sparse literal and partial final mask byte.
    c=bytearray(b);c[:66]=b'\x19\x2a'+b[:64];c[2046:2112]=b[2048:2112]+b'\x13\x24';c[-1]^=1
    encoded=encode(b,c,b'',2,2);assert decode(encoded,b,2,2)==(c,b'')
    assert any(x[:2]==b'\x80\xff' for x in encoded) and any(x[:2]==b'\x9f\x01' for x in encoded)
    return checks


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={};p247=BASE/'probes/nes-wholepath247';p249=BASE/'probes/nes-joint249'
    def pin(f,expected=None):
        h=sha(f)
        if expected is not None:assert h==expected,f
        pins[f.relative_to(BASE).as_posix()]=h;return f
    def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
    old=read(p247/'placement05/result.json');actual=read(p247/'jointdecode-analysis03/result.json');validation=read(p247/'validation-analysis02/result.json')
    previous=read(BASE/'probes/nes-schedule248/analysis04/result.json')
    for name in ('test01','map01','blocktest03','blockmap01'):
        q=read(p249/name/'result.json');assert q['passed']
    fixedtest=read(p249/'blocktest03/result.json');fixedmap=read(p249/'blockmap01/result.json');assert fixedtest['encoder_sha256']==fixedmap['encoder_sha256']
    prepared={}
    for codec,path in [('shift','test01'),('block','blocktest03')]:
        prepared[codec]={int(r['frame']):int(r['prepare']) for r in csv.DictReader(pin(p249/path/'cycles.csv').open())}
    place={r['frame']:r for r in old['rows'] if r['placement']=='FPGA_typed_ext16'}
    jp={(int(r['frame']),r['mode']):r for r in csv.DictReader(pin(p247/'validation-analysis02/joint-frames.csv').open())}
    packets={g:[] for g in range(1,72)}
    for path in sorted((p247/'jointdecode-test02/run').glob('req-*.bin')):
        b=pin(path,actual['input_hashes'][path.relative_to(BASE).as_posix()]).read_bytes();packets[int.from_bytes(b[8:10],'little')].append(b)
    ranges={g:[] for g in range(1,72)}
    path=p247/'validation-test02/run/range247.csv'
    for r in csv.DictReader(pin(path,validation['input_hashes'][path.relative_to(BASE).as_posix()]).open()):ranges[int(r['generation'])].append({k:int(v) for k,v in r.items()})
    ram=bytearray(1024);valid=[set(),set()];prior_geometry=bytes(4398);prior_map=bytes(4096);stale=[set(range(2048)),set(range(2048))]
    rows=[];wire_rows=[];checks=0;negatives=guards();observed=read(p247/'observer03/result.json')
    for g in range(1,72):
        frame=g+904;bank=(g-1)%2;pp=packets[g];seal=next(b for b in pp if b[0]==3)
        ram[332:754]=bytes(422);received=set()
        for r in ranges[g]:
            assert r['bank']==166*bank;first=r['start'];count=r['take']
            mark(ram,bank,first,count);valid[bank].update(range(first,first+count));received.update(range(first,first+count))
            for b in (0,1):
                expected=sum(1<<bit for bit in valid[b]).to_bytes(166,'little');assert ram[166*b:166*(b+1)]==expected
            assert ram[332:498]==sum(1<<bit for bit in received).to_bytes(166,'little');checks+=498
        if int.from_bytes(seal[38:40],'little')==0:
            for v in valid:v.difference_update(range(1184,1328))
        coverage(ram,bank,seal)
        # Per-lane missing coverage and exact receipt mismatch are independent
        # negatives on the byte-RAM policy, not executed FPGA fault tests.
        used=int.from_bytes(seal[40:184],'little')
        if used:
            bit=(used&-used).bit_length()-1;bad=ram[:];bad[bank*166+bit//8]&=~(1<<(bit%8))
            try:coverage(bad,bank,seal)
            except ValueError:negatives+=1
            else:raise AssertionError('missing pattern accepted')
        bad=ram[:];bad[332+144]^=1
        try:coverage(bad,bank,seal)
        except ValueError:negatives+=1
        else:raise AssertionError('receipt mismatch accepted')
        path=p247/f'observer03/frame{frame}.geometry';geometry=pin(path,observed['output_hashes'][path.name]).read_bytes()
        path=p247/f'observer03/frame{frame}.raw';raw=pin(path,observed['output_hashes'][path.name]).read_bytes()
        new=geometry[:3872]+project(geometry)+geometry[5664:]
        path=p247/f'jointdecode-test02/run/expected-{g}.bin';current=pin(path,actual['input_hashes'][path.relative_to(BASE).as_posix()]).read_bytes()[:4096]
        changed={w for w in range(2048) if current[2*w:2*w+2]!=prior_map[2*w:2*w+2]}
        for st in stale:st.update(changed)
        words=set(stale[bank])
        for codec in ('shift','block','literal'):
            rec=encode(prior_geometry,new,raw,g,g) if codec=='block' else variant(prior_geometry,new,raw,g,g,codec)
            if codec=='block':assert decode(rec,prior_geometry,g,g)==(new,raw)
            source=sum(map(len,rec))+19*blocks(list(map(len,rec)))+32
            wire_rows.append(dict(frame=frame,codec=codec,source_spi_bytes=source,records=len(rec),payload_bytes=sum(map(len,rec))))
            for gap in (0,16):
                fmt='exact64' if not gap else 'gap16_64';rr=spans(words,gap,64)
                bm=bitmap({w for at,n in rr for w in range(at//2,(at+n)//2)})
                ram[498:754]=bytes(256);map_receipt(ram,rr);assert ram[498:754]==bm
                mf=manifest_wire(bm);compressed=sum(len(b)+19 for at,b in mf)<294
                if not compressed:mf=[(0,bm[:240]),(240,bm[240:])]
                replacement=replace_map_packets(pp,map_encode(rr,current,True),mf,compressed)
                placement=dict(place[frame]);placement['ready4_bytes']=int(jp[frame,'packed_'+fmt]['ready4'])+99*placement['chunks']+32+source-placement['source_spi_bytes']
                placement.update(source_spi_bytes=source,runs=len(rr),staging_payload_normalization_ms=sum(n for at,n in rr)*8/MASTER,seal_coverage_tail_ms=0)
                if frame<907:continue
                nonmap=sum(b[0] in (2,4,5,7,8) for b in pp)
                for setup in (500,1000,1500):
                    for service in (0,500,1000):
                        marks=[service/MASTER]*nonmap
                        row,_=simulate(frame,replacement,marks,placement,setup,False)
                        # Charge preparation serially even though eventual
                        # capture/transport may overlap; query is not bound.
                        prep=prepared[codec][frame]/22000 if codec in prepared else 0
                        # Explicit FPGA cycle ALLOCATION, not measured RTL:
                        # eight cycles/input byte plus byte-RAM read/modify/
                        # write work; final166B+map256B scans and422B clear.
                        parse=sum(len(b) for b in replacement if b[0] not in (1,7))
                        ramcycles=422+6*sum((r['start']%8+r['take']+7)//8 for r in ranges[g])+3*166+3*256
                        fpga=(8*parse+ramcycles)/22000
                        final_fixed=2000/MASTER
                        total=row['total_ms']+prep+fpga+final_fixed
                        rows.append(dict(frame=frame,codec=codec,map_format=fmt,map_setup_clocks=setup,
                            nonmap_service_clocks=service,source_prepare_ms=prep,fpga_allocated_ms=fpga,
                            final_fixed_allocated_ms=final_fixed,total_ms=total,residual_ms=1000/60-total,
                            spi_bytes=row['spi_bytes'],source_spi_bytes=source,collector_query_bound=False,
                            new_receiver_timed=False,source_prepare_measured=codec in prepared))
        stale[bank].clear();prior_map=current;prior_geometry=new
    summaries={}
    for codec in ('shift','block','literal'):
        for fmt in ('exact64','gap16_64'):
            for setup in (500,1000,1500):
                for service in (0,500,1000):
                    rr=[r for r in rows if (r['codec'],r['map_format'],r['map_setup_clocks'],r['nonmap_service_clocks'])==(codec,fmt,setup,service)]
                    summaries[f'{codec}_{fmt}_{setup}_{service}']=dict(max_ms=max(r['total_ms'] for r in rr),
                        min_residual_ms=min(r['residual_ms'] for r in rr),over=[r['frame'] for r in rr if r['residual_ms']<0],
                        frame954=next(r for r in rr if r['frame']==954))
    for name in ('nes_block249.py','nes_block249_rtl.py','probe_nes_source249.py','analyze_nes_schedule248.py',
                 'analyze_nes_spantrade247.py','analyze_nes_relocation247.py','analyze_nes_path236.py','analyze_nes_source234.py',
                 'nes_stream234.py','nes_delta231.py','nes_maskboundary247.py','nes_maskfast247.py','nes_sparse232.py','nes_dirty212.py'):
        pin(ROOT/'tools'/name)
    result=dict(passed=True,scope=__doc__,stage=249,frames=71,scheduled_warm_frames=69,schedules=len(rows),
        range_bitmap_byte_checks=checks,receipt_policy_negatives=negatives,codec_python_negatives=codec_guards(),
        byte_ram_layout=dict(valid0=[0,165],valid1=[166,331],received=[332,497],map_receipt=[498,753],used_bytes=754,capacity=1024),
        map_receipt_rtl=False,frame_certificate=False,unified_validator_rtl=False,source_query_bound=False,
        whole_fit=False,physical=False,source_test=fixedtest,source_map=fixedmap,
        summaries=summaries,rows=rows,wire_rows=wire_rows,input_hashes=pins,script_sha256=sha(Path(__file__)),
        limitations=['Only source encoder is executed/mapped; projected input and output consumers are fixtures.',
         'All mark/coverage removal REQUIRES moving exact receipt and validity plus bounding retained SNES command work.',
         '754B fit is a same-clock byte-RAM policy,not inferred unified validator or CDC proof.',
         'FPGA8cycles/byte,remaining SNES service and2000cycle final work are allocations,not actual runtimes.',
         'Source prepare is charged serially;actual collector queries,projection,ARM,extra polls,ordinary DMA/dispatch and VBlank wait still share the residual.',
         'Remaining SNES validate181 layout/HDMA semantics are NOT proven covered by the2000cycle fixed allowance;they remain in the residual.',
         'Standalone MAP cannot be subtracted from full-board FIT;current source reduction does not establish490LE/40LAB plus new logic/mapper margin.'])
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n')
    public={k:v for k,v in result.items() if k not in ('rows','wire_rows','input_hashes')}
    public['source_test']={k:v for k,v in fixedtest.items() if k!='input_hashes'}
    public.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'))
    (d/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
    for filename,items in [('frames.csv',rows),('wire.csv',wire_rows)]:
        with (d/filename).open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(items[0]),lineterminator='\n');w.writeheader();w.writerows(items)
    shutil.copyfile(__file__,d/'analyzer.py')
    for name,s in summaries.items():
        if name.endswith('_500_500') or name.startswith('block_') and name.endswith('_1000_500'):print(name,round(s['max_ms'],6),round(s['min_residual_ms'],6),len(s['over']))


if __name__=='__main__':main()
