"""Reconcile identical-generation input traffic, old output intervals, and joint MAP costs."""
import argparse
import json
from statistics import mean
from pathlib import Path
import zipfile

from budget_nes_pages596 import blocks, sections
from check_nes_game478 import encode, sha
from check_nes_map598 import ROOT


def read(p):
    return json.loads(p.read_bytes())


def evidence(name):
    return read(ROOT/'analysis'/name)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('archive','unit','local','boundary','cached','pins','control','out'):
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    body_581=evidence('body581-verification.json')
    manifest=body_581['inputs']
    output_reference=evidence('abi582-verification.json')['frames']
    timing=evidence('whole580-verification.json')
    history=evidence('roles590-verification.json')['frames']
    previous=evidence('region597-verification.json')
    joint=read(a.boundary/'result.json')
    joint.update(read(a.cached/'result.json'))
    local=read(a.local/'result.json')
    unit=read(a.unit/'result.json')['tap']
    assert unit['pins']==local['tap']['pins']
    pins=read(a.pins/'result.json')
    control=read(a.control/'result.json')
    assert control['ELF']==pins['ELF'] and control['frames']==[r['packed'] for r in previous['rows']]
    assert pins['ELF']==previous['ELF'] and pins['repair_rows']==29 and pins['repair']['actions']==[0,3,4]
    assert pins['display']==previous['guards']['display']
    assert pins['cold_recovery']=={k:v for k,v in pins['frames'][0].items() if k!='generation'}
    for name,row in joint.items():
        path=(a.cached if name=='cached598' else a.boundary)/(name+'.map.rpt')
        assert sha(path)==row['report']
    rows=[]
    with zipfile.ZipFile(a.archive) as z:
        import hashlib
        for g,old in zip(range(905,958),history,strict=True):
            assert g==old['generation']
            inputs=[]
            for ext in ('geometry','raw'):
                k=f'frame{g}.{ext}';b=z.read('data/'+k)
                assert hashlib.sha256(b).hexdigest()==manifest[k]
                inputs.append(b)
            arrays=encode(*inputs,g)[2]+[list(inputs[1])]
            n=len(arrays[0])//33
            wanted=old['batched_shift']['full_rows']
            summaries=n if g!=905 else 0
            rec=list(blocks(arrays))
            pages=(1+1+summaries//30 + max(1,(wanted+2)//3)
                   +sum(map(len,sections(rec,'reserve')))+3)
            body=32+5*8+8*summaries+72*wanted+sum(len(b) for b,_ in rec)
            # Each D1 includes 2 phase bytes and 3 read/CRC bytes. D2 and
            # its D0 confirmation are each 8 B. All other ready polls omitted.
            fixed=body+21*pages+32*(3 if g!=905 else 2)+24
            literal=sum(len(values)*w for values,w in zip(arrays,(2,1,7,4,7,1,1)))
            phases=[]
            for phase in timing['phases']:
                if str(g) not in phase['frames']:continue
                frame=phase['frames'][str(g)];t=frame['terms']
                output=sum(frame['operation_wire_B'].get(k,0) for k in ('0xe1','0xe9','0xea'))
                old_phase=body_581['frames'][str(g)]['phases'][str(phase['phase'])]
                output_row=output_reference[g-905]
                assert output_row['generation']==g
                reuse=output_row['reuse'][str(phase['phase'])]
                out582=(output-old_phase['output']['map']['wire_B']+output_row['map']['wire_B']
                        -reuse['omitted_wire_B']+reuse['declaration_wire_B'])
                old_in=sum(frame['operation_wire_B'].get(k,0) for k in ('0xd0','0xd1','0xd2','0xd3'))
                post=sum(v for k,v in t.items() if k.startswith('SEAL_'))
                total=sum(t.values())
                assert abs(total-frame['ACK_interval_ms'])<1e-8
                phases.append(dict(phase=phase['phase'],old_input_ms=t['source_to_planner_ms'],
                                   planner_ms=t['planner_to_output_ms'],output_to_seal_ms=t['output_to_SEAL_head_ms'],
                                   seal_to_ack_ms=post,other_before_input_ms=t['previous_ACK_to_source_ms'],
                                   old_ack_interval_ms=total,old_noninput_ms=total-t['source_to_planner_ms'],
                                   selected_output_wire_B=output,packed_plus_output_min_B=fixed+output,
                                   literal_plus_output_min_B=literal+output,reference_output_B=out582,
                                   inherited_check_B=reuse['inherited_check_B'],
                                   old_input_all_plus_reference_output_B=old_in+out582,
                                   packed_min_plus_reference_output_B=fixed+out582))
            rows.append(dict(generation=g,groups=n,map_scan_reads_removed=n*33,
                             remaining_requested_words=wanted*33,summary_reads=summaries,pages=pages,
                             fixed_packed_input_B=fixed,unframed_literal_B=literal,phases=phases))
    assert sum(r['groups'] for r in rows)==unit['groups']
    for row,actual in zip(rows[:2],pins['frames'],strict=True):
        assert row['pages']==actual['packets'] and actual['wire_B']>=row['fixed_packed_input_B']
        polls=actual['calls']-3*row['pages']-2*len(actual['actions'])-3
        assert actual['wire_B']==row['fixed_packed_input_B']+8*polls
    groups={}
    for label,start,end in [('warm',907,957),('dense',951,955)]:
        window=[r for r in rows if start<=r['generation']<=end]
        groups[label]=[]
        for i in range(2):
            phases=[r['phases'][i] for r in window]
            groups[label].append({k:mean(r[k] for r in phases) for k in phases[0] if k!='phase'})
    result=dict(stage=598,groups=groups,frames=rows,unit=unit,collector_MAP=local,
                joint_MAP=joint,regional_screen_LE=joint['original']['LE']+148,pin_test=pins,pin_control=control,
                retained_board=evidence('source588-verification.json')['fit'],
                physical_baseline='MMC577',new_full_board_fit=False,new_two_phase_timing=False,
                scope='BG/row input reconstructed from pinned captures. Other query kinds and display peer modeled. The two phases are the unchanged 580 schedule; fixed shared wire excludes other polls and ROM.')
    a.out.write_bytes((json.dumps(result,indent=2)+'\n').encode())


if __name__=='__main__':main()
