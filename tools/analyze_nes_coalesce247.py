# SPDX-License-Identifier: MIT
"""Compare grouped receive timings and exact payloads against individual tiles."""
from pathlib import Path
import argparse,csv,json
import analyze_nes_order247 as prior
from prepare_nes_coalesce247 import COALESCE
from nes_delta231 import BASE,sha


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('model','build','host','test','append','individual','individual-analysis','range16','range8','guards','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
    r=prior.analyze(*(getattr(a,k).resolve() for k in ('model','build','host','test','append')))
    pins=r['input_hashes']
    def pin(f):pins[f.resolve().relative_to(BASE).as_posix()]=sha(f);return f
    def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
    def csvrows(f):return [{k:int(v) for k,v in x.items()} for x in csv.DictReader(pin(f).open())]
    guards=read(a.guards/'result.json');assert guards['passed'] and guards['cases']==4
    for n,digest in guards['output_hashes'].items():assert sha(pin(a.guards/n))==digest
    assert guards['helper_sha256']==__import__('hashlib').sha256(COALESCE.encode()).hexdigest()
    assert COALESCE in (a.host/'host.c').read_text(encoding='utf-8')
    oldphase=read(a.individual_analysis)['rows']
    oldtiles={};oldcalls={};oldbytes=0
    for f in sorted((a.individual/'run').glob('req-*.bin')):
        b=f.read_bytes()
        if b[0]!=7:continue
        pin(f);g=int.from_bytes(b[8:10],'little');at=int.from_bytes(b[10:12],'little')
        payload=pin(f.with_name(f.name.replace('req-','tile-'))).read_bytes()
        assert len(payload)==(32 if b[1] else 16)
        key=(g,b[1],at);assert key not in oldtiles;oldtiles[key]=payload
        oldcalls[g]=oldcalls.get(g,0)+1;oldbytes+=len(payload)
    order=csvrows(a.test/'run/order247.csv');expected=[]
    for item in order:
        g,k,slot=item['generation'],item['kind'],item['slot'];unit=32 if k else 16
        if expected and expected[-1]['generation']==g and expected[-1]['kind']==k and expected[-1]['slot']+expected[-1]['bytes']//unit==slot and expected[-1]['bytes']+unit<=2048:
            expected[-1]['bytes']+=unit
        else:expected.append(dict(generation=g,kind=k,slot=slot,bytes=unit))
    chunks=csvrows(a.test/'run/chunks247.csv');assert chunks==expected
    actual=[];byte_checks=0;seen=set()
    for f in sorted((a.test/'run').glob('req-*.bin')):
        b=f.read_bytes()
        if b[0]!=7:continue
        pin(f);g=int.from_bytes(b[8:10],'little');k=b[1];at=int.from_bytes(b[10:12],'little');n=int.from_bytes(b[14:16],'little');unit=32 if k else 16
        assert n and n<=2048 and n%unit==at%unit==0
        assert int.from_bytes(b[16:20],'little')==0x23200000+len(actual)
        payload=pin(f.with_name(f.name.replace('req-','tile-'))).read_bytes()
        keys=[(g,k,i) for i in range(at,at+n,unit)]
        assert not seen.intersection(keys);seen.update(keys)
        assert payload==b''.join(oldtiles[key] for key in keys)
        byte_checks+=len(payload);actual.append(dict(generation=g,kind=k,slot=at//unit,bytes=n))
    assert actual==expected and seen==set(oldtiles) and byte_checks==oldbytes
    # Normal successful packets execute the unique mark call once per data
    # packet (2/4/5/7/8). Associate their ordered calls, never a failed trace.
    packets={};phase={};pending={}
    for f in sorted((a.test/'run').glob('req-*.bin')):
        b=f.read_bytes();pin(f)
        if b[0] in (2,4,5,7,8):packets.setdefault(int.from_bytes(b[8:10],'little'),[]).append(b[1])
    for x in csv.DictReader((a.test/'run/order-phase247.csv').open()):
        g=int(x['generation']);e=x['event'];t=int(x['master_clock'])
        if e=='mark212':assert g not in pending;pending[g]=t
        elif e=='mark_return247':phase.setdefault(g,[]).append(t-pending.pop(g))
    assert not pending
    names={0:'pattern',1:'pattern',2:'map',3:'cgram',4:'oam',5:'raw'}
    for row,old in zip(r['rows'],oldphase):
        assert row['frame']==old['frame'];g=row['frame']-904
        count=sum(c['generation']==g for c in chunks)
        assert old['mark_calls']-row['mark_calls']==oldcalls[g]-count
        row.update(individual_mark_calls=old['mark_calls'],individual_mark_master_clocks=old['mark_master_clocks'],
                   mark_saved_master_clocks=old['mark_master_clocks']-row['mark_master_clocks'],pattern_chunks=count,
                   individual_pattern_chunks=oldcalls[g],coverage_delta_master_clocks=row['coverage_master_clocks']-old['coverage_master_clocks'])
        assert len(packets[g])==len(phase[g])==row['mark_calls']
        assert sum(phase[g])==row['mark_master_clocks']
        for name in sorted(set(names.values())):
            row[name+'_mark_clocks']=sum(t for k,t in zip(packets[g],phase[g]) if names[k]==name)
            row[name+'_mark_calls']=sum(names[k]==name for k in packets[g])
    ranges=[]
    for bits,path in ((16,a.range16),(8,a.range8)):
        b=read(path/'result.json');pin(path/'body.bin');pin(path/'builder.py')
        assert b['mask_bits']==bits and b['body_bytes']>3936 and b['program_bytes']==8192
        assert b['script_sha256']==sha(path/'builder.py')
        ranges.append(dict(mask_bits=bits,body_bytes=b['body_bytes'],body_excess=-b['body_free'],
                           decision='REJECT_current_4KiB_capacity',functional_tested=False,timing_measured=False))
    pin(BASE/'repository-nes-milestone/src/nes/rtl/nes_tile_bulk193.sv')
    warm=r['rows'][2:]
    for k in ('individual_mark_calls','individual_mark_master_clocks','mark_saved_master_clocks','pattern_chunks','individual_pattern_chunks','coverage_delta_master_clocks'):
        values=[x[k] for x in warm];r['warm'][k]=dict(minimum=min(values),maximum=max(values),total=sum(values))
    for k in sorted(key for key in warm[0] if key.endswith(('_mark_clocks','_mark_calls')) and key not in r['warm']):
        values=[x[k] for x in warm];r['warm'][k]=dict(minimum=min(values),maximum=max(values),total=sum(values))
    r.update(scope=__doc__,range_builds=ranges,grouped_chunks=len(chunks),individual_chunks=len(oldtiles),
             exact_grouped_payload_bytes=byte_checks,grouping_model_matches_packets=True,consumer_binary_unchanged=True,
             grouping_guard_cases=guards['cases'],grouping_guard_bytes=guards['payload_bytes'],
             analyzer_sha256=sha(Path(__file__)),upstream_analyzer_sha256=sha(Path(prior.__file__)))
    r['limitations']=[
        'Existing193 same-generation/kind/contiguous-slot/2048B rules are a host payload model,not actual RTL CDC/two-bank/token/backpressure timing.',
        'The grouping persists across encoded plan batches;END flushes it.Full ARM drain/deadline/STOP integration is unverified.',
        'Host fixture2048B and15 converted tiles are not new ARM allocations or product changes.',
        'Same3903B consumer;range-mask16/8 builds3971/3950B rejected on capacity before functional/timing tests.',
        'Mark savings cover measured routine calls only;copy/decode/CRC/source/ARM/gaps/DMA/display remain outside.',
        'Same coverage instructions do not imply identical master clocks;per-frame timing variation is reported,not attributed to a code change.',
        'Section timings associate ordered successful data packets with the unique mark call;not a fault-trace attribution.',
        'Synthetic fixture tokens were checked;no new FPGA token/STOP fault test or physical FPS claim.',
        '4192 policy,production227,GBC164 and SRAM unchanged;whole area/ARM/display ownership gates remain open.'
    ]
    raw=a.out/'result.json';raw.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
    public={k:v for k,v in r.items() if k not in ('rows','input_hashes')}
    public.update(private_result_sha256=sha(raw),input_count=len(pins))
    (a.out/'summary.json').write_text(json.dumps(public,indent=2)+'\n',encoding='utf-8')
    with (a.out/'frames.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(r['rows'][0]),lineterminator='\n');w.writeheader();w.writerows(r['rows'])
    print(json.dumps(public,indent=2))


if __name__=='__main__':main()
