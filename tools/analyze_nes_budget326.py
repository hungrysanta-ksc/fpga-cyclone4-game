# SPDX-License-Identifier: MIT
"""Audit existing325 traces; counterfactual budgets are not measured savings."""
import csv,json,re
from nes_delta231 import BASE,ROOT,sha

def main():
    pins={}
    def read(p):
        pins[str(p)]=sha(p)
        return p.read_text(encoding='utf-8-sig')
    ref=json.loads(read(ROOT/'analysis/expand325-verification.json'))
    assert ref['passed'] and ref['comb_deficit']==2394
    d=BASE/'probes/nes-expand325'
    rows=[]
    for run in ('fixed03','window02','normal02'):
        events=list(csv.reader(read(d/run/'joint-events.csv').splitlines()))
        read(d/run/'joint266_tb.sv')
        for old in ref['runs'][run]['rows']:
            f=old['frame'];e=[x for x in events if len(x)>1 and x[1]==str(f)]
            def at(name,kind=None,last=False):
                a=[x for x in e if x[0]==name and (kind is None or int(x[2])==kind)]
                return int(a[-1 if last else 0][-1])/1e9 if a else None
            final=old['finish_ms'];last=at('consume293',last=True)
            seal=at('release312',3);req=at('firstreq305',0);miss=at('firstmiss305',0)
            bg=at('romtile305',0)
            parser={str(op):sum(int(x[3])/1e9 for x in e if x[0]=='parser' and int(x[2])==op) for op in (15,11,3)}
            assert abs(bg-old['first_BG_ms'])<1e-9 and last<=seal<=final
            rows.append(dict(run=run,frame=f,start_ms=old['start_ms'],first_BG_request_ms=req,
                first_ready_gated_backend_request_ms=miss,first_BG_output_byte_ms=bg,
                request_to_backend_ms=miss-req,last_BG_output_tile_first_byte_ms=at('romtile305',0,True),
                last_OBJ_output_tile_first_byte_ms=at('romtile305',1,True),
                metadata_release_ms=old['metadata_release_ms'],last_consume_ms=last,seal_release_ms=seal,finish_ms=final,
                post_consume_envelope_ms=final-last,consume_to_seal_ms=seal-last,seal_to_finish_ms=final-seal,
                parser_occupancy_ms=parser,total_ms=old['total_ms'],gap_ms=old['gap_ms'],
                residual_if_entire_tail_free_ms=max(0,old['gap_ms']-(final-last)),
                ARM_instructions=old['ARM_instructions'],SPI_bytes=old['SPI_bytes'],max_credit=old['max_credit']))
    report=read(d/'board02/output_files/board.map.rpt');nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[v.strip() for v in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):
            nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==17802
    def own(suffix):
        a=[v for k,v in nodes.items() if k.endswith(suffix)];assert len(a)==1,(suffix,a)
        return a[0]
    host=own('nes_output260:flow');validator=own('nes_validator278:validator')
    def tree(suffix):
        paths=[k for k in nodes if k.endswith(suffix)];assert len(paths)==1
        return sum(v for k,v in nodes.items() if k==paths[0] or k.startswith(paths[0]+'|'))
    groups=dict(host_validator=host+validator,
        queue_SPI=own('nes_queue260:queue')+own('nes_spi270:spi_front270'),
        source=own('nes_core257:encoder')+tree('nes_transport257:transport'),
        plan=own('nes_plan_path267:retained_plan267')+tree('nes_plan_batch206:transport')+own('nes_plan_spi200:endpoint'))
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_bulk_aperture188.sv'):
        read(d/'board02'/n)
    pins[str(ROOT/'tools/analyze_nes_budget326.py')]=sha(ROOT/'tools/analyze_nes_budget326.py')
    out=dict(stage=326,passed=True,scope='reanalysis_only_no_new_RTL_ARM_CPU_MAP',rows=rows,
        whole=ref['whole'],comb_deficit=2394,own_entity_comb=nodes,groups=groups,
        all_region_budget=dict(current=sum(groups.values()),outside=17802-sum(groups.values()),maximum_remaining=sum(groups.values())-2394),
        joint_host_validator=dict(current=host+validator,outside=17802-host-validator,
            maximum_remaining_to_close_deficit=host+validator-2394,
            required_reduction_percent=239400/(host+validator)),
        caveats=['First BG timestamp is first accepted tile output byte, not ROM grant.',
            'firstmiss is ready-gated backend request; no independent PSRAM completion timestamp.',
            'Tail envelope and parser occupancy are not additive or guaranteed removable.',
            'No new timing/area improvement claimed; phase-dependent325 result remains.'],pins=pins)
    (ROOT/'analysis/budget326-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(dict(passed=True,rows=len(rows),budget=out['joint_host_validator'],warm=[x for x in rows if x['frame']==907]),indent=2))

if __name__=='__main__':main()
