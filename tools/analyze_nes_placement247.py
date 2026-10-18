# SPDX-License-Identifier: MIT
"""Same71 placement comparison: measured CPU paths and explicit wire models.

No new ARM/FPGA/65816 implementation or timing bound. A positive residual
is a shared allowance for ALL unmeasured work, never an FPS prediction.
"""
from pathlib import Path
import argparse,csv,json,struct,shutil
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_spantrade247 import spans
from analyze_nes_mapjoint247 import bitmap

PERIOD=1000/60
CLOCKS_PER_MS=21477.270
BYTE_MS=8/2625
CHUNK_CAPACITY=2048
CHUNK_HEADER=32
CERTIFICATE_BYTES=32
# Existing bulk accounting: descriptor/op7=43B, two modeled status polls=40B.
# New typed width adds a separately swept extension, not silently free bytes.
BASE_CHUNK_CONTROL=83


def chunks(ranges,data):
    """Proposed local FPGA output: 32B header + <dst16,src16,n16> + values.

    Six-byte descriptors and payload BOTH consume the existing2KiB buffer.
    Header values/CDC/control protocol are not implemented by this model.
    """
    result=[];group=[];size=CHUNK_HEADER
    for at,n in ranges:
        if size+6+n>CHUNK_CAPACITY:
            result.append(pack(group,data));group=[];size=CHUNK_HEADER
        group.append((at,n));size+=6+n
    if group:result.append(pack(group,data))
    return result


def pack(group,data):
    offset=CHUNK_HEADER+6*len(group);descriptors=bytearray();payload=bytearray()
    for at,n in group:
        descriptors+=struct.pack('<HHH',at,offset+len(payload),n)
        payload+=data[at:at+n]
    blob=bytes(CHUNK_HEADER)+descriptors+payload
    assert len(blob)<=CHUNK_CAPACITY
    return len(group),blob


def apply_chunks(items,base,expected,initialized):
    """Independent policy oracle, not endpoint token/CDC verification."""
    out=bytearray(base);seen=set();last=0
    for count,b in items:
        if not 0<count or not CHUNK_HEADER+6*count<len(b)<=CHUNK_CAPACITY:
            raise ValueError('chunk bounds')
        cursor=CHUNK_HEADER+6*count
        for i in range(count):
            dst,src,n=struct.unpack_from('<HHH',b,CHUNK_HEADER+6*i)
            if dst&1 or n&1 or not 0<n<=64 or dst<last or dst+n>4096:
                raise ValueError('destination bounds/order')
            if src!=cursor or src+n>len(b):raise ValueError('payload bounds/order')
            out[dst:dst+n]=b[src:src+n];seen.update(range(dst//2,(dst+n)//2))
            cursor+=n;last=dst+n
        if cursor!=len(b):raise ValueError('trailing payload')
    if bitmap(seen)!=expected:raise ValueError('exact receipt')
    if not initialized and len(seen)!=2048:raise ValueError('cold coverage')
    return bytes(out)


def guards():
    data=bytes((i*31+5)&255 for i in range(4096));rr=[(0,2),(16,4),(4094,2)]
    bb=bitmap({0,8,9,2047});cc=chunks(rr,data);count,b=cc[0];cases=[]
    def mutation(offset,value):
        q=bytearray(b);struct.pack_into('<H',q,offset,value);return [(count,bytes(q))]
    for offset,value in [(32,1),(32,4096),(34,0),(36,0),(36,66),(36,3),
                         (38,0),(40,2047),(44,4096)]:
        cases.append((mutation(offset,value),bb,True))
    cases += [([(count,b[:-1])],bb,True), (cc+cc,bb,True),
              ([],bb,True),(cc,bytes(256),True),(cc,bb,False)]
    for item,manifest,init in cases:
        try:apply_chunks(item,bytes(4096),manifest,init)
        except ValueError:pass
        else:raise AssertionError('bad typed policy accepted')
    return len(cases)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False);pins={}
    probe=BASE/'probes/nes-wholepath247'
    def pin(f,expected=None):
        digest=sha(f)
        if expected is not None:assert digest==expected,f
        pins[f.resolve().relative_to(BASE).as_posix()]=digest;return f
    def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
    old=read(probe/'validation-analysis02/result.json')
    actual=read(probe/'jointdecode-analysis03/result.json')
    linear=read(probe/'spantrade02/result.json')
    model=read(probe/'mapjoint03/result.json')
    dma=read(ROOT/'analysis/dma247-verification.json')
    relocation={int(r['frame']):r for r in csv.DictReader(pin(ROOT/'analysis/relocation247-frames.csv').open())}
    for name in ('nes_native_runtime165.c','nes_sink_window184.c','nes_plan_service200.c'):
        pin(BASE/'probes/nes-runtime233/arm01/src'/name)
    setup_samples=dma['no_wait_command_residual_after_8x_payload']
    final_samples=dma['no_wait_warm_final_master_clocks']
    assert old['passed'] and actual['passed'] and linear['passed'] and model['passed']
    for n in ('analyze_nes_spantrade247.py','analyze_nes_mapjoint247.py',
              'analyze_nes_validation247.py','analyze_nes_wholepath247.py',
              'nes_bulk194.py','nes_bulk195.py','nes_delta231.py'):
        pin(ROOT/'tools'/n)
    for n in ('src/nes/rtl/nes_bulk_control194.sv','src/nes/firmware/nes_sink_bulk195.inc',
              'docs/nes-relocation247-contract.ko.md','docs/nes-gap247-contract.ko.md'):
        pin(ROOT/n)
    map_packets={g:[] for g in range(1,72)}
    for fn in sorted((probe/'jointdecode-test02/run').glob('req-*.bin')):
        b=fn.read_bytes()
        if b[0]==9:
            pin(fn,actual['input_hashes'][fn.relative_to(BASE).as_posix()])
            map_packets[int.from_bytes(b[8:10],'little')].append(b)
    results=[];details=[];banks=[bytes(4096),bytes(4096)];init=[False,False]
    stale=[set(range(2048)),set(range(2048))];last=bytes(4096);checked=0
    for index,(baseline,measured) in enumerate(zip(old['rows'],actual['rows'])):
        f=905+index;g=index+1;bank=index%2
        assert baseline['frame']==measured['frame']==f
        path=probe/f'jointdecode-test02/run/expected-{g}.bin'
        current=pin(path,actual['input_hashes'][path.relative_to(BASE).as_posix()]).read_bytes()[:4096]
        changed={w for w in range(2048) if current[w*2:w*2+2]!=last[w*2:w*2+2]}
        for s in stale:s.update(changed)
        words=set(stale[bank]);rr=spans(words,0,64);cc=chunks(rr,current)
        assert apply_chunks(cc,banks[bank],bitmap(words),init[bank])==current
        checked+=4096;stale[bank].clear();last=current;banks[bank]=current;init[bank]=True
        assert len(rr)==measured['map_records'] and len(words)==measured['map_words']
        local_bytes=sum(len(b) for n,b in cc);values=sum(n for at,n in rr)
        fixed=baseline['mark_ms']+baseline['coverage_ms']
        retained=baseline['mark_ms']+baseline['mask_ms']+baseline['manifest_ms']+baseline['coverage_ms']
        source=relocation[f]
        source_wire=int(source['projected_input_payload'])+19*int(source['projected_input_blocks'])+32
        record=dict(frame=f,runs=len(rr),values_bytes=values,chunks=len(cc),
                    local_chunk_bytes=local_bytes,maximum_local_chunk=max([len(b) for n,b in cc] or [0]),
                    staging_dma_count=len(rr),charge=baseline['charge'],vblanks=baseline['vblanks'])
        details.append(record)
        def add(name,wire,known,extra=None):
            # Perfect-resource overlap is a necessary-floor sensitivity ONLY:
            # frame dependencies and bus/CPU/DMA conflicts are not scheduled.
            row=dict(frame=f,placement=name,ready4_bytes=wire,spi_ms=wire*BYTE_MS,
                     retained_or_measured_ms=known,conditional_serial_ms=wire*BYTE_MS+known,
                     remaining_all_unknown_ms=PERIOD-wire*BYTE_MS-known,
                     optimistic_resource_floor_ms=max(wire*BYTE_MS,known),
                     source_spi_bytes=source_wire,source_spi_ms=source_wire*BYTE_MS,
                     output_spi_bytes=wire-source_wire,
                     seal_coverage_tail_ms=baseline['coverage_ms'],
                     charge=baseline['charge'],actual_new_implementation=False)
            if extra:row.update(extra)
            # Changed-boundary CPU time is NOT supplied by these samples.
            # Reuse unchanged final list's observed normalization only as a
            # low/high sensitivity, not a safe bound or measured new frame.
            for end in ('minimum','maximum'):
                final_ms=(baseline['dma_bytes']*8+baseline['commands']*setup_samples[end]+final_samples[end])/CLOCKS_PER_MS
                row['display_sensitivity_'+end+'_ms']=final_ms
                row['serial_with_display_'+end+'_ms']=wire*BYTE_MS+known+final_ms
                row['remaining_after_display_'+end+'_ms']=PERIOD-wire*BYTE_MS-known-final_ms
                row['overlap_resource_floor_'+end+'_ms']=max(wire*BYTE_MS,known+final_ms)
                # Input COMMITTED precedes BEGIN/planner/output in runtime233.
                # Only the output phase may overlap this frame's SNES work.
                # coverage212 runs only after SEAL: it cannot be hidden under
                # this frame's DATA SPI. Keep that tail outside the maximum.
                tail=baseline['coverage_ms']
                row['input_barrier_overlap_'+end+'_ms']=source_wire*BYTE_MS+max((wire-source_wire)*BYTE_MS,known-tail)+tail+final_ms
            for clocks in (500,1000,1500):
                if 'runs' in row:
                    cost=row['runs']*clocks/CLOCKS_PER_MS
                    row['typed_setup_'+str(clocks)+'_ms']=cost
                    row['required_overlap_'+str(clocks)+'_ms']=max(0,row['serial_with_display_maximum_ms']+cost-PERIOD)
                    tail=baseline['coverage_ms']
                    row['input_barrier_setup_'+str(clocks)+'_ms']=source_wire*BYTE_MS+max((wire-source_wire)*BYTE_MS,known-tail+cost)+tail+row['display_sensitivity_maximum_ms']
            results.append(row)
        add('SNES_measured_5886',baseline['wire_ready4'],retained)
        add('SNES_measured_2472',measured['wire_ready4'],sum(measured[k+'_ms'] for k in ('mark','mask','manifest','coverage')))
        # ARM expands to ordinary literal packets; receiver checks remain.
        span=next(r for r in linear['rows'] if r['frame']==f and r['mode']=='literal_exact64')
        add('ARM_literal_exact64',span['ready4'],fixed+baseline['manifest_ms'])
        # Compare before and after charging typed handoff/certificate costs.
        # Input packed records + exact manifest are STILL sent over SPI.
        for extension in (0,16,32):
            wire=measured['wire_ready4']+(BASE_CHUNK_CONTROL+extension)*len(cc)+CERTIFICATE_BYTES
            # 8clk/B is a normalization sensitivity, not new DMA WCET.
            payload_ms=values*8/CLOCKS_PER_MS
            add('FPGA_typed_ext'+str(extension),wire,fixed+payload_ms,
                dict(staging_payload_normalization_ms=payload_ms,runs=len(rr),chunks=len(cc),
                     handoff_extra_bytes=(BASE_CHUNK_CONTROL+extension)*len(cc)+CERTIFICATE_BYTES,
                     per_run_shared_allowance_us=(PERIOD-wire*BYTE_MS-fixed-payload_ms)*1000/max(1,len(rr))))
        # ARM-prepared local layout forwarded through240B SPI packets. It can
        # simplify FPGA parsing, but still needs endpoint receipt validation.
        # Replace only map payload/envelopes in packed2472; manifest retained.
        # Original DATA grouping is used to recompute every new fragment poll.
        packed=map_packets[g]
        packet_count=sum((len(b)+239)//240 for n,b in cc)
        oldcount=measured['actual_nonbulk_data_packets'];newcount=oldcount-len(packed)+packet_count
        delta=local_bytes+19*packet_count-sum(len(b)-16+19 for b in packed)+20*((newcount+3)//4-(oldcount+3)//4)
        wire=measured['wire_ready4']+delta+99*len(cc)+CERTIFICATE_BYTES
        add('ARM_layout_FPGA_checked',wire,fixed+values*8/CLOCKS_PER_MS,
            dict(layout_spi_delta=delta,runs=len(rr),chunks=len(cc),
                 per_run_shared_allowance_us=(PERIOD-wire*BYTE_MS-fixed-values*8/CLOCKS_PER_MS)*1000/max(1,len(rr))))
    summary={}
    for name in dict.fromkeys(r['placement'] for r in results):
        warm=[r for r in results if r['placement']==name and r['frame']>=907]
        worst=min(warm,key=lambda r:r['remaining_all_unknown_ms'])
        summary[name]=dict(warm_frames=len(warm),ready4_max=max(r['ready4_bytes'] for r in warm),
          conditional_serial_max_ms=max(r['conditional_serial_ms'] for r in warm),
          remaining_min_ms=worst['remaining_all_unknown_ms'],limiting_frame=worst['frame'],
          negative_residual_frames=[r['frame'] for r in warm if r['remaining_all_unknown_ms']<0],
          optimistic_resource_floor_max_ms=max(r['optimistic_resource_floor_ms'] for r in warm),
          serial_with_display_sample_max_ms=max(r['serial_with_display_maximum_ms'] for r in warm),
          negative_after_display_sample_frames=[r['frame'] for r in warm if r['remaining_after_display_maximum_ms']<0],
          overlap_resource_floor_sample_max_ms=max(r['overlap_resource_floor_maximum_ms'] for r in warm),
          input_barrier_overlap_sample_max_ms=max(r['input_barrier_overlap_maximum_ms'] for r in warm),
          input_barrier_over_frames=[r['frame'] for r in warm if r['input_barrier_overlap_maximum_ms']>PERIOD],
          frame954=next(r for r in warm if r['frame']==954),qualified_for_p2=False)
    result=dict(passed=True,scope=__doc__,frames=71,exact_map_bytes=checked,typed_policy_negatives=guards(),
      typed_layout=dict(chunk_capacity=CHUNK_CAPACITY,header_reservation=CHUNK_HEADER,descriptor_bytes=6,
                        certificate_reservation=CERTIFICATE_BYTES,base_control_bytes=BASE_CHUNK_CONTROL,
                        control_extensions=[0,16,32],receipt_bytes=256,receipt_dedicated_m9k_scenario=1,
                        new_persistent_map_bytes=0,maximum_chunk_bytes=max(r['maximum_local_chunk'] for r in details),
                        warm_chunks=sum(r['chunks'] for r in details[2:]),warm_runs=sum(r['runs'] for r in details[2:])),
      memory_arithmetic=dict(reference240_m9k=54,program4_to6=2,semantic_base_reclaim=1,
                             new_receipt_scenario=1,total=56,device_m9k=56,margin=0,
                             raw_base_extra_m9k=2,with_raw_base=58,wholeboard_fit=False,
                             existing_LE_deficit=490,existing_LAB_deficit=40,new_logic_unknown=True,
                             word_ARM_extra=448,old233_margin=1616,remaining_ARM_arithmetic=1168,
                             above1024_gate_arithmetic=144,new_ARM_run_IRQ=False),
      display_sensitivity=dict(list_residual_clocks=setup_samples,final_clocks=final_samples,
                               actual_new_path_measurement=False,wcet=False,waits_excluded=True),
      summary=summary,rows=results,details=details,input_hashes=pins,script_sha256=sha(Path(__file__)),
      preferred_next_comparison='ARM planner retained, narrow FPGA map validation, SNES typed DMA/display; requires bounded output-phase overlap and wholeboard area,not yet selected for implementation',
      implementation_selected=None,product_changed=False,physical=False,
      limitations=['New typed layout is Python-only;no FPGA/ARM/65816 implementation or measured time.',
        'All models keep semantic449+rowshift input SPI and existing plans/nonmap data;ARM refill is counted.',
        'Retained nonmap mark/coverage timings are conditional reuse,not new-path timing bounds.',
        '8masterclocks/B staging normalization excludes setup/refresh/service/descriptor/CDC stalls.',
        'Residual must cover source prepare,ARM work,FPGA parser,staging setup,service,outer dispatch,gaps and final display;no positive result is60fps approval.',
        'Perfect-resource overlap is an overly optimistic diagnostic. Input-barrier column retains runtime233 COMMITTED-before-BEGIN ordering;output4packet queue already overlaps some work,not a new feature.',
        'Even input-barrier overlap aggregates output work ideally;chunk readiness,op7 barriers,ARM planner/IRQ,CRC,source and stalls remain unbounded.',
        'SEAL coverage is a mandatory tail outside output max;placement04 incorrectly allowed this tail to overlap DATA and is superseded by05.',
        'Final list sensitivity reuses old232 no-wait samples1218..1586 plus warm final9284..9442;not a new-path measurement or WCET. VBlank waits remain excluded.',
        '500/1000/1500clocks per typed run are sensitivity parameters,not measured instructions. Required overlap still excludes ARM/source/FPGA/gaps.',
        '83B bulk control is existing-model reuse;16/32B extensions are explicit sensitivity,not final protocol.',
        '32B certificate is reserved within190+32=222B SEAL;binding fields and counter widths remain unimplemented.',
        'Receipt checking is moved to FPGA,not replaced by hash. SNES checks chunk bounds/token/sequence and final certificate before display.',
        'Aperture reuse requires tile phase drained first;buffers cannot contain immutable tile and metadata simultaneously.',
        'One dedicated receipt M9K is capacity arithmetic;unused scratch space is not assumed available.',
        'Final VRAM list/write set and remaining952/955 bursts unchanged;global ordering minimum9554198 still exceeds4192 policy.',
        'Full planner unchanged arrays18752B need at least17M9K versus prior optimistic12 reclaimable;redesigned fullB remains unknown.'])
    raw=a.out/'result.json';raw.write_text(json.dumps(result,indent=2)+'\n')
    public={k:v for k,v in result.items() if k not in ('rows','details','input_hashes')}
    public.update(input_count=len(pins),private_result_sha256=sha(raw))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n')
    fields=list(dict.fromkeys(k for r in results for k in r))
    for name,rows,keys in [('frames.csv',results,fields),('chunks.csv',details,list(details[0]))]:
        with (a.out/name).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=keys,lineterminator='\n');w.writeheader();w.writerows(rows)
    shutil.copyfile(__file__,a.out/'analyzer.py')
    print(json.dumps(dict(passed=True,exact_map_bytes=checked,typed_policy_negatives=result['typed_policy_negatives'],
      summary={k:{x:v[x] for x in ('ready4_max','conditional_serial_max_ms','remaining_min_ms','limiting_frame')} for k,v in summary.items()}),indent=2))


if __name__=='__main__':main()
