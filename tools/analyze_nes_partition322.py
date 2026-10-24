# SPDX-License-Identifier: MIT
"""Audit actual319 transfers; candidate wire costs, not new ARM/RTL timings."""
import json, math
from collections import Counter
from nes_delta231 import BASE, ROOT, sha

def main():
    pins={}
    def read(p):
        pins[str(p)]=sha(p)
        return json.loads(p.read_text(encoding='utf-8-sig'))
    budget=read(ROOT/'analysis/budget320-verification.json')
    rejected=read(ROOT/'analysis/execute321-verification.json')
    assert budget['passed'] and rejected['passed']
    rows=[]
    for run in ('window01','normal01','fixed02'):
        for frame in (905,906,907):
            obj=read(BASE/f'probes/nes-owner319/{run}/arm{frame}.json')
            ops=Counter(); ordinary=[]; metadata_bytes=0; metadata_packets=0; ranges=0
            crossings=0; batch_packets=0
            for t in obj['transfers']:
                tx=bytes.fromhex(t['tx'])
                if not tx or tx[0]!=0xe1: continue
                h=tx[1:17]; op=h[0]; ops[op]+=1
                plen=int.from_bytes(h[12:14],'little')
                assert len(tx)==plen+19,(run,frame,op,len(tx),plen)
                if op in (15,10,11):
                    metadata_bytes+=len(tx);metadata_packets+=1
                if op in (2,4,5,8,7):
                    start=int.from_bytes(h[10:12],'little')
                    span=plen if op==2 else int.from_bytes(h[14:16],'little')
                    ordinary.append(dict(op=op,section=h[1],start=start,span=span,encoded=plen))
                    if h[1]==5:
                        crossings+=sum(start<b<start+span for b in (1121,3169))
                if op==14:
                    batch_packets+=1; n=tx[21]; ranges+=n; p=22
                    for _ in range(n):
                        count=tx[p+2]; assert 0<count<=64 and count%2==0
                        p+=3+count
                    assert p==len(tx)-2
            # Replacement dense op15: 190 payload; map256 split across <=240 payload packets.
            dense_packets=1+math.ceil(256/240)
            dense_bytes=190+256+19*dense_packets
            rows.append(dict(run=run,frame=frame,op_counts=dict(sorted(ops.items())),
                ordinary=ordinary,domain_boundary_crossings=crossings,map_ranges=ranges,batch_packets=batch_packets,
                metadata_wire_bytes=metadata_bytes,metadata_packets=metadata_packets,
                dense_metadata_wire_bytes=dense_bytes,dense_extra_bytes=dense_bytes-metadata_bytes,
                dense_extra_packets=dense_packets-metadata_packets,
                redundant_receipt_pair_extra_bytes=4*len(ordinary),
                proposed_replacement_format_extra_bytes=0,
                proposed_replacement_format_extra_bytes_is_design_constraint=True))
    out=dict(stage=322,passed=True,kind='trace_audit_and_protocol_budget',baseline=319,
        new_ARM_run=False,new_RTL=False,new_Quartus_run=False,
        baseline_MAP=budget['baseline_MAP'],comb_deficit=2416,remaining_ms=budget['remaining_ms'],
        rows=rows,scope_budgets=budget['scope_budgets'],
        time_budget=budget['time_budget'],candidate_area_saving=None,candidate_ARM_cycles=None,
        candidate_critical_path_gain_ms=None,physical_60fps_proven=False,input_hashes=pins)
    out['input_hashes'][str(ROOT/'tools/analyze_nes_partition322.py')]=sha(ROOT/'tools/analyze_nes_partition322.py')
    (ROOT/'analysis/partition322-verification.json').write_text(json.dumps(out,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps([{k:v for k,v in r.items() if k!='ordinary'} for r in rows],indent=2))

if __name__=='__main__': main()
