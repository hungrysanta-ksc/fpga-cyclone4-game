# SPDX-License-Identifier: MIT
"""Same-byte-boundary area/time comparison; explicit stimulus cost accounting."""
from pathlib import Path
import argparse,csv,json,re,shutil
from nes_delta231 import BASE,sha
from analyze_nes_joint253 import area


def stream_cost(commands):
    """Exact normal driver occupancy, not a hardware transport performance bound.

    Every byte is offered for one rising edge with a one-cycle gap. A two-cycle
    producer pause follows byte indices divisible by11. The final byte stalls
    256cycles. The post-final producer pause falls outside STREAM.
    """
    result={};frame=904
    for c in commands:
        op=c>>60
        if op==1:
            frame+=1;result[frame]=dict(bytes=0,ranges=0,stream_cycles=0)
        if op!=2:continue
        first=(c>>12)&4095;count=c&4095;mode=(c>>32)&1
        n=count*(2 if mode else 32 if 1024<=first<1152 else 16)
        r=result[frame];r['bytes']+=n;r['ranges']+=1
        r['stream_cycles']+=2*n+2*((n-1+10)//11)+256
    return result


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('out','test','reference','incremental','consumer-guards','map','reference-map'):
        p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True);pins={}
    def pin(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f
    def read(f):return json.loads(pin(f).read_text(encoding='utf-8'))
    def rows(f):return list(csv.DictReader(pin(f).open(encoding='utf-8')))
    def run(path):
        r=read(path/'result.json');assert r['passed']
        for n,h in r['rtl_hashes'].items():assert sha(pin(path/n))==h
        for n,h in r['input_hashes'].items():
            f=BASE/n
            if sha(f)!=h:f=path/f.name
            assert sha(pin(f))==h,(path,n)
        return r
    test=run(a.test);ref=run(a.reference);inc=run(a.incremental);extra=run(a.consumer_guards)
    mapped=run(a.map);rm=run(a.reference_map)
    assert test['frames']==ref['frames']==71
    assert test['guards']==ref['guards']==list(range(1,29))
    assert inc['frames']==4 and inc['incremental_shadow_granules']==8
    assert test['rtl_hashes']==inc['rtl_hashes']==extra['rtl_hashes']==mapped['rtl_hashes']
    assert extra['frames']==1 and extra['guards']==list(range(22,29))
    assert ref['rtl_hashes']==rm['rtl_hashes']
    prior=BASE/'probes/nes-joint254'
    old=read(prior/'analysis01/result.json')
    # Normalize the module identifier only; decimal255 is real bitmap data.
    reference_core=pin(a.reference/'nes_core255.sv').read_text().replace('nes_core255','nes_core254')
    reference_core=reference_core.replace(' output wire consume_lease_ok,\n','').replace(' wire live,lease_ok;assign consume_lease_ok=lease_ok;', ' wire live,lease_ok;')
    assert reference_core==pin(prior/'test03/nes_core254.sv').read_text()
    def table(path):return {int(r['frame']):{k:int(v) for k,v in r.items()} for r in rows(path)}
    src=table(a.test/'cycles.csv');rsrc=table(a.reference/'cycles.csv');oldsrc=table(prior/'test03/cycles.csv')
    out=table(a.test/'output-cycles.csv');rout=table(a.reference/'output-cycles.csv');oldout=table(prior/'test03/output-cycles.csv')
    traffic=table(a.test/'stream-cycles.csv');rt=table(a.reference/'stream-cycles.csv')
    assert {f:{k:v for k,v in r.items() if k!='stream_stage_cycles'} for f,r in traffic.items()}=={f:{k:v for k,v in r.items() if k!='stream_stage_cycles'} for f,r in rt.items()}
    for name in ('blocks.txt','commands.hex','expected.hex','certs.hex','hashes.hex','stream.hex','sink.hex'):
        assert pin(a.test/name).read_bytes()==pin(a.reference/name).read_bytes(),name
    assert pin(a.test/'blocks.txt').read_bytes()==pin(prior/'test03/blocks.txt').read_bytes()
    costs=stream_cost([int(v,16) for v in pin(a.test/'commands.hex').read_text().split()])
    for path in (a.reference,a.incremental):
        for f,r in table(path/'stream-cycles.csv').items():
            assert r['stream_stage_cycles']==costs[f]['stream_cycles'],(path,f,r,costs[f])
    detail=[]
    for f in range(905,976):
        s=src[f];b=rsrc[f];o=out[f];bo=rout[f];c=costs[f];t=traffic[f]
        assert s['queries']==b['queries']==oldsrc[f]['queries']
        assert s['transfer']==b['transfer']==oldsrc[f]['transfer']
        assert o['transport_crc_cycles']==bo['transport_crc_cycles']==oldout[f]['transport_crc_cycles']
        assert c['bytes']==t['accepted'] and c['ranges']==t['ranges'] and t['stalled']==256*c['ranges']
        detail.append(dict(frame=f,source_cycles=s['total'],reference_source_cycles=b['total'],
            source_delta=s['total']-b['total'],prepare=s['prepare'],prepare_delta=s['prepare']-b['prepare'],
            output_cycles=o['total'],reference_output_cycles=bo['total'],output_delta=o['total']-bo['total'],
            accepted_bytes=t['accepted'],ranges=t['ranges'],sink_stall_cycles=t['stalled'],
            driver_stream_cycles=c['stream_cycles'],nonstream_cycles=o['total']-c['stream_cycles'],
            reference_nonstream_cycles=bo['total']-c['stream_cycles'],
            combined_delta=s['total']-b['total']+o['total']-bo['total']))
    # Two explicit accounting policies. In transfer-covered, old parser/DMA
    # allocations must cover the accepted-byte phase; that integration is NOT
    # proved. In serialized-stress, the entire artificial driver is added as
    # an extra reservation, intentionally double-charging transfer/service.
    schedules=[]
    for r in old['rows']:
        f=r['frame'];di=(src[f]['total']-oldsrc[f]['total'])/22000
        for policy in ('transfer_covered_conditional','serialized_stress_reservation'):
            newout=out[f]['total']-(costs[f]['stream_cycles'] if policy=='transfer_covered_conditional' else 0)
            total=r['total_ms']+di+(newout-oldout[f]['total'])/22000
            schedules.append(dict(frame=f,setup=r['setup'],retained_policy=r['retained_policy'],
                accounting_policy=policy,old254_ms=r['total_ms'],input_delta_ms=di,
                output_replacement_cycles=newout,total_ms=total,residual_ms=1000/60-total))
    summaries=[]
    for policy in ('transfer_covered_conditional','serialized_stress_reservation'):
        for setup in (500,1000):
            for retained in ('command_tail','only_bitmap_removed'):
                rr=[r for r in schedules if r['accounting_policy']==policy and r['setup']==setup and r['retained_policy']==retained]
                worst=max(rr,key=lambda r:r['total_ms'])
                summaries.append(dict(accounting_policy=policy,setup=setup,retained_policy=retained,
                    max_ms=worst['total_ms'],min_residual_ms=worst['residual_ms'],worst_frame=worst['frame'],
                    over=[r['frame'] for r in rr if r['residual_ms']<0]))
    def report(path):
        s=pin(path).read_text();hier={}
        for line in s.splitlines():
            if not line.startswith(';'):continue
            c=[v.strip() for v in line.split(';')]
            if len(c)>4 and c[1].startswith('|nes_') and re.fullmatch(r'\d+ \(\d+\)',c[2]):
                hier[c[1]]=dict(comb=int(c[2].split()[0]),own_comb=int(re.search(r'\((\d+)\)',c[2])[1]),
                    FF=int(c[3].split()[0]),own_FF=int(re.search(r'\((\d+)\)',c[3])[1]))
        return dict(hierarchy=hier,fsm=sorted(set(re.findall(r'State Machine - (\|[^\s;]+)',s))))
    before=area(rm['summary']);after=area(mapped['summary'])
    assert before['bits']==after['bits']==49152
    assert len(mapped['ram_rows'])==4 and any('True Dual Port' in r and '1024' in r for r in mapped['ram_rows'])
    warm=detail[2:];fields=['source_cycles','source_delta','prepare','prepare_delta','output_cycles','output_delta','nonstream_cycles','combined_delta','accepted_bytes','ranges']
    by_kind={}
    for c in [int(v,16) for v in (a.test/'commands.hex').read_text().split()]:
        if c>>60!=2:continue
        first=(c>>12)&4095;count=c&4095;mode=(c>>32)&1
        kind='map' if mode else 'BG' if first<1024 else 'OBJ' if first<1152 else 'CGRAM' if first<1184 else 'rawCHR'
        item=by_kind.setdefault(kind,dict(ranges=0,bytes=0));item['ranges']+=1;item['bytes']+=count*(2 if mode else 32 if kind=='OBJ' else 16)
    assert sum(v['bytes'] for v in by_kind.values())==sum(r['accepted_bytes'] for r in detail)
    result=dict(passed=True,stage=255,scope=__doc__,
        test={k:v for k,v in test.items() if k!='input_hashes'},reference={k:v for k,v in ref.items() if k!='input_hashes'},
        incremental={k:v for k,v in inc.items() if k!='input_hashes'},consumer_guards={k:v for k,v in extra.items() if k!='input_hashes'},area_reference=before,area_joint=after,
        area_old254_without_adapter=old['area_joint'],delta={k:after[k]-before[k] for k in before},
        joint_report=report(a.map/'output_files/joint.map.rpt'),reference_report=report(a.reference_map/'output_files/joint.map.rpt'),
        warm_bounds={k:[min(r[k] for r in warm),max(r[k] for r in warm)] for k in fields},
        mean_source_delta_ms=sum(r['source_delta'] for r in warm)/len(warm)/22000,
        source_faster=sum(r['source_delta']<0 for r in warm),source_slower=sum(r['source_delta']>0 for r in warm),
        final_source_wire_delta_bytes=src[975]['wirebytes_cumulative']-rsrc[975]['wirebytes_cumulative'],
        accepted_by_kind=by_kind,accepted_bytes=sum(r['accepted_bytes'] for r in detail),ranges=sum(r['ranges'] for r in detail),
        sink_stall_cycles=sum(r['sink_stall_cycles'] for r in detail),frames_detail=detail,rows=schedules,summaries=summaries,
        input_hashes=pins,wholeboard_fit=False,sta=False,physical=False,full_ARM=False,new_SNES_execution=False,P2_selected=False,
        limitations=[
            'Same-clock descriptor/byte accepted sink; modeled destination memory. Actual SPI output packet parser, queue arbitration/retirement, physical SNES consumer and display ACK remain unbound.',
            'Sink bank selection is supplied by the frame harness; consumer bank/token ownership is not a new implemented interface.',
            'Range adapter covers BG/OBJ/map/CGRAM/rawCHR; tail CRC, fresh scroll, OAM and H2 context transport are not connected to this sink. Tail/scroll are actual C byte fixtures.',
            'Reference and joint reject oversized descriptors with different local codes (9 versus2); both cancel and prevent sealing.',
            'Area delta is joint query/receipt/adapter effect, not individual attribution and not a subtraction from whole240 deficit490LE40LAB.',
            'Transfer-covered schedule requires existing parser/DMA allocations to cover stream service. Serial stress reservation adds all fixture timing again. Neither is a measured whole-path bound.',
            'ARM32000cycles,32 certificate bytes,parser8cycles/byte and conditional SNES validate181 removal remain allocations, not measurements.',
            'Source SPI timing includes actual status polling; MCU service/capture readiness/final display lease overlap remain fixture assumptions.',
            'All71 recorded frames have raw2; no new integrated raw0 transition. Earlier250 coverage preserved.',
            'CRC16 is neither authentication nor collision-free equivalence.'])
    def dump(path,o):path.write_text(json.dumps(o,indent=2)+'\n',encoding='utf-8',newline='\n')
    dump(d/'result.json',result)
    summary={k:v for k,v in result.items() if k not in ('input_hashes','rows','frames_detail')}
    summary.update(input_count=len(pins),private_result_sha256=sha(d/'result.json'));dump(d/'summary.json',summary)
    for n,rr in [('frames.csv',detail),('schedules.csv',schedules)]:
        with (d/n).open('w',newline='') as f:
            w=csv.DictWriter(f,fieldnames=list(rr[0]),lineterminator='\n');w.writeheader();w.writerows(rr)
    shutil.copyfile(__file__,d/'analyzer.py')
    print(json.dumps({k:result[k] for k in ('area_reference','area_joint','delta','warm_bounds','accepted_bytes','ranges','summaries')},indent=2))


if __name__=='__main__':main()
