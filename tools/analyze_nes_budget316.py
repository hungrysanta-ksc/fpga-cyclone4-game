# SPDX-License-Identifier: MIT
"""Audit measured NES315 critical paths and explicit replacement budgets.

No counterfactual time or resource saving is a new RTL/M4 measurement.
"""
import csv,json
from nes_delta231 import BASE,ROOT,sha

def main():
    pins={}
    def read(p):
        pins[str(p)]=sha(p)
        return p.read_text(encoding='utf-8-sig')
    ref=json.loads(read(ROOT/'analysis/response315-verification.json'))
    assert ref['passed']
    board=BASE/'probes/nes-response315/board01'
    for n in ('nes_mux260.sv','nes_queue260.sv','nes_validator278.sv','nes_joint257.sv','output_files/board.map.rpt'):
        p=board/n
        read(p)
        if str(p) in ref['input_hashes']:assert sha(p)==ref['input_hashes'][str(p)]
    rows=[]
    for mode,tag in [('normal','normal01'),('restricted','window01')]:
        d=BASE/'probes/nes-response315'/tag
        result=json.loads(read(d/'result.json'));assert result['passed']
        for name,h in result['rtl_hashes'].items():
            assert sha(d/name)==h
        ev=list(csv.reader(read(d/'joint-events.csv').splitlines()))
        for r in ref['runs'][mode]['rows']:
            f=r['frame'];e=[x for x in ev if len(x)>1 and x[1]==str(f)]
            tx=[x for x in e if x[0]=='arm267']
            assert sum(int(x[3]) for x in tx)==r['SPI_bytes']
            bg=r['first_BG_ms']
            phases={}
            for label,pred in [('before_BG',lambda t:t<bg),('after_BG',lambda t:t>=bg)]:
                selected=[x for x in tx if pred(int(x[4])/1e9)]
                phases[label]={hex(c):dict(count=sum(int(x[2])==c for x in selected),
                  wire_bytes=sum(int(x[3]) for x in selected if int(x[2])==c))
                  for c in (0xe0,0xe2,0xe1,0xe9,0xea)}
            consume=max(int(x[-1])/1e9 for x in e if x[0]=='consume293')
            releases=[x for x in e if x[0]=='release312' and int(x[2]) in (15,10,11,3)]
            arm=json.loads(read(d/f'arm{f}.json'))
            metadata=[x for x in arm['transfers'] if x['tx'].startswith(('e10f','e10a','e10b','e103'))]
            assert metadata
            last_release=max(int(x[-1])/1e9 for x in releases)
            rows.append(dict(mode=mode,frame=f,total_ms=r['total_ms'],gap_ms=r['gap_ms'],
                before_BG_ms=r['before_BG_ms'],after_BG_ms=r['after_BG_ms'],
                first_BG_ms=bg,last_consume_ms=consume,last_internal_release_ms=last_release,
                post_consume_ms=r['finish_ms']-consume,
                consume_to_internal_release_ms=last_release-consume,
                internal_release_to_finish_ms=r['finish_ms']-last_release,
                metadata_wire_bytes=sum(len(bytes.fromhex(x['tx'])) for x in metadata),
                metadata_transfer_instructions=sum(x['instructions'] for x in metadata),
                metadata_tx_completion_ms=[x['RTL_ns']/1e6 for x in metadata],
                responses_by_completion_phase=phases,
                ARM_instructions=r['ARM_instructions'],SPI_bytes=r['SPI_bytes']))
        for n in ('nes_refill267.c','nes_output264.c','nes_native289.c'):
            read(d/n)
    own=ref['own_resources']['315'];cost={k.split(':')[-1].strip('|'):v for k,v in own.items()}
    deficit=ref['comb_deficit'];narrow=cost['queue']['comb']+cost['spi_front270']['comb']
    broad=cost['flow']['comb']+cost['validator']['comb']
    r=next(x for x in rows if x['mode']=='restricted' and x['frame']==907)
    assert r['gap_ms']>0 and r['consume_to_internal_release_ms']>0
    result=dict(stage=316,kind='measured_baseline_and_replacement_budget_audit',passed=True,
        new_RTL=False,new_ARM=False,new_MAP=False,selected=False,
        baseline_whole_MAP=ref['whole_MAP'],comb_deficit=deficit,own_resources=cost,
        zero_cost_ingress_SPI_limit=dict(removed_comb=narrow,remaining_deficit=deficit-narrow,
            note='Impossible free replacement diagnostic, not realizable savings or predicted MAP'),
        host_validator_budget=dict(current_own_comb=broad,
            minimum_reduction_after_free_ingress_SPI=deficit-narrow,
            fraction=(deficit-narrow)/broad),
        timing=rows,restricted907_target=dict(required_ms=r['gap_ms'],
            post_consume_ms=r['post_consume_ms'],
            metadata_window_ms=r['consume_to_internal_release_ms'],
            fraction_of_metadata_window=r['gap_ms']/r['consume_to_internal_release_ms'],
            note='Movable-window threshold only; includes overlapping work, not additive/free saving'),
        limitations=['Metadata immutable-ready time is not instrumented in NES315.',
            'Transfer instruction counts include work since preceding checkpoint; not pure encoder cost.',
            'Phase classification uses transaction completion, not exact occupancy interval.',
            'Retained independent validation and final display checks cannot be credited as deleted.',
            *ref['limits']],input_hashes=pins)
    read(ROOT/'tools/analyze_nes_budget316.py')
    (ROOT/'analysis/budget316-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:result[k] for k in ('own_resources','zero_cost_ingress_SPI_limit','host_validator_budget','restricted907_target')},indent=2))
    for x in rows:print(json.dumps(x))

if __name__=='__main__':main()
