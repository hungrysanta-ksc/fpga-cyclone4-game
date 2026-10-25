# SPDX-License-Identifier: MIT
"""Protocol/ownership budget model; not new ARM/RTL execution or synthesis."""
import json,binascii,math
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from probe_nes_decode280 import golden,encode280,chunks

# Canonical storage remains unchanged. Region order is a NEW proposed ABI.
# OBJ follows BG geometry; all ROM/plan publication still waits for full commit.
REGIONS=[('map',0,2112,2),('row',2112,224,1),('exception',3360,512,1),
 ('raster',3872,448,2),('mask',4320,1,1),('palette',4321,64,1),
 ('counts',4385,13,1),('object',2336,1024,1),('raw',4398,512,1)]


def encode_region(rid,old,new,cold):
    name,start,size,width=REGIONS[rid];assert len(new)==size
    n=size//width;v=[new[i*width:(i+1)*width] for i in range(n)]
    u=[old[i*width:(i+1)*width] for i in range(n)]
    cost=[0]*(n+1);choice=[None]*n
    for i in range(n-1,-1,-1):
        best=(10**9,None)
        if not cold and v[i]==u[i]:best=(cost[i+1],(i+1,None))
        same=True
        for j in range(i+1,min(n,i+min(64,239//width))+1):
            same=same and v[j-1]==v[i]
            for mode,payload in [(0,b''.join(v[i:j]))]+([(1,v[i])] if same else []):
                b=bytes([rid])+i.to_bytes(2,'little')+bytes([(mode<<6)|(j-i-1)])+payload
                c=len(b)+cost[j]
                if c<best[0]:best=(c,(j,b))
        if not cold and name=='map' and i%33==0 and i+33<=n:
            for mode,ok,payload in [(2,v[i:i+32]==u[i+1:i+33],v[i+32]),(3,v[i+1:i+33]==u[i:i+32],v[i])]:
                if ok:
                    b=bytes([rid])+i.to_bytes(2,'little')+bytes([(mode<<6)|32])+payload
                    if len(b)+cost[i+33]<best[0]:best=(len(b)+cost[i+33],(i+33,b))
        cost[i],choice[i]=best
    out=[];i=0
    while i<n:
        j,b=choice[i]
        if b is not None:out.append(b)
        i=j
    return out


def decode(old,rr,cold):
    out=bytearray(old);last=[0]*len(REGIONS);seen=-1
    for b in rr:
        assert len(b)>=4
        rid=b[0];assert rid<len(REGIONS) and rid>=seen;seen=rid
        name,start,size,width=REGIONS[rid];at=int.from_bytes(b[1:3],'little');count=(b[3]&63)+1;mode=b[3]>>6
        assert at>=last[rid] and at+count<=size//width
        if cold:assert at==last[rid]
        pos=start+at*width;end=pos+count*width;p=b[4:]
        if mode==0:assert len(p)==count*width;out[pos:end]=p
        elif mode==1:assert len(p)==width;out[pos:end]=p*count
        else:
            assert not cold and name=='map' and at%33==0 and count==33 and len(p)==2
            out[pos:end]=(old[pos+2:end]+p) if mode==2 else (p+old[pos:end-2])
        last[rid]=at+count
    if cold:assert last==[size//width for _,_,size,width in REGIONS]
    return bytes(out)


def greedy_region(rid,old,new,cold):
    name,start,size,width=REGIONS[rid];n=size//width
    v=[new[i*width:(i+1)*width] for i in range(n)];u=[old[i*width:(i+1)*width] for i in range(n)]
    result=[];i=0
    while i<n:
        if not cold and v[i]==u[i]:i+=1;continue
        mode=0;j=i+1;payload=v[i]
        if not cold and name=='map' and i%33==0 and i+33<=n and v[i:i+32]==u[i+1:i+33]:mode=2;j=i+33;payload=v[i+32]
        elif not cold and name=='map' and i%33==0 and i+33<=n and v[i+1:i+33]==u[i:i+32]:mode=3;j=i+33;payload=v[i]
        else:
            while j<min(n,i+64) and v[j]==v[i]:j+=1
            if j-i>=2:mode=1
            else:
                while j<min(n,i+min(64,239//width)):
                    if (not cold and v[j]==u[j]) or (j+1<n and v[j]==v[j+1]):break
                    j+=1
                payload=b''.join(v[i:j])
        result.append(bytes([rid])+i.to_bytes(2,'little')+bytes([(mode<<6)|(j-i-1)])+payload);i=j
    return result


def model_packets(rr):
    # Same H20/GEO10/END6 overhead, but NEW region transcript CRC/phase meaning.
    # Object is moved after GEO; the old C receiver would correctly reject it.
    before=[b for b in rr if b[0]<7];after=[b for b in rr if b[0]>=7]
    ordered=[bytes(20),*before,bytes(10),*after,bytes(6)]
    return ordered,chunks(ordered),20+sum(map(len,before))+10


def main():
    pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    baseline=json.loads(read(ROOT/'analysis/ingress338-verification.json'))
    assert baseline['passed']
    for p,h in baseline['pins'].items():assert sha(Path(p))==h
    for name in ('docs/nes-execute321-contract.ko.md','docs/nes-units323-contract.ko.md','docs/nes-ingress338-contract.ko.md'):read(ROOT/name)
    read(BASE/'probes/nes-ingress338/board01/output_files/board.map.summary')
    old=bytes(4910);rows=[];negatives=0
    for f in range(905,976):
        geom,raw=golden(f);new=geom+raw;assert len(new)==4910
        for suffix in ('expected','records'):read(BASE/f'probes/nes-joint278/test07/frame{f}.{suffix}')
        reference=encode280(old[:4398],geom,raw,None if f==905 else old[4398:],f-904,f-904)
        rr=[];region_bytes={};greedy=[]
        for rid,(name,at,size,width) in enumerate(REGIONS):
            part=encode_region(rid,old[at:at+size],new[at:at+size],f==905);rr+=part;region_bytes[name]=sum(map(len,part))
            greedy+=greedy_region(rid,old[at:at+size],new[at:at+size],f==905)
        assert decode(old,rr,f==905)==new
        assert decode(old,greedy,f==905)==new
        # Negative model checks retain sorted region/offset bounds and cold coverage.
        if rr:
            bad=[bytes([255])+rr[0][1:]]
            for invalid in (bad,[rr[0],rr[0]], [rr[0][:1]+b'\xff\xff'+rr[0][3:]]):
                try:decode(old,invalid,False)
                except AssertionError:negatives+=1
                else:raise AssertionError('invalid model accepted')
        ordered,packed,geo=model_packets(rr);original=chunks(reference)
        go,gp,gg=model_packets(greedy)
        maps=[b for b in reference[1:] if b[:3]!=b'\xff\xff\x00' and (b[0]&127)<32]
        rebuilt=bytearray(old[:2112])
        for b in maps:
            at=(b[0]&127)*66
            if b[0]&128:
                assert b[1] in (1,255)
                rebuilt[at:at+66]=old[at+2:at+66]+b[2:] if b[1]==1 else b[2:]+old[at:at+64]
            else:
                k=10
                for bit in range(66):
                    if b[1+bit//8]&(1<<(bit%8)):rebuilt[at+bit]=b[k];k+=1
                assert k==len(b)
        assert bytes(rebuilt)==new[:2112]
        # Disjoint tags: map MASK0..31/SHIFT128..159; region65..72.
        tagged=lambda b:bytes([0x40|b[0]])+b[1:]
        hybrid=[bytes(20),*maps,*[tagged(b) for b in greedy if 0<b[0]<7],bytes(10),*[tagged(b) for b in greedy if b[0]>=7],bytes(6)]
        hp=chunks(hybrid)
        pay=sum(map(len,ordered));oldpay=sum(map(len,original))
        def wire(n,b):return n+15*b+8
        # Earliest D5 ACK, same framing/gaps. No producer/ARM/IRQ cost included.
        def floor(n,b):return wire(n,b)*8/2625000*1000+.008*(b+1)-.004190476190476
        rows.append(dict(frame=f,reference_payload=oldpay,reference_blocks=len(original),candidate_payload=pay,candidate_blocks=len(packed),candidate_region_bytes=region_bytes,
            reference_wire=wire(oldpay,len(original)),candidate_wire=wire(pay,len(packed)),candidate_record_count=len(rr),
            reference_commit_floor_ms=floor(oldpay,len(original)),candidate_commit_floor_ms=floor(pay,len(packed)),geometry_prefix_payload=geo,
            greedy_payload=sum(map(len,go)),greedy_blocks=len(gp),greedy_wire=wire(sum(map(len,go)),len(gp)),greedy_commit_floor_ms=floor(sum(map(len,go)),len(gp)),greedy_geometry_prefix=gg,
            hybrid_payload=sum(map(len,hybrid)),hybrid_blocks=len(hp),hybrid_wire=wire(sum(map(len,hybrid)),len(hp)),hybrid_commit_floor_ms=floor(sum(map(len,hybrid)),len(hp)),
            payload_crc16=binascii.crc_hqx(new,65535),reconstruction_exact=True))
        old=new
    root=BASE/'probes/nes-ingress338/window03'
    for name in ('nes_core257.sv','nes_mux260.sv','nes_validator278.sv','nes_queue260.sv','nes_transport257.sv','nes_planner211.c','nes_input286.inc','nes_planner285.c','order247.h','nes_decode280.c'):read(root/name)
    constraints={}
    warm=rows[2]
    arm=json.loads(read(root/'arm907.json'))
    first_plan=next(bytes.fromhex(t['tx']) for t in arm['transfers'] if t['tx'].startswith('e9'))
    assert len(first_plan)==46 and first_plan[3]==6 and first_plan[4]==130 and first_plan[7]==128
    split=dict(old_first_wire=46,prefix_wire=18,remainder_wire=36,first_wire_advance_us=28*8/2625000*1e6,
        whole_added_wire=8,whole_added_SPI_us=8*8/2625000*1e6+8,
        prerequisite='clear + one immutable BG plan; future lower slots/duplicates must be proven safe. Existing partial-BG marker stays. No measured early-ready time.')
    for tag in ('fixed01','window03','normal01'):
        row=baseline['runs'][tag]['rows'][-1];b=baseline['runs'][tag]['source_BG_schedule'][-1]
        available=b['available_before_previous_close_ms']
        constraints[tag]=dict(baseline_total_ms=row['total_ms'],baseline_gap_ms=row['total_ms']-1000/60,
            baseline_ROM_wait_ms=row['first_accept_ms']-row['first_request_ms'],post_ROM_ms=row['post_ROM_ms'],
            post_ROM_floor_gap_ms=row['post_ROM_ms']-3.18,previous_close_applies=tag!='normal01',previous_close_available_ms=available,
            model_commit_floor_ms=warm['greedy_commit_floor_ms'],first_E9_wire_ms=b['first_E9_wire_ms'],
            zero_compute_before_previous_close_budget_ms=available-warm['greedy_commit_floor_ms']-b['first_E9_wire_ms'],
            required_whole_gain_ms=max(0,row['total_ms']-1000/60))
        c=constraints[tag]
        c.update(early_prefix_wire_ms=.008+18*8/2625000*1000,
            early_prefix_nonwire_budget_ms=available-warm['hybrid_commit_floor_ms']-(.008+18*8/2625000*1000),
            required_preROM_advance_with_3p180_tail_ms=max(0,row['total_ms']-row['post_ROM_ms']-(1000/60-3.18)))
    # Auditable whole cost envelope: NOT predicted component savings.
    current=dict(host=2161,validator_aperture=1159,queue_SPI=798,source=1747,plan=459)
    cap=dict(host=1146,validator_aperture=1160,queue_SPI=600,source=1100,plan=297)
    assert sum(current.values())==6324 and sum(cap.values())==4303
    read(ROOT/'tools/analyze_nes_structure339.py')
    aggregates={k:dict(total_wire=sum(x[k+'_wire'] for x in rows),regressions=[dict(frame=x['frame'],delta=x[k+'_wire']-x['reference_wire']) for x in rows if x[k+'_wire']>x['reference_wire']]) for k in ('candidate','greedy','hybrid')}
    assert not aggregates['hybrid']['regressions']
    out=dict(stage=339,passed=True,selected_RTL=338,selected_ARM=336,new_RTL=False,new_MAP=False,new_measured_gain_ms=0,new_candidate_comb=None,
        model='Compare offline DP, bounded all-region greedy, and bounded hybrid retaining existing map MASK/SHIFT. Nonmap 4B disjoint-tag record; max243B record/248B bank. H20/BG-seal10/END6 charged placeholders, not new CRC/ABI execution. No FPGA/ARM performance or area claim.',
        rows=rows,negative_model_cases=negatives,constraints=constraints,aggregates=aggregates,reference_total_wire=sum(x['reference_wire'] for x in rows),regions=REGIONS,first_BG_split=split,
        nonwire_design_caps_ms=dict(source_query_compare_seal=.45,ARM_decode=.10,ARM_BG_prepare=.36,ARM_first_plan_refill=.18,IRQ_CDC_poll=.11),
        word_scan=dict(old_scan_bytes=4910,new_padded_bytes=4912,allocated_base_bytes=5120,data_bits=40960,
            old_two_cycle_scan_floor_ms=4910*2/22e3,new_two_cycle_word_scan_floor_ms=2456*2/22e3,
            scope='Arithmetic source scan floors only. Query, compare/run selection, serial emission and stalls excluded. M9K packing and new datapath area unmeasured.'),
        whole_baseline=baseline['whole'],comb_deficit=1866,
        area_current=current,area_caps=cap,scope_reduction_required=2021,outside_comb=10950,whole_cap=15253,margin=155,
        safety='Full input commit before E9/ROM; speculative BG preparation only. Independent expected/actual-read CRC/coverage and STOP/finalACK/VBlank retained; new ABI guards not executed in RTL.',pins=pins)
    (ROOT/'analysis/structure339-verification.json').write_text(json.dumps(out,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,frames=len(rows),negative_model_cases=negatives,warm=warm,cold=rows[0],constraints=constraints,pins=len(pins)),indent=2))


if __name__=='__main__':main()
