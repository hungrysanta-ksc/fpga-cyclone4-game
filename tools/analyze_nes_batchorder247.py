# SPDX-License-Identifier: MIT
"""Bounded existing plan-batch reorder and receive-time DMA append model.

No producer/SNES implementation or timing claim. Preserve allocation and bytes.
"""
from pathlib import Path
from collections import defaultdict
import argparse,csv,json,struct
from nes_delta231 import BASE,sha
from analyze_nes_geometry230 import packets


def pack(records):
    batches=[];batch=[];size=0
    for item in records:
        if len(batch)==15 or size+item['encoded_bytes']>240:
            batches.append(batch);batch=[];size=0
        batch.append(item);size+=item['encoded_bytes']
        if len(batch)==15:batches.append(batch);batch=[];size=0
    if batch:batches.append(batch)
    return batches


def join(ranges):
    out=[]
    for kind,at,n in ranges:
        if out and out[-1][0]==kind:
            _,start,size=out[-1];gap=at-start-size
            if 0<=gap<=96 and at+n-start<=4096:
                out[-1]=(kind,start,at+n-start);continue
        out.append((kind,at,n))
    return out


def insertion(batch):
    result=[];compares=moves=bytes_moved=0
    for r in batch:
        at=len(result)
        while at:
            compares+=1
            if result[at-1]['key']<=r['key']:break
            at-=1;moves+=1;bytes_moved+=result[at]['encoded_bytes']
        result.insert(at,r)
    return result,compares,moves,bytes_moved


def analyze(observer,prior,walk,relocation):
    pins={}
    def pin(p):pins[p.resolve().relative_to(BASE).as_posix()]=sha(p);return p
    old=json.loads(pin(prior).read_text(encoding='utf-8'))['rows']
    wr=json.loads(pin(walk).read_text(encoding='utf-8'))['rows']
    rel=list(csv.DictReader(pin(relocation).open(encoding='utf-8',newline='')))
    slots=defaultdict(list)
    for r in csv.DictReader(pin(observer/'slot247.csv').open()):
        r={k:int(v) for k,v in r.items()}
        if r['kind']==2 or not(r['equal'] and r['resident']):slots[r['frame']].append(r)
    assert len(old)==len(wr)==len(rel)==71
    rows=[];private=[]
    for o,w,rr in zip(old,wr,rel):
        f=o['frame'];assert f==w['frame']==int(rr['frame'])
        plans=[tuple(map(int,l.split(','))) for l in pin(observer/f'frame{f}.plans').read_text().splitlines()]
        records=[]
        assert len(plans)==len(slots[f])
        for p,s in zip(plans,slots[f]):
            kind=1 if s['kind']==1 else 0;assert p==(kind,s['slot'],32 if kind else 16)
            # Every observed write is ordinary; do not silently assume that for
            # new scenes. Nonidentity/alt plans require real variable lengths.
            assert s['retain']==1
            records.append(dict(kind=kind,slot=s['slot'],size=p[2],key=kind*1024+s['slot'],
                                encoded_bytes=3 if s['kind']==2 else 8 if kind else 7))
        records.append(dict(kind=3,slot=0,size=0,key=65535,encoded_bytes=3))
        batches=pack(records);ordered=[];compares=moves=moved_bytes=0
        for batch in batches:
            q,c,m,b=insertion(batch);ordered.extend(q);compares+=c;moves+=m;moved_bytes+=b
            assert sorted((r['kind'],r['slot'],r['size']) for r in q)==sorted((r['kind'],r['slot'],r['size']) for r in batch)
            assert sum(r['encoded_bytes'] for r in q)==sum(r['encoded_bytes'] for r in batch)
        assert ordered[-1]['kind']==3 and ordered[0]['key']==0
        ordered=ordered[:-1]
        tail=[]
        for p in packets(pin(observer/f'frame{f}.packets').read_bytes()):
            if p[0] in (1,3):continue
            at,n,expanded=struct.unpack_from('<HHH',p,10);size=n if p[0]==2 else expanded
            if p[1]==2:tail.append((2,at,size))
            elif p[1]==5 and 1121<=at<3169:tail.append((5,at-1121,min(size,3169-at)))
        original=[(k,s*n,n) for k,s,n in plans]+tail
        batch_ranges=[(r['kind'],r['slot']*r['size'],r['size']) for r in ordered]+tail
        sorted_ranges=sorted(original)
        global_list=join(sorted_ranges)
        assert sum(n+96 for _,_,n in global_list)+o['snes']['fixed_charge']==w['charge']
        assert len(global_list)==w['commands']
        row=dict(frame=f,plan_records=len(plans),batches=len(batches),
                 largest_batch=max(map(len,batches)),encoded_plan_bytes=sum(r['encoded_bytes'] for r in records),
                 insertion_comparisons=compares,insertion_moved_records=moves,insertion_moved_bytes=moved_bytes,
                 global_sorted_charge=w['charge'],global_sorted_commands=w['commands'])
        for name,ranges in [('arrival_gap',original),('batch_sorted_gap',batch_ranges)]:
            commands=join(ranges)
            # Every real write lies in a command of its section. Overlap caused
            # by a later out-of-order arrival is permitted only after SEAL;
            # no validity update is attributed to gap copying.
            for kind,at,n in original:assert any(k==kind and a<=at and at+n<=a+z for k,a,z in commands)
            row[name+'_commands']=len(commands)
            row[name+'_bytes']=sum(n for _,_,n in commands)
            row[name+'_charge']=sum(n+96 for _,_,n in commands)+o['snes']['fixed_charge']
        row['semantic16_ready4_wire_bytes']=int(rr['semantic_shift_batched16.ready4'])
        # Plan count/encoded lengths/batch membership unchanged. Pattern
        # aperture chunk count may change; report separately, not as zero cost.
        def chunks(seq):
            n=0;last=None
            for r in seq:
                if r['kind']==3:continue
                if last is None or last[0]!=r['kind'] or last[1]!=r['slot']*r['size']:n+=1
                last=(r['kind'],(r['slot']+1)*r['size'])
            return n
        row['original_pattern_runs']=chunks(records)
        row['batch_sorted_pattern_runs']=chunks(ordered)
        rows.append(row);private.append(dict(frame=f,batches=batches,ordered=ordered,
                                              arrival_commands=join(original),batch_commands=join(batch_ranges)))
    warm=rows[2:]
    def stats(k):v=[r[k] for r in warm];return dict(minimum=min(v),maximum=max(v),total=sum(v))
    # Caller already owns a32B encoded record before append. Insertion at append
    # can reuse it; at most14 prior records totaling<=237B are shifted per add.
    return dict(stage=247,passed=True,frames=71,scope=__doc__,
        warm={k:stats(k) for k in rows[0] if k!='frame'},
        charge_over_4192={name:[r['frame'] for r in warm if r[name]>4192] for name in ('arrival_gap_charge','batch_sorted_gap_charge','global_sorted_charge')},
        per_batch_bounds=dict(max_records=15,max_payload_bytes=240,max_pair_comparisons=105,
                              conservative_shift_write_bytes=14*240,extra_reads_same=True,
                              one_record_scratch_bytes=32,existing_append_scratch_bytes=32,
                              proposed_additional_persistent_bytes=0),
        ordering_guards=['Do not reorder across original batch boundaries.',
                         'END remains last and zero tile remains first; allocator output and arbitrary row/alt record bytes are immutable.',
                         'CRC must be calculated after reordering;sent count,token and physical bank ownership are unchanged.',
                         'Full196 nonordinary records must be parsed with their alt_mask lengths; observed71 alone does not test them.'],
        limitations=['Model only: no C sorter,FPGA converter or actual65816 new receive-time path was run.',
                     'No post-SEAL scan is required by append-only descriptors, but receive-time work and ARM sorting are not free or timed.',
                     'Gap allowance for patterns requires the existing SEAL used-subset-valid contract;never early DMA.',
                     'Actual aperture2048B/token boundaries can split a pattern run;run counts are not measured wire savings.',
                     'No new FPGA area,full ARM RUN/IRQ,STOP or complete display schedule approval.'],
        selected_implementation=None,product_changed=False,rows=rows,details=private,input_hashes=pins,
        analyzer_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('observer','prior','walk','relocation','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=analyze(*(getattr(a,k).resolve() for k in ('observer','prior','walk','relocation')))
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','details','input_hashes')};public.update(private_result_sha256=sha(raw),input_count=len(r['input_hashes']))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(r['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(r['rows'])
    print(json.dumps(public,indent=2))


if __name__=='__main__':main()
