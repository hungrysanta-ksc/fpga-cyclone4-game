# SPDX-License-Identifier: MIT
"""Bind actual M4 frontier observations to the proposed joint control boundary."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha


def main():
    ap=argparse.ArgumentParser();ap.add_argument('--frontier',required=True,type=Path)
    ap.add_argument('--out',required=True,type=Path);a=ap.parse_args()
    a.out.mkdir(parents=True,exist_ok=False);pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    r=js(a.frontier/'result.json');assert r['passed'] and len(r['frames'])==71
    assert r['script_sha256']==sha(ROOT/'tools/probe_nes_frontier292.py')
    read(ROOT/'tools/probe_nes_frontier292.py')
    for name,h in r['input_hashes'].items():assert sha(Path(name))==h;pins[name]=h
    steps=list(csv.DictReader(read(a.frontier/'steps.csv').splitlines()))
    old=js(ROOT/'analysis/joint291-verification.json')
    previous=js(ROOT/'analysis/joint289-verification.json')
    original=js(a.frontier.parent/'frontier01/result.json')
    rows=[]
    for f in r['frames']:
        reference=next(x for x in previous['native_frames'] if x['frame']==f['frame'])
        assert f['producer_instructions']==reference['producer_instructions']
        first=next(x for x in original['frames'] if x['frame']==f['frame'])
        for key in ('components','steps','plans','ranges','planner_steps_instructions','early_closed','early_hypothetical_closed'):
            assert f[key]==first[key],(f['frame'],key)
        ss=[s for s in steps if int(s['frame'])==f['frame']]
        assert len(ss)==30 and sum(int(s['instructions']) for s in ss)==f['planner_steps_instructions']
        assert [int(s['result']) for s in ss]==[1]*29+[2]
        early=ss[:-1]
        hypot=[(int(s['step']),json.loads(s['hypothetical_detail'])) for s in early if int(s['hypothetical_freeze_closed'])]
        nonzero=[(n,rr) for n,rr in hypot if any(x[0]!=0 or x[1]!=0 or x[2]!=16 for x in rr)]
        pending=bytes.fromhex(ss[-2]['pending_hex'])
        # Frame generation is kept in the initial 3-byte zero plan; the BG
        # frontier is tentative, never an authorization to use uncommitted data.
        assert len(bytes.fromhex(f['initial_pending_hex']))==3
        row=dict(frame=f['frame'],plans=f['plans'],ranges=f['ranges'],
                 first_immutable_step=f['first_immutable'],final_step=f['final_step'],
                 before_final_immutable=int(ss[-2]['immutable_plans']),
                 before_final_pending=int(ss[-2]['pending_plans']),
                 before_final_pending_bytes=len(pending),
                 early_closed=f['early_closed'],
                 hypothetical_first_closed_step=hypot[0][0] if hypot else None,
                 hypothetical_nonblank_closed_step=nonzero[0][0] if nonzero else None,
                 final_step_instructions=int(ss[-1]['instructions']),
                 final_step_CPI1_ms=int(ss[-1]['instructions'])/84000,
                 step_calls_CPI1_ms=f['planner_steps_instructions']/84000,
                 producer_CPI1_ms=f['producer_instructions']/84000,
                 real_new_frame_ms=None)
        rows.append(row)
    warm=rows[2:]
    assert all(x['first_immutable_step']==29 and x['early_closed']==0 for x in warm)
    assert len(steps)==2130
    # Structural contract: one main host controller plus the concurrent bus
    # observer/tap. This is deliberately not a simulated or synthesized FSM.
    transitions=[
        ('HEAD','queue ready + admitted identity','READ_HEADER','hold head; reset packet CRC mask','no credit return'),
        ('READ_HEADER','registered byte valid and identity matches','ADMIT','advance one packet reader','retain qtag/latency'),
        ('ADMIT','H2/BEGIN/map/ordinary/manifest checks','EXECUTE','select operation and single continuation','retain independent bounds'),
        ('EXECUTE','ordinary command exposed','BUS_WAIT','enable bus observer and CRC tap','head and descriptor immutable'),
        ('BUS_WAIT','exact reads + ordered ACK + tap drained','RANGE_READ','admit independent receipt walk','ACK alone never retires'),
        ('EXECUTE','map chunk staged','DMA_WAIT','publish held token/length/first','retain aperture owner'),
        ('DMA_WAIT','exact reads + full token consume','RANGE_READ','admit map receipt walk','no staging-as-DMA shortcut'),
        ('RANGE_READ','RAM result registered','RANGE_TEST','capture coverage mask','CRC domain remains independent'),
        ('RANGE_TEST','no duplicate + raw CRC coverage','VALID_READ_OR_NEXT','write provisional receipt; read persistent validity if ordinary','fault blocks every write'),
        ('VALID_READ_OR_NEXT','required validity write complete','RANGE_READ_OR_COMPLETE','advance byte range or common completion','retain persistent map_end'),
        ('EXECUTE','manifest literal or decoded RLE byte available','MANIFEST_READ','hold value and expanded index','compressed/expanded cursors distinct'),
        ('MANIFEST_READ','all required RAM comparisons pass','MANIFEST_NEXT','advance expanded cursor and return to decoder','422-byte/cold/raw0 checks retained'),
        ('COMPLETE','more map ranges in same packet','READ_DESCRIPTOR','advance token and descriptor','keep credit until last range'),
        ('COMPLETE','whole command valid, not final display','RETIRE','one qretire and packet sequence advance','tap and RAM work finished'),
        ('EXECUTE','manifest complete + H2/digest/certificate valid','DISPLAY','seal and supply 12 byte H2 view','retain RAM read latency'),
        ('DISPLAY','12 exact reads + full final token + empty queue/owner','FINAL_ACK','existing mailbox then lease return','packet ACK cannot substitute'),
        ('ANY','STOP/fault','FAULT','gate RAM writes, invalidate, burn allocated tokens','no stale callback or ACK resumes execution')]
    contract=[dict(state=x[0],guard=x[1],next=x[2],action=x[3],invariant=x[4]) for x in transitions]
    boundary=[]
    for label,added in [('fixed291',0),('plus_source_encoder_transport',1346+425),('plus_source_and_tile_aperture',1346+425+204+167)]:
        size=4853+added;outside=17671-size;budget=15408-outside
        boundary.append(dict(boundary=label,old_comb=size,outside_comb=outside,replacement_budget=budget,
                             reserve128_budget=budget-128,required_reduction=2263,
                             required_percent=226300/size,measured_replacement_comb=None))
    sim=BASE/'probes/nes-joint289/test02'
    anchors={
        'nes_planner285.c':['batch_count285==15||batch_size285+n>240','order247_insert(batch285','return batch_count285<15||flush285();'],
        'nes_input286.inc':['if(result==2&&!flush285())'],
        'nes_planner211.c':['ctx286.g<ctx286.groups','No later lookup reads bg_keys','rank<8'],
        'nes_tile_producer260.sv':['opened&&!append_ok','if(opened)state<=SEAL'],
        'nes_resident211.c':['q->kind!=2&&equal&&bit(s->resident[s->target],index)'],
        'nes_mux260.sv':['if(qdone&&tap_idle278&&range_ready)','wire [7:0] qaddr=','state==CONSUME'],
        'nes_validator278.sv':['V_RWRITE:if(!crc_covered287)','V_PCHECKTEST:if(checked_byte'],
        'nes_joint257.sv':['always @(posedge clk)begin aq','always @(posedge host_clk)begin bq']}
    evidence=[]
    for file,checks in anchors.items():
        text=read(sim/file)
        for anchor in checks:
            hits=[i+1 for i,l in enumerate(text.splitlines()) if anchor in l]
            assert hits,(file,anchor)
            evidence.append(dict(file=file,anchor=anchor,lines=hits))
    # Bind the broadened own-cost entries to the original mapped hierarchy.
    area=js(ROOT/'analysis/joint287-verification.json')
    report=read(BASE/'probes/nes-joint287/board01/output_files/board.map.rpt')
    import re
    own={}
    for line in report.splitlines():
        fields=[x.strip() for x in line.split(';')]
        if len(fields)==14 and re.fullmatch(r'\d+ \(\d+\)',fields[2]):own[fields[10]]=int(re.search(r'\((\d+)\)',fields[2]).group(1))
    for key,n in [('nes_core257:encoder',1346),('nes_transport257:transport',425),('nes_tile_producer260:tiles',204),('nes_bulk_aperture188:shared_ram.aperture',167)]:
        assert sum(v for k,v in own.items() if key in k)==n
    result=dict(passed=True,stage=292,selected=['frontier02','analysis01'],
                kind='actual_retained_ARM_frontier_and_unimplemented_controller_design',
                frames=rows,steps=len(steps),
                warm_count=69,warm_first_immutable_only_final=69,
                warm_only_blank_plan=sum(x['plans']==1 for x in warm),
                warm_hypothetical_closed=sum(x['hypothetical_first_closed_step'] is not None for x in warm),
                warm_hypothetical_nonblank_closed=sum(x['hypothetical_nonblank_closed_step'] is not None for x in warm),
                controller_contract=contract,boundary_scenarios=boundary,source_anchors=evidence,
                retained_area=old['whole_comb'],retained_deficit=old['deficit'],
                new_RTL=False,new_MAP=False,new_schedule=False,actual_ACK=False,P2_selected=False,
                decision='Investigate BG-phase batch publication with actual E9/ROM timing; controller area fit remains unproven.',
                input_hashes=pins,script_sha256=sha(Path(__file__)))
    for name,data in [('frontier',rows),('controller',contract),('boundaries',boundary)]:
        with (a.out/(name+'.csv')).open('w',newline='',encoding='utf-8') as fp:
            w=csv.DictWriter(fp,fieldnames=list(data[0]),lineterminator='\n');w.writeheader();w.writerows(data)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('frames','controller_contract','source_anchors','input_hashes')},indent=2))


if __name__=='__main__':main()
