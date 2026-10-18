# SPDX-License-Identifier: MIT
"""Measured register activity and explicitly limited access-budget scenarios."""
from pathlib import Path
import argparse, collections, csv, json, math
from nes_delta231 import BASE, ROOT, sha
from nes_operand242 import FIELDS, PINNED, inventory

PERIOD_NS=45.454
HOT={'row_i','old1','old2','new1','new2'}


def analyze(run):
    result=json.loads((run/'result.json').read_text())
    assert result['passed'] and result['baseline240_cycles_exact']
    assert (result['frames'],result['records'],result['blocks'],result['payload'],result['exact_c_files'])==(71,2229,350,62967,355)
    for p,h in result['observer_pins'].items(): assert sha(ROOT/p)==h,p
    assert sha(run/'nes_source_encoder240.sv')==result['instrumented_encoder_sha256']
    inv=json.loads((run/'inventory.json').read_text())
    assert inv==json.loads(json.dumps(inventory((ROOT/'src/nes/rtl/nes_source_encoder240.sv').read_text())))
    states=inv['states']; names=list(FIELDS); width=[(w+7)//8 for w in FIELDS.values()]
    timing={int(r['frame']):{k:int(v) for k,v in r.items() if k!='frame'}
            for r in csv.DictReader((run/'cycles.csv').open())}
    fields={n:collections.Counter() for n in names}
    totals=collections.Counter(); state_counts=collections.Counter(); state_bytes=collections.Counter()
    frame={f:collections.Counter() for f in timing}
    for row in csv.DictReader((run/'operands.csv').open()):
        f=int(row['frame']); state=states[int(row['state'])]; count=int(row['cycles'])
        rd=int(row['reads'],16); wr=int(row['writes'],16); alu=int(row['alu_bytes']); ram=int(row['ram_ops'])
        assert rd|wr < (1<<len(names))
        frame[f]['observed_cycles']+=count
        state_counts[state]+=count if f>=907 else 0
        # Transfer state SREAD resolves and latches the address once per byte.
        # A new byte latch is REQUIRED before reusing scratch ports. Keeping
        # byte_data directly on a_q, as240 does, would break stalled views.
        # Protocol waits and unchanged RAW response wait do not reload operands.
        useful=state not in {'REQUEST','WAITACK','SBYTE','FETCH'} and (state!='RAWWAIT' or wr!=0)
        if not useful:continue
        read_bytes=sum(w for i,w in enumerate(width) if rd>>i&1)
        write_bytes=sum(w for i,w in enumerate(width) if wr>>i&1)
        hot_reads=sum(w for i,w in enumerate(width) if rd>>i&1 and names[i] in HOT)
        hot_writes=sum(w for i,w in enumerate(width) if wr>>i&1 and names[i] in HOT)
        for policy,r,w in [('all_rf',read_bytes,write_bytes),('hot5_retained',read_bytes-hot_reads,write_bytes-hot_writes)]:
            # Best-case issue floor for THIS uncached access policy. It is NOT
            # a lower bound on all possible architectures or an executable
            # schedule: comparisons, instruction fetch, dependency latency,
            # RF address decode and control/PC operations are not included.
            slots=max(math.ceil((r+w+ram)/2),alu,1)
            frame[f][policy+'_ideal_extra_cycles']+=max(0,slots-1)*count
            frame[f][policy+'_operand_reads']+=r*count
            frame[f][policy+'_operand_writes']+=w*count
        if f>=907:
            totals['executed_write_bytes']+=write_bytes*count
            totals['conservative_read_bytes']+=read_bytes*count
            totals['selected_arithmetic_byte_ops']+=alu*count
            totals['payload_port_ops']+=ram*count
            state_bytes[state]+=(read_bytes+write_bytes)*count
            for i,n in enumerate(names):
                if rd>>i&1:fields[n]['conservative_reads']+=count;fields[n]['read_bytes']+=width[i]*count
                if wr>>i&1:fields[n]['executed_writes']+=count;fields[n]['write_bytes']+=width[i]*count
    rows=[]
    for f,t in timing.items():
        assert frame[f]['observed_cycles']==t['total']+1,(f,frame[f]['observed_cycles'],t['total'])
        r=dict(frame=f,baseline=t,access_policy=dict(frame[f]))
        for policy in ('all_rf','hot5_retained'):
            extra=frame[f][policy+'_ideal_extra_cycles']
            r[policy]=dict(extra_issue_ms=extra*PERIOD_NS/1e6,
                          baseline_prepare_plus_issue_ms=(t['prepare']+extra)*PERIOD_NS/1e6,
                          baseline_total_plus_issue_ms=(t['total']+extra)*PERIOD_NS/1e6)
        rows.append(r)
    warm=[r for r in rows if r['frame']>=907]
    summary={}
    for policy in ('all_rf','hot5_retained'):
        key=policy+'_ideal_extra_cycles'
        worst=max(warm,key=lambda r:r['access_policy'][key])
        summary[policy]=dict(extra_cycles_sum=sum(r['access_policy'][key] for r in warm),
            extra_cycles_max=worst['access_policy'][key],extra_cycles_max_frame=worst['frame'],
            extra_ms_max=worst[policy]['extra_issue_ms'],
            prepare_plus_issue_max_ms=max(r[policy]['baseline_prepare_plus_issue_ms'] for r in warm),
            isolated_total_plus_issue_max_ms=max(r[policy]['baseline_total_plus_issue_ms'] for r in warm))
    return dict(stage=242,baseline=240,production=227,scope='Instrumented240 actual recorded first-level71; no new datapath or hardware FPS.',
        result_sha256=sha(run/'result.json'),profile_sha256=sha(run/'operands.csv'),
        cycles_sha256=sha(run/'cycles.csv'),inventory=inv,warm_frames=69,
        activity=dict(totals),fields=fields,states=state_counts,
        top_access_states=state_bytes.most_common(12),policy_summary=summary,frames=rows,
        model_limitations=['Conservative per-state reads include untaken branches; writes are executed assignments, including same-value writes.',
            'Ideal two-port/one-byte-ALU issue floor for specified uncached policy, not an executable schedule or overall runtime bound.',
            'Branch comparisons, instruction fetch/dependency latency/address decode/PC are excluded; no inference of area savings.',
            'Adding ideal issue costs to baseline is a sensitivity calculation, not a retimed real SPI/ARM/SNES simulation.',
            'The proposed byte output latch and scratch arbitration are not implemented.',
            'Initialization checks cover these recorded paths, not all branch/lifetime cases or formal liveness.',
            'Original240 timing/output exactness validates the observer only. Production remains227.'],
        analyzer_sha256=sha(Path(__file__)),new_fit=False,new_datapath=False,physical=False,fps_proven=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();a.out.mkdir(parents=True)
    r=analyze(a.run);(a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps({k:r[k] for k in ('activity','top_access_states','policy_summary')},indent=2))


if __name__=='__main__':main()
