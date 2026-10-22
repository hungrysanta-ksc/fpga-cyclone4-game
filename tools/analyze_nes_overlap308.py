# SPDX-License-Identifier: MIT
"""307 trace audit and replacement budgets; no invented retiming or MAP."""
import csv,json
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha

def main():
    pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    prior=js(ROOT/'analysis/ingress307-verification.json')
    for p,h in prior['input_hashes'].items():assert sha(Path(p))==h,(p,'changed307')
    d=BASE/'probes/nes-ingress307/window03'
    events=list(csv.reader(pin(d/'joint-events.csv').open()))
    es=[e for e in events if e[1]=='907']
    plan=next(e for e in es if e[:3]==['romplan305','907','0'])
    miss=next(e for e in es if e[:3]==['firstmiss305','907','0'])
    a,b=int(plan[-1])/1e9,int(miss[-1])/1e9
    tx=js(d/'arm907.json')['transfers'];rows=[]
    for x in tx:
        raw=bytes.fromhex(x['tx'])
        if not raw or raw[0]!=0xe1:continue
        rows.append(dict(op=raw[1],section=raw[2],SPI_bytes=len(raw),end_ms=x['RTL_ns']/1e6,
                         preceding_instructions=x['instructions'],IRQ_instructions=x['IRQ_instructions']))
    meta=[x for x in rows if x['op'] in (15,10,11)]
    broader=[x for x in rows if x['op'] not in (13,1,7,3)]
    assert [x['op'] for x in meta]==[15,11]
    # Bounds on explicitly observed late transfers only, NOT CPU function cost.
    # The event accounts instructions since the preceding callback, including
    # work unrelated to encoding; they are not all movable into the wait.
    cpu=sum(x['preceding_instructions'] for x in meta)/84000
    wire=sum(x['SPI_bytes'] for x in meta)*8/2625
    last=next(x for x in reversed(rows) if x['op'] not in (15,10,11,3))
    finish=prior['restricted'][-1]['absolute_finish_ms']
    gap=prior['restricted'][-1]['total_ms']-1000/60
    # Conservative allocated live ranges, including unused portions of the
    # persistent validity domains. They are not offered for new storage.
    ranges=[(0,166),(256,422),(448,512),(512,678),(680,716),(768,1024)]
    used=set()
    for lo,hi in ranges:
        region=set(range(lo,hi));assert not used&region;used|=region
    free=set(range(1024))-used
    assert len(free)==170
    host=pin(d/'nes_mux260.sv').read_text()
    assert 'manifest_phase!=0&&header[0]!=10&&header[0]!=11&&header[0]!=3' in host
    assert 'exec_busy298?exec_addr298:parser_address' in host
    native=pin(d/'nes_native289.c').read_text()
    assert '!r->prepared' in native and '!d->prepared' in native
    for n in ('nes_refill267.c','nes_planner211.c','nes_validator278.sv','nes_joint257.sv','nes_irq284.c','joint266_tb.sv'):pin(d/n)
    own=prior['regions'];assert sum(own.values())==4730
    budget={'admission_DMA_owner':700,'independent_validator_CRC_display':900,
            'queue_SPI_ingress_response':450,'plan_transport':328,'glue':49}
    assert sum(budget.values())==2427
    result=dict(stage=308,passed=True,kind='trace_dependency_and_budget_audit',new_ARM_run=False,new_RTL=False,new_MAP=False,
        baseline=307,baseline_whole_MAP=prior['whole_MAP'],baseline_regions=own,
        BG_wait=dict(plan_ms=a,grant_ms=b,span_ms=b-a,
            last_pregrant_SPI_ms=max(x['RTL_ns']/1e6 for x in tx if a<=x['RTL_ns']/1e6<b),
            readiness_time_measured=False),
        late_packets=rows,manifest_only=dict(SPI_bytes=sum(x['SPI_bytes'] for x in meta),
            preceding_instruction_ms_CPI1=cpu,wire_ms_2625kbit=wire,
            accounting_sum_ms=cpu+wire,remaining_if_sum_removed_ms=gap-cpu-wire,
            note='Fixed trace diagnostic, not a gain bound under rescheduling; no proof all preceding instructions are encoding'),
        broader_staging=dict(packets=len(broader),SPI_bytes=sum(x['SPI_bytes'] for x in broader),
            stored_packet_bytes=sum(x['SPI_bytes']-3 for x in broader),
            wire_ms_2625kbit=sum(x['SPI_bytes'] for x in broader)*8/2625,
            preceding_instruction_ms_CPI1=sum(x['preceding_instructions'] for x in broader)/84000,
            feasible_in_current_four_slot_queue=len(broader)<=4,
            note='All map/ordinary/manifest E1s, no tile/H2/BEGIN/SEAL. Preparation availability and consumption not moved.'),
        late_suffix=dict(last_nonmanifest_E1_end_ms=last['end_ms'],finish_ms=finish,
            span_ms=finish-last['end_ms'],gap_after_free_suffix_ms=gap-(finish-last['end_ms']),
            note='Includes outstanding DMA and ACK. Neither removable nor an achievable gain.'),
        phase_RAM=dict(live_ranges_half_open=ranges,free_bytes=len(free),expanded_manifest_bytes=446,
            expanded_deficit=446-len(free),source_scratch_not_free=True),
        area=dict(boundary=4730,outside=12853,capacity=15408,hard_cap=2555,function_cap=2427,reserve=128,
            deficit=2175,required_with_reserve=2303,host_zero_deficit=2175-own['host'],
            host_validator_only_cap=own['host']+own['validator']-2175,
            host_validator_only_reserve_cap=own['host']+own['validator']-2303,budget=budget),
        time=dict(required_ms=gap,required_with_margin_ms=gap+.25),
        candidate_time_ms=None,candidate_MAP=None,selected=False,input_hashes=pins)
    pin(Path(__file__))
    (ROOT/'analysis/overlap308-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:result[k] for k in ('BG_wait','manifest_only','broader_staging','late_suffix','phase_RAM','area','time')},indent=2))

if __name__=='__main__':main()
