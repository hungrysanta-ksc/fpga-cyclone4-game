# SPDX-License-Identifier: MIT
"""Reconcile source/plan ownership budgets and measured ROM phase effects.

Reuses hash-bound 315 MAP and 317 actual-M4/RTL traces. No new simulation,
counterfactual schedule, synthesis saving, or physical performance claim.
"""
import csv,json,re
from nes_delta231 import BASE,ROOT,sha

def main():
    pins={}
    def read(p):
        pins[str(p)]=sha(p)
        return p.read_text(encoding='utf-8-sig')
    old=json.loads(read(ROOT/'analysis/response315-verification.json'))
    measured=json.loads(read(ROOT/'analysis/metadata317-verification.json'))
    assert old['passed'] and measured['passed']
    board=BASE/'probes/nes-response315/board01'
    report=read(board/'output_files/board.map.rpt')
    section=report.split('; Analysis & Synthesis Resource Utilization by Entity')[1]
    entities={}
    for line in section.splitlines():
        c=[x.strip() for x in line.split(';')]
        if len(c)<13 or not c[1].startswith('|'):continue
        m=re.fullmatch(r'(\d+) \((\d+)\)',c[2]);n=re.fullmatch(r'(\d+) \((\d+)\)',c[3])
        if not m or not n:continue
        entities[c[10]]=dict(entity=c[11],comb=int(m[1]),own_comb=int(m[2]),FF=int(n[1]),own_FF=int(n[2]),RAM_bits=int(c[4]))
    # Every own value, including primitives, counts once; never sum parent totals.
    assert sum(x['own_comb'] for x in entities.values())==17870
    def node(suffix):
        matches=[v for k,v in entities.items() if k.endswith(suffix)]
        assert len(matches)==1,(suffix,len(matches))
        return matches[0]
    selected={s:node(s) for s in ('nes_output260:flow','nes_validator278:validator','nes_queue260:queue',
        'nes_spi270:spi_front270','nes_core257:encoder','nes_transport257:transport',
        'nes_plan_path267:retained_plan267','nes_plan_batch206:transport','nes_plan_spi200:endpoint',
        'nes_source_tile192:source')}
    narrow=sum(selected[s]['own_comb'] for s in list(selected)[:4]);assert narrow==4474
    source=selected['nes_core257:encoder']['comb']+selected['nes_transport257:transport']['comb']
    plan=selected['nes_plan_path267:retained_plan267']['comb']-selected['nes_source_tile192:source']['comb']
    assert (source,plan)==(1778,465)
    regions={}
    for name,size in [('host_validator_queue_SPI',narrow),('plus_source_transport_plan_control',narrow+433+plan),('plus_source_encoder',narrow+source+plan)]:
        regions[name]=dict(current_comb=size,fixed_outside=17870-size,required_net_saving=2462,
            maximum_replacement_comb=size-2462,with_128_margin=size-2462-128,required_fraction=2462/size,
            predicted_saving=None)
    for n in ('nes_joint257.sv','nes_core257.sv','nes_transport257.sv','nes_plan_batch206.sv',
              'nes_plan_spi200.sv','nes_queue260.sv','nes_validator278.sv','nes_chr_cache192.sv','nes_native_arbiter165.sv'):
        read(board/n)
    rows=[]
    for tag in ('observe02','arm01'):
        d=BASE/'probes/nes-metadata317'/tag
        result=json.loads(read(d/'result.json'));assert result['passed']
        for name,h in result['rtl_hashes'].items():assert sha(d/name)==h
        assert sha(d/'output.elf')==result['ELF_sha256']
        for name in ('nes_core257.sv','nes_transport257.sv','nes_plan_batch206.sv','nes_plan_spi200.sv','nes_queue260.sv','nes_validator278.sv'):
            assert read(d/name).split()==read(board/name).split(),(tag,name)
        tb=read(d/'joint266_tb.sv')
        assert 'romcycle267%357368>=330088&&romcycle267%357368<354640&&romcycle267%12==3' in tb
        assert 'back_request=request&&ready&&!hit' in read(d/'nes_chr_cache192.sv')
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        for r in measured['runs'][tag]['rows']:
            f=r['frame'];e=[x for x in ev if len(x)>1 and x[1]==str(f)]
            req=next(x for x in e if x[:3]==['firstreq305',str(f),'0'])
            grant=next(x for x in e if x[:3]==['firstmiss305',str(f),'0'])
            tile=next(x for x in e if x[:3]==['romtile305',str(f),'0'])
            ti=ev.index(tile);previous=next((x for x in reversed(ev[:ti]) if x[0]=='romtile305'),None)
            counter_delta=None if previous is None else [int(tile[i])-int(previous[i]) for i in range(5,9)]
            rows.append(dict(tag=tag,frame=f,total_ms=r['total_ms'],gap_ms=r['gap_ms'],start_ms=r['start_ms'],
                request_ms=int(req[-1])/1e9,accepted_miss_ms=int(grant[-1])/1e9,first_BG_ms=r['BG_ms'],
                request_to_accept_ms=(int(grant[-1])-int(req[-1]))/1e9,
                accept_to_first_BG_ms=(int(tile[-1])-int(grant[-1]))/1e9,
                request_phase=int(req[3])%357368,accept_phase=int(grant[3])%357368,
                counter_delta_since_previous_tile=counter_delta,counter_interval_start_ms=None if previous is None else int(previous[-1])/1e9,
                tail_ms=r['tail_ms'],finish_ms=r['finish_ms'],SPI_bytes=r['SPI_bytes'],ARM_instructions=r['ARM_instructions'],
                requirements_tx_end_ms=r['requirements_tx_end_ms'],max_credit=r['max_credit']))
    b=next(x for x in rows if x['tag']=='observe02' and x['frame']==907)
    a=next(x for x in rows if x['tag']=='arm01' and x['frame']==907)
    delta={k:a[k]-b[k] for k in ('start_ms','request_ms','accepted_miss_ms','first_BG_ms','request_to_accept_ms','tail_ms','finish_ms','total_ms')}
    assert abs(delta['total_ms']-(delta['finish_ms']-delta['start_ms']))<1e-9
    assert delta['accepted_miss_ms']==delta['first_BG_ms']==0
    for prior in (old,measured):
        for p,h in prior['input_hashes'].items():
            if p in pins:assert pins[p]==h,p
    out=dict(stage=318,passed=True,kind='ownership_and_phase_review',new_RTL=False,new_ARM=False,new_MAP=False,
        baseline='315 RTL + 317 arm01 metadata early issue',whole_MAP=old['whole_MAP'],comb_deficit=2462,
        remaining_ms=a['gap_ms'],resources=selected,regions=regions,timing=rows,restricted907_delta=delta,
        limitations=['New architecture budgets are targets, not predicted synthesis savings.',
          'Actual M4 instruction execution at modeled CPI1/84MHz, IRQ and two-slot costs included; not hardware cycle measurement.',
          'firstmiss305 is accepted cache backend request, not initial miss detection.',
          'Counters are cumulative; reported deltas cover previous tile event to first BG, not exact frame or request interval.',
          'ROM window uses fixed testbench phase, not live full NES RUN. No same-start paired run or phase sweep yet.',
          '315 RTL + early ARM unrestricted-ROM schedule is not separately measured; 317 normal01 uses rejected joint RTL.',
          'Tile/map/VBlank retain modeled service; no full live 65816/71-frame/FIT/STA/physical60fps.'],input_hashes=pins)
    read(ROOT/'tools/analyze_nes_ownership318.py')
    (ROOT/'analysis/ownership318-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(regions=regions,delta=delta,baseline907=a),indent=2))

if __name__=='__main__':main()
