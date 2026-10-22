# SPDX-License-Identifier: MIT
"""Deletion boundary and hard budgets from measured307/310, not new timing."""
import csv,json
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha


def main():
    pins={}
    def pin(p):pins[str(p)]=sha(p);return p
    def js(p):return json.loads(pin(p).read_text(encoding='utf-8-sig'))
    b=js(ROOT/'analysis/ingress307-verification.json');c=js(ROOT/'analysis/storage310-verification.json')
    old=js(ROOT/'analysis/overlap308-verification.json')
    own=b['regions'];assert sum(own.values())==4730
    trio=sum(own[k] for k in ('queue','host','validator'));outside=b['whole_MAP']['comb']-trio
    budgets=dict(admission_DMA_owner=700,independent_validator_CRC_display=900,queue_SPI_ingress_response=450,plan_transport=328,glue=49)
    assert sum(budgets.values())==2427
    rows=[];packets=[]
    for tag,root,mode in [('307',BASE/'probes/nes-ingress307/window03','restricted'),('310',BASE/'probes/nes-storage310/window05','restricted')]:
        proof=js(root/'result.json');assert proof['passed']
        for n,h in proof['rtl_hashes'].items():assert sha(pin(root/n))==h
        assert sha(pin(root/'output.elf'))==proof['ELF_sha256']
        assert sha(pin(root/'joint266_tb.sv'))==proof['tb_sha256']
        events=list(csv.reader(pin(root/'joint-events.csv').open()))
        issue=js(root/'issue307.json')
        for f in (905,906,907):
            rec=next(x for x in (b[mode] if tag=='307' else c['runs'][mode]['rows']) if x['frame']==f)
            es=[x for x in events if len(x)>1 and x[1]==str(f)]
            bg=next(x for x in es if x[:3]==['firstmiss305',str(f),'0'])
            frame_start=rec['absolute_finish_ms']-rec['total_ms']
            rows.append(dict(stage=int(tag),frame=f,total_ms=rec['total_ms'],start_ms=frame_start,
                finish_ms=rec['absolute_finish_ms'],BG_grant_ms=int(bg[-1])/1e9,
                start_to_BG_ms=int(bg[-1])/1e9-frame_start,
                BG_to_finish_ms=rec['absolute_finish_ms']-int(bg[-1])/1e9,
                status_reads_E2=sum(x[0]=='arm267' and x[2]=='226' for x in es),
                status_reads_E0=sum(x[0]=='arm267' and x[2]=='224' for x in es),
                status_extra_wire_ms_fixed_count=2*sum(x[0]=='arm267' and x[2] in ('224','226') for x in es)*8/2625,
                E1_issues_with_pending_ge2=sum(x['generation']==f-904 and x['pending']>=2 for x in issue),
                note='pending>=2 is a two-slot pressure diagnostic, not predicted extra waits'))
            for x in js(root/f'arm{f}.json')['transfers']:
                raw=bytes.fromhex(x['tx'])
                if not raw or raw[0]!=0xe1:continue
                p=raw[1:-2];assert 16<=len(p)<=256
                # Keep compact batch entries; no 24-byte expansion per range.
                payload=len(p)-(21 if p[0]==14 else 16)
                assert payload>=0 and 24+payload<=272
                packets.append(dict(stage=int(tag),frame=f,op=p[0],wire_packet_bytes=len(p),normalized_record_plus_payload=24+payload))
    a=next(x for x in rows if x['stage']==307 and x['frame']==907)
    z=next(x for x in rows if x['stage']==310 and x['frame']==907)
    assert a['BG_grant_ms']==z['BG_grant_ms']
    assert abs((z['total_ms']-a['total_ms'])-((z['finish_ms']-a['finish_ms'])-(z['start_ms']-a['start_ms'])))<1e-10
    # Exact existing 1024-byte queue replacement. Canonical manifest is 190+256.
    regions=[('requirements',0,190),('map_expected',190,446),('manifest_directory',446,478),('padding',478,480),('stream0',480,752),('stream1',752,1024)]
    occupied=set()
    for _,lo,hi in regions:
        part=set(range(lo,hi));assert not occupied&part;occupied|=part
    assert occupied==set(range(1024))
    for name in ('nes_queue260.sv','nes_mux260.sv','nes_validator278.sv','nes_spi270.sv','nes_plan_spi200.sv','nes_refill267.c','nes_output264.c'):
        pin(BASE/'probes/nes-ingress307/window03'/name)
    pin(BASE/'probes/nes-ingress307/board03/output_files/board.map.rpt')
    pin(BASE/'probes/nes-storage310/board01/output_files/board.map.rpt')
    gap=a['total_ms']-1000/60
    result=dict(stage=311,passed=True,kind='measured_evidence_deletion_boundary_budget_audit',new_ARM_run=False,new_RTL=False,new_MAP=False,
        baseline=307,baseline_whole_MAP=b['whole_MAP'],rejected310_whole_MAP=c['whole_MAP'],regions=own,
        area=dict(trio=trio,trio_outside=outside,trio_hard_cap=15408-outside,trio_function_cap=15408-outside-128,
            extended_boundary=4730,extended_outside=12853,extended_hard_cap=2555,extended_function_cap=2427,
            reserve=128,required_net_reduction=2175,required_with_reserve=2303,requirements_not_estimates=budgets),
        time=dict(required_net_ms=gap,reserve_ms=.25,required_with_reserve_ms=gap+.25,
            maximum_frame_ms=1000/60,preferred_frame_ms=1000/60-.25,
            fixed_start_finish_deadline_ms=a['start_ms']+1000/60,
            shifted310_start_finish_deadline_ms=z['start_ms']+1000/60,
            removed_manifest_accounting_ms=old['manifest_only']['accounting_sum_ms'],
            gap_after_free_manifest_accounting_ms=old['manifest_only']['remaining_if_sum_removed_ms'],
            note='No fixed-start bound, no free overlap, and no candidate timing prediction'),
        measured_schedules=rows,storage=dict(regions=regions,total_bytes=1024,canonical_manifest_bytes=446,
            directory_bytes=32,stream_slots=2,slot_bytes=272,descriptor_bytes=24,max_payload_bytes=240,
            max_record_bytes=264,per_slot_slack_bytes=8,extra_RAM_bits_required_by_layout=0,
            retained_compact_batch_entries=True,all_general_metadata_preload=False),
        packet_shape_checks=len(packets),max_observed_record_bytes=max(x['normalized_record_plus_payload'] for x in packets),
        candidate_MAP=None,candidate_time_ms=None,selected_for_implementation_boundary=True,selected_for_production=False,input_hashes=pins)
    pin(Path(__file__))
    (ROOT/'analysis/boundary311-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps({k:result[k] for k in ('area','time','measured_schedules','storage','packet_shape_checks')},indent=2))
if __name__=='__main__':main()
