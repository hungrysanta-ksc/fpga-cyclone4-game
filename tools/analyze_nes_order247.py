# SPDX-License-Identifier: MIT
"""Independent bounded-order command oracle and actual receive/coverage timing."""
from pathlib import Path
import argparse,csv,json,re
from nes_delta231 import BASE,sha


def analyze(model,build,host,test,append):
    pins={}
    def pin(p):pins[p.resolve().relative_to(BASE).as_posix()]=sha(p);return p
    def read(p):return json.loads(pin(p).read_text(encoding='utf-8'))
    m=read(model);b=read(build/'result.json');h=read(host/'result.json');t=read(test/'result.json');a=read(append/'result.json')
    assert m['passed'] and h['passed'] and a['passed'] and t['passed'] and t['commits']==71
    assert b['body_bytes']==3903 and b['post_seal_scan'] is False
    for n,digest in t['inputs'].items():assert sha(BASE/n)==digest;pin(BASE/n)
    for n,digest in h['output_hashes'].items():assert sha(host/n)==digest;pin(host/n)
    pin(test/'run/capture.lua');pin(test/'run/mesen.log');pin(build/'body.bin');pin(build/'labels.json')
    assert sha(host/'order247.h')==a['helper_sha256']==sha(append/'order247.h')
    actual_order=list(csv.DictReader(pin(test/'run/order247.csv').open()))
    phases=list(csv.DictReader(pin(test/'run/order-phase247.csv').open()))
    warnings=[int(x,16) for x in re.findall(r'Uninitialized memory read: \$([0-9A-Fa-f]+)',(test/'run/mesen.log').read_text(errors='replace'))]
    # The exact used/valid check is the unchanged Lua and C reference replay.
    # For warnings allow only pattern gap addresses, never an uploaded unit.
    allowed=set();rows=[];command_count=byte_count=0
    for detail,work in zip(m['details'],m['rows']):
        f=work['frame'];assert detail['frame']==f;gen=f-904;bank=(gen-1)%2
        order=[(int(r['kind']),int(r['slot']),int(r['encoded_bytes'])) for r in actual_order if int(r['generation'])==gen]
        assert order==[(r['kind'],r['slot'],r['encoded_bytes']) for r in detail['ordered']]
        expected=[];received={k:set() for k in (0,1)}
        for r in detail['ordered']:received[r['kind']].update(range(r['slot']*r['size'],(r['slot']+1)*r['size']))
        for kind,at,n in detail['batch_commands']:
            src,da,db={0:(0,0,0xc000),1:(0x4000,0x4000,0x8000),2:(0x5000,0x6000,0xa000),5:(0x6961,0x5000,0x9000)}[kind]
            expected.append(dict(source=bank*0x8000+src+at,destination=(db if bank else da)+at,bytes=n))
            if kind<2:allowed.update(0x7f0000+bank*0x8000+src+i for i in range(at,at+n) if i not in received[kind])
        actual=[{k:int(v) for k,v in r.items()} for r in csv.DictReader(pin(test/f'run/commands-{gen}.csv').open())]
        assert actual==expected,(f,'descriptor difference');command_count+=len(actual);byte_count+=sum(r['bytes'] for r in actual)
        pp=[r for r in phases if int(r['generation'])==gen];times={};pending={};counts={}
        for r in pp:
            name=r['event'];clock=int(r['master_clock'])
            if name in ('mark212','coverage212'):assert name not in pending;pending[name]=clock
            else:
                key='mark212' if name=='mark_return247' else 'coverage212';assert key in pending
                times[key]=times.get(key,0)+clock-pending.pop(key);counts[key]=counts.get(key,0)+1
        assert not pending and counts['coverage212']==1
        vblanks=int(pin(test/f'run/vblank-{gen}.txt').read_text())
        receive=times['mark212']/21477.270;coverage=times['coverage212']/21477.270
        rows.append(dict(frame=f,commands=len(actual),dma_bytes=sum(r['bytes'] for r in actual),
            charge=work['batch_sorted_gap_charge'],vblanks=vblanks,mark_calls=counts['mark212'],
            mark_master_clocks=times['mark212'],mark_ms=receive,coverage_master_clocks=times['coverage212'],coverage_ms=coverage,
            semantic16_wire_plus_mark_coverage_ms=work['semantic16_ready4_wire_bytes']*8/2625+receive+coverage))
    assert len(rows)==71 and command_count==t['vram_commands'] and byte_count==t['vram_bytes']
    assert warnings and set(warnings)<=allowed,sorted(set(warnings)-allowed)[:8]
    warm=rows[2:]
    def stats(k):v=[r[k] for r in warm];return dict(minimum=min(v),maximum=max(v),total=sum(v))
    return dict(stage=247,passed=True,scope=__doc__,actual_frames=71,exact_command_frames=71,exact_order_frames=71,
        body_bytes=3903,body_free=33,post_seal_scan=False,extra_persistent_bytes=0,
        commands=command_count,dma_bytes=byte_count,warm={k:stats(k) for k in rows[0] if k!='frame'},
        warm_multi_vblank=[r['frame'] for r in warm if r['vblanks']>1],
        conditional_serial_over_16_67=[r['frame'] for r in warm if r['semantic16_wire_plus_mark_coverage_ms']>1000/60],
        uninitialized_warnings=len(warnings),unique_uninitialized_addresses=len(set(warnings)),
        warnings_only_pattern_gap=True,actual_append_crc_end_cases=a['cases'],
        limitations=['Replay C fixture stores up to15 converted pixels on the host;not new ARM allocation or real FPGA order execution.',
                     'Replay sends one bulk per plan(598 total);actual FPGA2048B coalescing may reduce mark calls.The measured mark sum is not a physical lower bound.',
                     'Production insertion reuses encoded[32] within existing append, but full new-input ARM RUN/IRQ and timing are unverified.',
                     'Mark timing includes original bitmap validation plus list append,not just added work;no old-mark subtraction or free receive claim.',
                     'Conditional semantic16 wire+mark+coverage excludes copy/decode/ARM/source/gaps/DMA/display and assumes serialization;not pipeline impossibility.',
                     'No changed4192 policy,STOP fault injection,full FPGA or physical FPS approval.',
                     'C helper uses forward insertion;earlier backward-comparison model counts are not actual C comparisons.15-record bound still105.'],
        selected_implementation=None,product_changed=False,rows=rows,input_hashes=pins,analyzer_sha256=sha(Path(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ('model','build','host','test','append','out'):p.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=analyze(*(getattr(a,k).resolve() for k in ('model','build','host','test','append')))
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','input_hashes')};public.update(private_result_sha256=sha(raw),input_count=len(r['input_hashes']))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(r['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(r['rows'])
    print(json.dumps(public,indent=2))


if __name__=='__main__':main()
