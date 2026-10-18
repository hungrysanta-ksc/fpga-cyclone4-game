# SPDX-License-Identifier: MIT
"""Compare structural traversal work on the same received ranges; not CPU timing."""
from pathlib import Path
import argparse,csv,json,struct
from nes_delta231 import BASE,sha
from analyze_nes_geometry230 import packets

GROUPS=((0,1024,16),(1,128,32),(2,256,16),(5,128,16))


def workload(ranges):
    units=set();ordered=[];comparisons=moves=0
    for start,count in ranges:
        new=set(range(start,start+count));assert not units&new
        units|=new
        # Stable backward insertion into an unmerged range list. Keep the
        # original ranges: eager merge could change later insertion costs.
        at=len(ordered)
        while at:
            comparisons+=1
            if ordered[at-1][0]<start:break
            at-=1;moves+=1
        ordered.insert(at,(start,count))
    assert sorted(units)==[u for a,n in ordered for u in range(a,a+n)]
    words={}
    for unit in units:words[unit//16]=words.get(unit//16,0)|(1<<(unit%16))
    # Shift a loaded nonzero word until zero; only set bits do address/run work.
    replay=[];shifts=0
    for index,value in sorted(words.items()):
        bit=0
        while value:
            if value&1:replay.append(index*16+bit)
            value>>=1;bit+=1;shifts+=1
    assert replay==sorted(units)
    return dict(units=len(units),nonzero_bytes=len({u//8 for u in units}),
                nonzero_words=len(words),word_shift_steps=shifts,
                range_records=len(ranges),insertion_comparisons=comparisons,
                moved_descriptors=moves)


def analyze(prior,observer,scan):
    original=json.loads(prior.read_text(encoding='utf-8'))['rows'];pins={}
    def pin(p):pins[p.relative_to(BASE).as_posix()]=sha(p);return p
    for p in (prior,scan/'result.json',scan/'run/capture.lua'):pin(p)
    rows=[];details=[]
    for old in original:
        f=old['frame'];pfx=observer/f'frame{f}';ranges={k:[] for k,_,_ in GROUPS}
        for line in pin(pfx.with_suffix('.plans')).read_text().splitlines():
            kind,slot,n=map(int,line.split(','));assert n==(32 if kind else 16)
            ranges[kind].append((slot,1))
        for p in packets(pin(pfx.with_suffix('.packets')).read_bytes()):
            if p[0] in (1,3):continue
            kind=p[1];at,n,expanded=struct.unpack_from('<HHH',p,10);size=n if p[0]==2 else expanded
            if kind==2:
                assert at%16==size%16==0;ranges[2].append((at//16,size//16))
            elif kind==5 and 1121<=at<3169:
                end=min(at+size,3169);assert (at-1121)%16==(end-at)%16==0
                ranges[5].append(((at-1121)//16,(end-at)//16))
        groups={k:workload(ranges[k]) for k,_,_ in GROUPS}
        # Independent existing *actual* scanner descriptors establish the
        # exact union and permitted gaps, rather than treating estimates as IO.
        commands=list(csv.DictReader(pin(scan/f"run/commands-{old['generation']}.csv").open()))
        expected=[]
        for kind,limit,size in GROUPS:
            units=sorted(u for a,n in ranges[kind] for u in range(a,a+n));assert all(0<=u<limit for u in units)
            spans=[]
            for unit in units:
                at=unit*size
                if spans and at-spans[-1][1]<=96 and at+size-spans[-1][0]<=4096:spans[-1][1]=at+size
                else:spans.append([at,at+size])
            src,da,db={0:(0,0,0xc000),1:(0x4000,0x4000,0x8000),2:(0x5000,0x6000,0xa000),5:(0x6961,0x5000,0x9000)}[kind]
            expected.extend(dict(source=old['bank']*0x8000+src+a,destination=(db if old['bank'] else da)+a,bytes=b-a) for a,b in spans)
        assert [{k:int(v) for k,v in row.items()} for row in commands]==expected
        total={k:sum(g[k] for g in groups.values()) for k in next(iter(groups.values()))}
        rows.append(dict(frame=f,full_bit_visits=1536,word_loads=96,**total,
                         byte_expanded_bits=total['nonzero_bytes']*8,
                         word_expanded_bits=total['nonzero_words']*16,
                         moved_descriptor_bytes=total['moved_descriptors']*8,
                         final_commands=len(expected)))
        details.append(dict(frame=f,groups=groups,ranges=ranges))
    def stats(key):
        values=[r[key] for r in rows[2:]]
        return dict(minimum=min(values),maximum=max(values),sum=sum(values),mean=sum(values)/len(values))
    # Same section max counts. Range insertion moves are bounded but quadratic;
    # a per-section reverse order is a legal ordering absent an added protocol.
    bounds={str(k):n*(n-1)//2 for k,n,_ in GROUPS}
    return dict(stage=247,passed=True,scope='Structural work model, not65816 cycles or code-size proof',
        frames=len(rows),exact_existing_command_frames=len(rows),word_loads_per_frame=96,
        warm={k:stats(k) for k in rows[0] if k!='frame'},
        full_density=dict(units=1536,nonzero_words=96,word_shift_steps=1536),
        worst_unmerged_insertion=dict(per_section_descriptor_moves=bounds,total_descriptor_moves=sum(bounds.values()),
                                     descriptor_write_bytes=8*sum(bounds.values()),extra_read_bytes_same=True),
        decision='Prefer bounded word traversal for a code-size/runtime diagnostic; range insertion has no justified worst-case advantage.',
        code_size_limit=3936,old_body_after_removal_and_scan_call=3647,
        maximum_new_scanner_and_table_bytes=289,
        service_contract='At most16 shifts/set-bit handling per word,96 service opportunities; actual maximum gap and STOP still need execution.',
        limitations=['No ms estimate: full-bit53ms cannot be scaled by visit counts.',
                     'Insertion counts model unmerged lists within each section in original plan/packet order; not an implemented receiver.',
                     'At most1536 entries share existing12KiB list; command union equivalence does not prove cancellation or ownership.',
                     'Word traversal cold/full-density still needs1536 shifts; no unconditional60Hz assertion.',
                     'No production/FPGA/ARM/FIT/charge-policy change or P2 selection.'],
        product_changed=False,selected_implementation=None,rows=rows,details=details,input_hashes=pins,
        analyzer_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('prior','observer','scan','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=analyze(a.prior.resolve(),a.observer.resolve(),a.scan.resolve())
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','details','input_hashes')}
    public.update(input_count=len(r['input_hashes']),private_result_sha256=sha(raw))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(r['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(r['rows'])
    print(json.dumps(public,indent=2))


if __name__=='__main__':main()
