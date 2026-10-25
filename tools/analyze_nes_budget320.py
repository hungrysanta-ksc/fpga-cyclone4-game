# SPDX-License-Identifier: MIT
"""Rebudget remaining execution replacement using pinned319 evidence, no new runs."""
import csv,json,re
from nes_delta231 import BASE,ROOT,sha

def main():
    pins={}
    def read(p):
        pins[str(p)]=sha(p)
        return p.read_text(encoding='utf-8-sig')
    prior=json.loads(read(ROOT/'analysis/owner319-verification.json'))
    assert prior['passed'] and prior['comb_deficit']==2416
    d=BASE/'probes/nes-owner319'
    for p in [d/'board01/output_files/board.map.rpt']+[d/t/'joint-events.csv' for t in ('window01','normalref01','normal01','reference01','fixed02')]:
        assert sha(p)==prior['input_hashes'][str(p)]
    report=read(d/'board01/output_files/board.map.rpt');nodes={}
    for line in report.split('; Analysis & Synthesis Resource Utilization by Entity')[1].splitlines():
        c=[v.strip() for v in line.split(';')]
        if len(c)>12 and c[1].startswith('|') and re.fullmatch(r'\d+ \(\d+\)',c[2]):
            nodes[c[10]]=int(re.search(r'\((\d+)\)',c[2])[1])
    assert sum(nodes.values())==17824
    def cost(suffix,children=False):
        k=next(k for k in nodes if k.endswith(suffix))
        return sum(v for n,v in nodes.items() if n==k or (children and n.startswith(k+'|')))
    groups=dict(host_validator=cost('nes_output260:flow')+cost('nes_validator278:validator'),
        queue_SPI=cost('nes_queue260:queue')+cost('nes_spi270:spi_front270'),
        source=cost('nes_core257:encoder')+cost('nes_transport257:transport',True),
        plan=cost('nes_plan_path267:retained_plan267')+cost('nes_plan_batch206:transport',True)+cost('nes_plan_spi200:endpoint'))
    assert groups==dict(host_validator=3492,queue_SPI=973,source=1774,plan=461)
    scopes={}
    for name,old in [('host_validator',3492),('host_validator_ingress',4465),('source_plan',2235),('all',6700)]:
        scopes[name]=dict(current=old,ceiling=old-2416,ceiling_with_128_margin=old-2544,required_reduction_percent=2416/old*100)
    rows=[]
    for tag in ('window01','normalref01','normal01','reference01','fixed02'):
        ev=list(csv.reader(read(d/tag/'joint-events.csv').splitlines()))
        for f in (905,906,907):
            e=[x for x in ev if len(x)>1 and x[1]==str(f)]
            finish=int(next(x for x in e if x[0]=='frame_done')[2])/1e9
            consume=max(int(x[-1]) for x in e if x[0]=='consume293')/1e9
            seal=max(int(x[-1]) for x in e if x[0]=='release312' and x[2]=='3')/1e9
            bg=int(next(x for x in e if x[:3]==['romtile305',str(f),'0'])[-1])/1e9
            assert bg<=consume<=seal<=finish
            rows.append(dict(run=tag,frame=f,first_BG_ms=bg,last_consume_ms=consume,seal_release_ms=seal,finish_ms=finish,
                BG_to_consume_ms=consume-bg,consume_to_seal_ms=seal-consume,seal_to_finish_ms=finish-seal,
                post_consume_ms=finish-consume,tail_ms=finish-bg))
    warm=next(x for x in rows if x['run']=='window01' and x['frame']==907)
    gap=prior['remaining_ms']
    assert abs(warm['post_consume_ms']-.236063)<1e-9
    for n in ('nes_mux260.sv','nes_validator278.sv','nes_core257.sv','nes_transport257.sv','nes_plan_batch206.sv','nes_queue260.sv','nes_spi270.sv'):
        p=d/'board01'/n
        assert sha(p)==prior['input_hashes'][str(p)]
        read(p)
    out=dict(stage=320,passed=True,kind='review_not_implementation',new_RTL=False,new_ARM=False,new_MAP=False,
        baseline_MAP=prior['whole_MAP'],comb_deficit=2416,groups=groups,outside_comb=11124,scope_budgets=scopes,
        schedules=rows,remaining_ms=gap,
        time_budget=dict(current_tail_ms=warm['tail_ms'],required_tail_ms=warm['tail_ms']-gap,
            post_consume_ms=warm['post_consume_ms'],minimum_upstream_gain_even_if_tail_free_ms=gap-warm['post_consume_ms'],
            chosen_upstream_target_ms=.400,chosen_post_consume_target_ms=.060,chosen_total_target_ms=.460,
            projected_margin_if_targets_met_ms=.460-gap),
        targets_are_predictions=False,physical_60fps_proven=False,input_hashes=pins)
    out['input_hashes'][str(ROOT/'tools/analyze_nes_budget320.py')]=sha(ROOT/'tools/analyze_nes_budget320.py')
    (ROOT/'analysis/budget320-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:out[k] for k in ('groups','scope_budgets','time_budget')},indent=2))

if __name__=='__main__':main()
