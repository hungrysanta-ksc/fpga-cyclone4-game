# SPDX-License-Identifier: MIT
"""Joint map representation, receipt coverage and wire/DMA feasibility models.

Independent Python decoding of private observed maps; no C/65816/RTL change.
New decoder timing and code size remain unknown, not borrowed from old loops.
"""
from pathlib import Path
import argparse,csv,json,struct
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_geometry230 import packets
from analyze_nes_batchorder247 import join
from analyze_nes_gap247 import minimum_charge

MODES={'pairs':1,'mask8':2,'mask32':3}


def bitmap(words):
    b=bytearray(256)
    for w in words:b[w//8]|=1<<(w%8)
    return bytes(b)


def encode(mode,words,data):
    records=[]
    if mode=='pairs':
        records=[struct.pack('<H',w*2)+data[w*2:w*2+2] for w in sorted(words)]
    else:
        width=8 if mode=='mask8' else 32
        for group in sorted({w//width for w in words}):
            mask=sum(1<<(w%width) for w in words if w//width==group)
            header=bytes([group])+mask.to_bytes(width//8,'little')
            records.append(header+b''.join(data[w*2:w*2+2] for w in range(group*width,(group+1)*width) if w in words))
    result=[];p=bytearray([MODES[mode]])
    for record in records:
        assert len(record)<=69
        if len(p)+len(record)>240:result.append(bytes(p));p=bytearray([MODES[mode]])
        p+=record
    if len(p)>1:result.append(bytes(p))
    return result,records


def decode(mode,wire,base,valid,manifest):
    """One hypothetical frame after outer sequence/epoch/transport validation.

    Writes are private candidate bytes. Failure yields no publishable result;
    actual implementation must terminally STOP/reset rather than roll back.
    """
    out=bytearray(base);received=set();last_group=-1;last_word=-1
    for p in wire:
        if not 1<len(p)<=240 or p[0]!=MODES[mode]:raise ValueError('packet/version')
        at=1
        while at<len(p):
            if mode=='pairs':
                if at+4>len(p):raise ValueError('truncated pair')
                offset=struct.unpack_from('<H',p,at)[0];at+=2
                if offset&1 or offset>=4096:raise ValueError('word offset')
                indices=[offset//2]
            else:
                width=8 if mode=='mask8' else 32;header=1+width//8
                if at+header>len(p):raise ValueError('truncated mask')
                group=p[at];mask=int.from_bytes(p[at+1:at+header],'little');at+=header
                if group>=2048//width or group<=last_group or not mask:raise ValueError('mask order/range/zero')
                last_group=group;indices=[group*width+i for i in range(width) if mask>>i&1]
            if at+2*len(indices)>len(p):raise ValueError('truncated values')
            for w in indices:
                if w<=last_word or w in received:raise ValueError('duplicate/descending')
                out[2*w:2*w+2]=p[at:at+2];at+=2;received.add(w);last_word=w
    # Two bounded manifest packets, offset in existing outer address field.
    # Compare to already-received bits as they arrive; no256B expected copy.
    cursor=0;actual=bitmap(received)
    for offset,payload in manifest:
        if offset!=cursor or not 0<len(payload)<=240 or cursor+len(payload)>256:raise ValueError('manifest order/bounds')
        if payload!=actual[cursor:cursor+len(payload)]:raise ValueError('missing/unexpected word')
        cursor+=len(payload)
    if cursor!=256:raise ValueError('incomplete manifest')
    newvalid=valid|received
    if len(newvalid)!=2048:raise ValueError('cold/target coverage')
    return bytes(out),newvalid,received


def guards():
    count=0;data=bytes((i*37+9)&255 for i in range(4096));base=bytes(4096);full=set(range(2048))
    for mode in MODES:
        selected={0,2,7,8,31,32,2047};wire,recs=encode(mode,selected,data)
        manifest=[(0,bitmap(selected)[:240]),(240,bitmap(selected)[240:])]
        wanted=bytearray(base)
        for w in selected:wanted[2*w:2*w+2]=data[2*w:2*w+2]
        assert decode(mode,wire,base,full,manifest)[0]==wanted
        def reject(wire,valid=full,manifest=manifest):
            nonlocal count
            try:decode(mode,wire,base,valid,manifest)
            except ValueError:count+=1
            else:raise AssertionError((mode,'accepted malformed frame'))
        reject(wire[:-1]);reject(wire+[wire[-1]])
        reject([wire[0][:-1]]+wire[1:]);reject([bytes([255])+wire[0][1:]]+wire[1:])
        reject(wire,manifest=manifest[:1]);reject(wire,manifest=[manifest[1],manifest[0]])
        reject(wire,manifest=[(0,bytes(240)),manifest[1]])
        reject(wire,valid=set());reject(wire,valid=full-{1})
        # Reverse record order in separate packets so duplicate/order checks
        # cannot be satisfied merely by one packet's internal positions.
        reject([bytes([MODES[mode]])+x for x in reversed(recs)])
        if mode=='pairs':reject([bytes([1])+struct.pack('<HH',4096,0)])
        else:
            header=2 if mode=='mask8' else 5
            reject([bytes([MODES[mode]])+bytes(header)])
    # A sparse word cannot initialize its entire old16B validity granule.
    selected=set(range(0,2048,8));wire,_=encode('mask8',selected,data);m=bitmap(selected)
    assert {w//8 for w in selected}==set(range(256))
    try:decode('mask8',wire,base,set(),[(0,m[:240]),(240,m[240:])])
    except ValueError:count+=1
    else:raise AssertionError('coarse validity hid1792 uninitialized words')
    return count


def literal_packets(data,indices,unit):
    """Existing packet2/4 wire costs for sorted contiguous units, max240B."""
    ranges=[]
    for i in sorted(indices):
        at=i*unit
        if ranges and ranges[-1][0]+ranges[-1][1]==at:ranges[-1]=(ranges[-1][0],ranges[-1][1]+unit)
        else:ranges.append((at,unit))
    lengths=[];writes=[]
    for at,n in ranges:
        for start in range(at,at+n,240):
            size=min(240,at+n-start);payload=data[start:start+size]
            repeated=size>=4 and all(payload[i]==payload[i%2] for i in range(size))
            lengths.append(2 if repeated else size);writes.append((2,start,size))
    return lengths,writes


def analyze(a):
    pins={}
    def pin(p,expected=None):
        digest=sha(p)
        if expected is not None:assert digest==expected,p
        pins[p.resolve().relative_to(BASE).as_posix()]=digest;return p
    def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
    prior=read(a.prior);coalesce=read(a.coalesce);order=read(a.order)
    observed=read(a.observer/'result.json');assert observed['passed'] and prior['passed'] and coalesce['passed'] and order['passed']
    rel=list(csv.DictReader(pin(a.relocation).open(encoding='utf-8')))
    for name in ('src/nes/firmware/nes_plan_service200.c','tools/nes_sparse232.py','tools/nes_dirty212.py'):
        pin(ROOT/name)
    previous=bytes(4096);banks=[None,None];stale=[set(range(2048)),set(range(2048))]
    decoded={name:[bytes(4096),bytes(4096)] for name in MODES};valid={name:[set(),set()] for name in MODES}
    initialized={name:[False,False] for name in MODES};full_words=set(range(2048))
    rows=[];exact_bytes=0;mode_names=['current16','batched16','row64']+list(MODES)
    for p,c,o,detail,rr in zip(prior['rows'],coalesce['rows'],order['rows'],order['details'],rel):
        f=p['frame'];assert f==c['frame']==o['frame']==detail['frame']==int(rr['frame'])
        target=p['bank'];current=pin(a.observer/f'frame{f}.metadata',observed['output_hashes'][f'frame{f}.metadata']).read_bytes()[:4096]
        pp=list(packets(pin(a.observer/f'frame{f}.packets',observed['output_hashes'][f'frame{f}.packets']).read_bytes()))
        map_packets=[b for b in pp if b[1]==2 and b[0] not in (1,3)]
        changes={w for w in range(2048) if previous[2*w:2*w+2]!=current[2*w:2*w+2]}
        assert len(changes)==p['changes']['map_changed_words']
        for bank in stale:bank.update(changes)
        words=set(stale[target]);granules={w//8 for w in words};coarse_rows={w//32 for w in words}
        sent=set();original_map_ranges=[]
        for b in map_packets:
            at,n,expanded=struct.unpack_from('<HHH',b,10);size=n if b[0]==2 else expanded
            sent.update(range(at//16,(at+size)//16));original_map_ranges.append((2,at,size))
        assert sent==granules
        true_words=set(range(2048)) if banks[target] is None else {w for w in range(2048) if banks[target][2*w:2*w+2]!=current[2*w:2*w+2]}
        assert true_words<=words
        map_wire=sum(len(b)+3 for b in map_packets);data_count=len(pp)-2
        w=p['spi']['ready4_components']
        assert w['plans']+w['plan_control']==32*o['plan_records']+3+28*((o['plan_records']+6)//7)
        new_plan_wire=o['encoded_plan_bytes']+28*o['batches']
        old_chunks=w['pattern_control']//43;new_chunks=c['pattern_chunks']
        assert w['pattern_control']==old_chunks*43
        # Hold the same ready scenarios; replace conservative plan lengths and
        # arrival chunks by observed actual encoded lengths/batch-sort chunks.
        plan_delta=new_plan_wire-w['plans']-w['plan_control']
        chunk_delta=83*(new_chunks-old_chunks)
        source_delta=int(rr['semantic_shift_batched16.ready4'])-p['p1_models']['batched16']['ready4_bytes']
        assert source_delta==int(rr['semantic_shift_batched16.ready1'])-p['p1_models']['batched16']['ready1_bytes']
        base4=p['spi']['ready4_bytes']+source_delta+plan_delta+chunk_delta
        base1=p['spi']['ready1_bytes']+source_delta+plan_delta+chunk_delta
        pattern_charge=sum(n+96 for k,at,n in detail['batch_commands'] if k<2)
        pattern_min=minimum_charge([(r['kind'],r['slot'],r['size']) for r in detail['ordered']])
        raw_charge=sum(n+96 for k,at,n in detail['batch_commands'] if k==5)
        models={}
        for name in mode_names:
            manifest_extra=0;manifest_packets=0;writes=[];records=0;values=0;mask_bytes=0
            if name=='current16':
                lengths=[len(b)-16 for b in map_packets];writes=original_map_ranges;count=len(lengths);wirecost=map_wire
                values=8*len(granules);records=len(granules)
            elif name=='batched16':
                records=len(granules);values=8*records
                lengths=[18*min(13,records-i) for i in range(0,records,13)]
                wirecost=sum(lengths)+19*len(lengths);count=len(lengths);writes=[(2,g*16,16) for g in sorted(granules)]
                assert wirecost==p['p1_models']['batched16']['map_wire_bytes']
            elif name=='row64':
                expanded={g for row in coarse_rows for g in range(row*4,row*4+4)}
                lengths,writes=literal_packets(current,expanded,16);count=len(lengths);wirecost=sum(lengths)+19*count
                values=8*len(expanded);records=len(coarse_rows)
                rebuilt=bytearray(banks[target] or bytes(4096))
                for _,at,n in writes:rebuilt[at:at+n]=current[at:at+n]
                assert rebuilt==current
            else:
                wire,recs=encode(name,words,current);manifest=bitmap(words)
                # Inductive committed-state invariant: map coverage requires
                # ALL4096B, so each bank is either uninitialized or fully valid.
                # A warm full-valid flag does NOT replace received==manifest.
                assert valid[name][target]==(full_words if initialized[name][target] else set())
                output,newvalid,received=decode(name,wire,decoded[name][target],valid[name][target],[(0,manifest[:240]),(240,manifest[240:])])
                assert output==current and received==words
                assert initialized[name][target] or manifest==bytes([255])*256
                assert newvalid==full_words
                # Model boundary is successful final displayACK; failure/STOP
                # must prevent publication and discard both initialization flags.
                initialized[name][target]=True
                decoded[name][target]=output;valid[name][target]=newvalid;exact_bytes+=4096
                lengths=list(map(len,wire));records=len(recs);values=len(words)
                mask_bytes=records*(1 if name=='mask8' else 4 if name=='mask32' else 0)
                # SEAL222 ->190 removes the old32B map receipt mask; a256B
                # word manifest requires TWO additional bounded packets.
                manifest_extra=256+2*19-32;manifest_packets=2
                wirecost=sum(lengths)+19*len(lengths)+manifest_extra;count=len(lengths)
                writes=[(2,word*2,2) for word in sorted(words)]
            next_count=data_count-len(map_packets)+count+manifest_packets
            ready4=base4-map_wire+wirecost+20*((next_count+3)//4-(data_count+3)//4)
            ready1=base1-map_wire+wirecost+20*(next_count-data_count)
            # Preserve the already-measured batch pattern command order, not
            # global resorting: only replace its sorted map section.
            commands=[x for x in detail['batch_commands'] if x[0]<2]+join(writes)+[x for x in detail['batch_commands'] if x[0]==5]
            charge=sum(n+96 for _,_,n in commands)+p['snes']['fixed_charge']
            if name=='current16':assert charge==c['charge']
            nonmap_ms=(c['mark_master_clocks']-c['map_mark_clocks'])/21477.270
            models[name]=dict(map_data_wire_bytes=wirecost-manifest_extra,map_manifest_extra_wire=manifest_extra,
                map_packets=count,manifest_packets=manifest_packets,records=records,value_words=values,bitmap_mask_bytes=mask_bytes,
                ready4=ready4,ready1=ready1,charge=charge,dma_commands=len(commands),dma_bytes=sum(n for _,_,n in commands),
                optimistic_map_decode_and_coverage_budget_ms=1000/60-ready4*8/2625-nonmap_ms,
                budget_if_old_coverage_time_retained_ms=1000/60-ready4*8/2625-nonmap_ms-c['coverage_ms'],
                decoder_master_clocks=None,decoder_body_bytes=None,qualified_for_p2=False)
        row=dict(frame=f,current_changed_words=len(changes),causal_target_words=len(words),actual_target_different_words=len(true_words),
            causal_equal_target_words=len(words-true_words),catchup_words=len(words-changes),
            sent_granules=len(granules),old_sent_word_capacity=8*len(granules),changed_rows=len(coarse_rows),
            map_calls_measured=c['map_mark_calls'],map_master_clocks=c['map_mark_clocks'],
            plan_wire_old=w['plans']+w['plan_control'],plan_wire_new=new_plan_wire,pattern_chunks_old=old_chunks,pattern_chunks_new=new_chunks,
            original_map_wire=map_wire,word_min_map_charge=minimum_charge([(0,i,2) for i in sorted(words)]),
            pattern_batch_charge=pattern_charge,pattern_global_order_minimum=pattern_min,raw_charge=raw_charge,fixed_charge=p['snes']['fixed_charge'],
            corrected_current_wire_plus_mark_coverage_ms=base4*8/2625+c['mark_ms']+c['coverage_ms'],models=models)
        assert models['pairs']['charge']==models['mask8']['charge']==models['mask32']['charge']
        assert row['word_min_map_charge']==sum(n+96 for _,_,n in join([(2,i*2,2) for i in sorted(words)]))
        row['word_charge_with_pattern_order_relaxed']=row['word_min_map_charge']+pattern_min+raw_charge+p['snes']['fixed_charge']
        if f==955:
            assert not changes and len(words)==76
            assert sum(x!=y for x,y in zip(banks[target],current))==100
        rows.append(row);previous=current;banks[target]=current;stale[target].clear()
    assert len(rows)==71
    warm=rows[2:]
    def stats(v):return dict(minimum=min(v),maximum=max(v),total=sum(v))
    report={}
    for name in mode_names:
        report[name]={k:stats([r['models'][name][k] for r in warm]) for k in warm[0]['models'][name] if k not in ('decoder_master_clocks','decoder_body_bytes','qualified_for_p2')}
        report[name].update(over_ready4=[r['frame'] for r in warm if r['models'][name]['ready4']>5468.75],
            over_ready1=[r['frame'] for r in warm if r['models'][name]['ready1']>5468.75],
            over_charge=[r['frame'] for r in warm if r['models'][name]['charge']>4192],
            negative_decoder_budget=[r['frame'] for r in warm if r['models'][name]['optimistic_map_decode_and_coverage_budget_ms']<0],
            negative_if_old_coverage_retained=[r['frame'] for r in warm if r['models'][name]['budget_if_old_coverage_time_retained_ms']<0],
            qualified_for_p2=False)
    return dict(passed=True,stage=247,scope=__doc__,frames=71,word_formats=3,exact_map_bytes=exact_bytes,
        policy_negative_cases=guards(),rows=rows,warm={k:stats([r[k] for r in warm]) for k in rows[0] if k not in ('frame','models')},models=report,
        resources=dict(word_arm_retained_extra=448,old233_margin=1616,arithmetic_margin_after_word_bits=1168,
            arithmetic_above1024_gate=144,full_new_input_arm_approved=False,
            word_snes_bitmap_extra_naive=672,
            word_snes_received_plus_full_bank_flags_extra_logical=161,
            committed_map_validity_full_or_empty_proof=True,committed_bank_checks=213,
            initialization_flags_only_after_final_display_ack=True,stop_discards_both_bank_flags=True,
            manifest_expected_copy_extra=0,manifest_cursor_and_completion_minimum=3,
            decoder_order_state_minimum=2,word_seal_unsplit_bytes=446,existing_payload_limit=240,
            proposed_seal_bytes=190,manifest_bytes=256,manifest_packets=2,extra_manifest_wire=262,
            snes_body_limit=3936,existing_body=3903,new_body=None,new_map_cycles=None),
        preferred_wire_model='mask8',candidate_for_minimal_diagnostic=None,selected_implementation=None,
        negative_counterexamples=dict(last_display_only_frame955_missing_words=76,last_display_only_frame955_wrong_bytes=100,
            coarse_validity_all256_granules_marked_but_uninitialized_words=1792),
        limitations=['Python reconstruction/policy models only;no new C/65816/RTL or whole runtime.',
                    'Word receipt stays256B.Two target-valid maps may become two initialization flags ONLY because accepted map coverage always requires all4096B.',
                    'Initialization is published only at final displayACK;partial failure/commonSTOP invalidates both bases.Received==manifest still required on every warm frame.',
                    'Two ordered256B-total manifest packets must complete before SEAL/DMA;no extra expected256B copy is proposed.',
                    'Outer serial/epoch/sequence/CRC,STOP and displayACK integration remains required,not exercised by this decoder.',
                    'No target-shadow4096B retained on ARM:causal stale words use448B extra;oracle equality is comparison only.',
                    'New mask decoders need sparse stores,range/mask checks and bounded STOP service;old mark timings are NOT reused.',
                    'Positive decoder budget is optimistic:excludes source/ARM/copy/decode/gaps/DMA/display and unknown coverage time.',
                    'Old-coverage timing sensitivity is a conditional scenario,not a lower bound for a rewritten coverage path.',
                    'SPI ready scenarios use observed plan lengths and grouped chunks,not shared-runtime upper bounds.',
                    'Whole FPGA/mapper/new-input ARM and warm VBlank bursts remain jointly open.'],
        product_changed=False,input_hashes=pins,analyzer_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('observer','prior','coalesce','order','relocation','out'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);r=analyze(a)
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','input_hashes')}
    public.update(input_count=len(r['input_hashes']),private_result_sha256=sha(raw))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    flat=[]
    for row in r['rows']:
        out={k:v for k,v in row.items() if k!='models'}
        for name,model in row['models'].items():out.update({name+'.'+k:('UNKNOWN' if v is None else v) for k,v in model.items()})
        flat.append(out)
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(flat[0]),lineterminator='\n');w.writeheader();w.writerows(flat)
    print(json.dumps(dict(passed=r['passed'],frames=r['frames'],exact_map_bytes=r['exact_map_bytes'],policy_negative_cases=r['policy_negative_cases'],
        models={name:{k:r['models'][name][k] for k in ('ready4','charge','over_charge','negative_decoder_budget')} for name in r['models']}),indent=2))


if __name__=='__main__':main()
