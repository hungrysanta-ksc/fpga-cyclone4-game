# SPDX-License-Identifier: MIT
"""305 evidence-backed replacement budget and wire model, NOT a retimed RTL run."""
import csv,json
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha

def encode(data):
    out=bytearray();i=0
    while i<len(data):
        zero=data[i]==0;j=i+1
        while j<len(data) and (data[j]==0)==zero and j-i<128:j+=1
        out.append((128 if zero else 0)+(j-i-1))
        if not zero:out.extend(data[i:j])
        i=j
    return bytes(out)

def decode(data,size):
    out=bytearray();i=0
    while i<len(data):
        tag=data[i];i+=1;n=(tag&127)+1
        if len(out)+n>size:raise ValueError('expanded overflow')
        if tag&128:out.extend(bytes(n))
        else:
            if i+n>len(data):raise ValueError('truncated literal')
            out.extend(data[i:i+n]);i+=n
    if len(out)!=size:raise ValueError('expanded underflow')
    return bytes(out)

def packets(blob):
    at=0
    while at<len(blob):
        assert at+2<=len(blob)
        n=int.from_bytes(blob[at:at+2],'little');at+=2
        assert 16<=n<=256 and at+n<=len(blob)
        yield blob[at:at+n];at+=n
    assert at==len(blob)

def main():
    pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    old=js(ROOT/'analysis/record305-verification.json')
    for p,h in old['input_hashes'].items():assert sha(Path(p))==h,(p,'changed305')
    d=BASE/'probes/nes-record305';rows=[]
    for f in range(905,976):
        ps=list(packets(pin(d/'native01'/f'frame{f}.packets').read_bytes()))
        # Native producer emits the 206B terminal op3. ARM serializer splits
        # it into early op15 requirements and the 16B final op3 fence.
        m=[p for p in ps if p[0]==3];assert len(m)==1 and len(m[0])==206
        req=m[0][40:];assert len(req)==166
        rle=encode(req);assert decode(rle,166)==req
        # Keep all 24 display bytes, all 16 header bytes and E1+CRC16.
        # One explicit codec byte; raw fallback must be charged too.
        new=1+16+24+1+min(166,len(rle))+2
        rows.append(dict(frame=f,requirements_raw=166,requirements_RLE=len(rle),old_SPI=209,new_SPI=new,saved_SPI=209-new,codec='RLE' if len(rle)<166 else 'raw'))
    tests=0
    for n in (1,127,128,129,166,256):
        for b in (bytes(n),bytes([255])*n,bytes(i%2 for i in range(n))):
            assert decode(encode(b),n)==b;tests+=1
    negatives=0
    for b,n in [(b'',166),(b'\xff\xff',166),(b'\x02\x01',3),(b'\x80\x80',1),(b'\x00\x01',2)]:
        try:decode(b,n)
        except ValueError:negatives+=1
        else:raise AssertionError('bad stream accepted')
    ev=list(csv.reader(pin(d/'window02/joint-events.csv').open()))
    es=[e for e in ev if e[1]=='907'];arm=js(d/'window02/arm907.json')
    tx=[(bytes.fromhex(t['tx']),t) for t in arm['transfers'] if t['tx']]
    manifest=next(t for b,t in tx if b[:2]==b'\xe1\x0f')
    native907=list(packets((d/'native01/frame907.packets').read_bytes()))[-1]
    assert bytes.fromhex(manifest['tx'])[17:-2]==native907[16:]
    wire_bindings=0
    for tag in ('test03','window02'):
        for f in (905,906,907):
            live=js(d/tag/f'arm{f}.json')
            native=list(packets((d/'native01'/f'frame{f}.packets').read_bytes()))[-1]
            wire=[bytes.fromhex(t['tx']) for t in live['transfers'] if t['tx'].startswith('e10f')]
            assert len(wire)==1 and wire[0][17:-2]==native[16:]
            wire_bindings+=1
    end=manifest['RTL_ns']/1e6
    idx=arm['transfers'].index(manifest);before=arm['transfers'][idx-1]['RTL_ns']/1e6
    assert abs(end-280.889583)<1e-8 and abs(before-280.097084)<1e-8
    bg=next(e for e in es if e[0]=='romplan305' and e[2]=='0');cycle=int(bg[3]);period=357368
    prior_end=(cycle//period-1)*period+354640-1
    prior_slot=prior_end-((prior_end-3)%12)
    assert prior_slot<cycle and prior_slot%12==3 and 330088<=prior_slot%period<354640
    warm=next(x for x in old['restricted'] if x['frame']==907)
    mr=next(x for x in rows if x['frame']==907)
    # SPI clock is actual retained testbench 190.476190476ns per half bit.
    tb=pin(d/'window02/joint266_tb.sv').read_text()
    assert '#190.476190476' in tb
    byte_ms=16*190.476190476/1e6
    wire_gain=mr['saved_SPI']*byte_ms
    need=warm['total_ms']-1000/60
    # These are deliberately separate sensitivities, never added as savings.
    manifest_interval=end-before
    last_dma_tx=279.213503
    assert any(e[0]=='arm267' and e[2:4]==['225','67'] and int(e[4])==279213503000 for e in es)
    cpu_services=sum(int(e[3]) for e in es if e[0]=='cpu267')/1e9
    caps=dict(shared_ingress_queue_SPI=425,plan_decode_CDC=300,execution_and_receipt=750,independent_validation=886,glue=48)
    assert sum(caps.values())==2409
    region=old['regions'];assert sum(region.values())==4746
    assert region['queue']+region['SPI']+region['plan']==1361
    result=dict(passed=True,stage=306,scope='Architecture, existing-trace analysis and bounded codec model only',
        new_RTL=False,new_ARM=False,new_MAP=False,new_retimed_schedule=False,FIT=False,STA=False,physical=False,
        measured305_MAP=old['whole_MAP'],measured_regions=region,measured_schedules={k:old[k] for k in ('normal','restricted')},
        boundary=4746,outside=12871,hard_cap=2537,functional_cap=2409,reserve=128,required_gain_comb=2209,
        required_gain_with_reserve_comb=2337,required_caps_not_predictions=caps,
        ingress_zero_still_short_comb=2209-1361,host_validator_allowed_if_ingress_unchanged=2537-1361-48,
        ROM=dict(first_BG_plan_cycle=cycle,phase=cycle%period,previous_last_fine_slot=prior_slot,
                 minimum_advance_to_previous_last_slot_ms=(cycle-prior_slot)*45.454/1e6,
                 previous_slot_is_not_full_batch_deadline=True,window_policy_unchanged=True),
        wire_model=rows,codec_positive_vectors=tests+71,codec_negative_vectors=negatives,actual_wire_bindings=wire_bindings,
        warm907=dict(measured_ms=warm['total_ms'],required_gain_ms=need,required_with_margin_ms=need+.25,
             manifest_SPI_old=209,manifest_SPI_new=mr['new_SPI'],wire_only_sensitivity_ms=wire_gain,
             wire_only_remaining_ms=need-wire_gain,manifest_issue_interval_ms=manifest_interval,
             full_manifest_interval_free_remaining_ms=need-manifest_interval,
             last_DMA_enqueue_ms=last_dma_tx,manifest_previous_return_ms=before,
             earlier_issue_window_ms=before-last_dma_tx,late_CPU_service_occupancy_ms=cpu_services,
             compression_plus_early_issue_gain_ms=None,retimed_ms=None),
        candidate_MAP=None,candidate_selected=False,input_hashes=pins,verified_prior_input_hashes=len(old['input_hashes']),script_sha256=sha(Path(__file__)))
    (ROOT/'analysis/ingress306-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    with (ROOT/'analysis/ingress306-wire.csv').open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=list(rows[0]),lineterminator='\n');w.writeheader();w.writerows(rows)
    print(json.dumps({k:result[k] for k in ('warm907','ROM','codec_positive_vectors','codec_negative_vectors')},indent=2))

if __name__=='__main__':main()
