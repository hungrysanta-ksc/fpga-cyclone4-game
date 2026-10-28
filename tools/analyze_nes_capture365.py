# SPDX-License-Identifier: MIT
"""Verify shared RTL identity, source read handoff and bounded capture cadence.

Processing latency excludes capture. The free-running test covers real908 while
907 outputs plus the following909 start, not an unbounded frame throughput proof.
"""
import hashlib,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE
from nes_capture365 import COMMON

PINS={}
def read(p):
    p=Path(p);b=p.read_bytes();PINS[str(p)]=hashlib.sha256(b).hexdigest();return b.decode('utf-8')
def data(p):return json.loads(read(p))
def events(d):return [x.split(',') for x in read(d/'joint-events.csv').splitlines()]
def event(rows,name,frame):return next(x for x in rows if x[:2]==[name,str(frame)])
def whole(d):
    r=data(d/'result.json');assert r['passed'] and not r['undriven']
    summary=r['summary']
    labels={'LE':'Total logic elements','comb':'Total combinational functions','FF':'Dedicated logic registers','RAM_bits':'Total memory bits'}
    return {k:int(re.search(re.escape(v)+r'\s*:\s*([\d,]+)',summary).group(1).replace(',','')) for k,v in labels.items()}

def main():
    read(ROOT/'tools/analyze_nes_capture365.py');read(ROOT/'tools/nes_capture365.py')
    b=BASE/'probes/nes-capture365';ref=b/'early03';board=b/'map03'
    control=b/'test04';negative=b/'cadence01'
    rr=data(ref/'result.json');assert rr['passed'] and rr['frames']==4
    manifest=data(ref/'manifest365.json');assert manifest['early_release'] and manifest['cadence']
    hashes={}
    source_root=ROOT/'src/fpga/nes_capture365'
    source_manifest=data(source_root/'manifest.json')
    for relative,expected in source_manifest['source_files'].items():
        p=source_root/relative;read(p);assert PINS[str(p)]==expected
        assert expected==manifest['shared_boundary'][p.name]
    qsf=read(board/'board.qsf')
    compiled=set(re.findall(r'-name SYSTEMVERILOG_FILE\s+"?([^\s"]+)',qsf))
    assert set(COMMON)<=compiled, set(COMMON)-compiled
    for n in COMMON:
        read(ref/n);read(board/n)
        assert PINS[str(ref/n)]==PINS[str(board/n)]==manifest['shared_boundary'][n],n
        hashes[n]=manifest['shared_boundary'][n]
    assert '#(.EARLY_RELEASE(1)) frame(' in read(ref/'joint266_tb.sv')
    assert '#(.EARLY_RELEASE(1)) native_frame(' in read(board/'nes_live_joint.sv')
    # Match every shared functional module, including unchanged validator/queues.
    bymodule={}
    for f in board.glob('*.sv'):
        if f.name not in compiled:continue
        for m in re.findall(r'^\s*module\s+(\w+)',f.read_text(),re.M):bymodule[m]=f
    shared_all={}
    for n,h in rr['rtl_hashes'].items():
        text=read(ref/n);assert PINS[str(ref/n)]==h,n
        modules=re.findall(r'^\s*module\s+(\w+)',text,re.M)
        for m in modules:
            if m in bymodule:
                read(bymodule[m]);assert PINS[str(bymodule[m])]==h,(n,m)
                shared_all[m]=h
    log=read(ref/'vsim.log')
    assert 'Errors: 0, Warnings: 0' in log
    counts=re.search(r'CAPTURE365 input_core=(\d+) replies=(\d+)',log)
    core_requests,core_replies=map(int,counts.groups());assert core_requests==core_replies and core_requests>0
    assert 'CADENCE366 attempts=2 admitted=2 missed=0' in log
    oldlog=read(negative/'vsim.log');assert 'CADENCE365 attempts=2 admitted=1 missed=1' in oldlog
    guards=data(b/'guards04/result.json');raw=data(b/'rawguards02/result.json')
    assert guards['passed'] and guards['guards']==22 and raw['passed'] and raw['cases']==3
    assert guards['pins']['nes_native_capture365.sv']==hashes['nes_native_capture365.sv']
    assert raw['pins']['nes_core257.sv']==hashes['nes_core257.sv']
    read(b/'guards04/vsim.log');read(b/'rawguards02/vsim.log')
    ev=events(ref);ce=events(control);rows=[]
    for f in range(905,909):
        start=event(ev,'start319',f);end=event(ev,'frame_done',f);commit=event(ev,'input_done337',f);seal=event(ev,'materialized366',f)
        s=int(start[2]);end_time=int(end[2]);seal_time=int(seal[3]);commit_time=int(commit[3])
        assert s<seal_time<commit_time<end_time
        row=dict(frame=f,source_start_ROM_cycle=int(start[3]),read_handoff_ms=(seal_time-s)/1e9,
                 input_commit_ms=(commit_time-s)/1e9,processing_ms=(end_time-s)/1e9,
                 output_after_commit_ms=(end_time-commit_time)/1e9,
                 excess_60Hz_ms=max(0,(end_time-s)/1e9-1000/60))
        if f==907:
            cs=int(event(ce,'start319',f)[2]);cf=int(event(ce,'frame_done',f)[2])
            row['before365_processing_ms']=(cf-cs)/1e9
            row['delta_vs365_ms']=row['processing_ms']-row['before365_processing_ms']
        rows.append(row)
    attempts=[]
    for x in ev:
        if x[0]=='capture_attempt366':
            assert x[2:4]==['0','1']
            frame=int(x[1]);s=int(event(ev,'start319',frame-1)[2]);seal=int(event(ev,'materialized366',frame-1)[3]);commit=int(event(ev,'input_done337',frame-1)[3]);t=int(x[5])
            attempts.append(dict(frame=frame,collector_owned_at_start=0,admitted=True,native_generation_before_start=int(x[4]),
                                 time_after_prior_source_start_ms=(t-s)/1e9,
                                 handoff_margin_ms=(t-seal)/1e9,
                                 input_ACK_after_capture_start_ms=(commit-t)/1e9))
            assert seal<t<commit,(frame,'overlap not exercised')
    assert [x['frame'] for x in attempts]==[908,909]
    costs={'362_reference':dict(LE=22733,comb=17724,FF=9179,RAM_bits=308832),'365_start_fix':whole(b/'map01'),'366_selected':whole(board)}
    selected=costs['366_selected'];delta={k:selected[k]-costs['362_reference'][k] for k in selected}
    tb=read(ref/'joint266_tb.sv')
    assert 'if(hf337==907&&!sent361)' in tb
    result=dict(stage='365-366',passed=True,merged_PR131='914138969246387162bf2c909159824e72a3666d',
                branch='codex/nes-capture-admission-365',selected_run='early03',selected_MAP='map03',
                shared_boundary=hashes,all_shared_modules=shared_all,
                normal_functional_frames=4,continuous_next_capture_attempts=attempts,
                control_missed_capture_count=1,selected_missed_capture_count=0,
                source_queries_after_handoff=0,source_query_claim='Asserted by RTL TB for all4 frames; actual core raw0/1/2 directed guards also pass.',
                input_ROM_core_requests=core_requests,input_ROM_core_replies=core_replies,
                core_ROM_workload='Declared ready-gated period120 NES clocks at001234 during input AND output; returned bytes/physical priority checked. Not a live NES CPU trace.',
                timing=rows,whole_MAP=costs,whole_delta_vs362=delta,
                comb_device_limit=15408,comb_deficit=selected['comb']-15408,
                deletion_needed_with155_reserve=selected['comb']-15253,
                session_guards=22,source_raw_lifetime_guards=3,
                actual_ARM_output=True,actual_ARM_source='Measured per-block M4 source receive/decode costs, exact bytes checked; not full firmware foreground/preemption.',
                actual65816='Existing ordinary-command bus traces replayed. Map DMA and final display ACK are bus models; unchanged VBlank firmware is not a new full65816 proof.',
                IRQ_entry_exit='Declared allocations plus real handler instruction counts, not measured hardware WCET.',
                prefetch_scope='BG5/OBJ2 hint is causally produced only for907 in this harness.908 has no new hint; its ROM/output wait is NOT a general per-frame prefetch result.',
                source_to_display_identity='Current collector may advance; admitted epoch/generation/serial frozen through final display ACK plus drained plan retirement.',
                FIT=False,STA=False,physical=False,sustained60fps=False,
                conclusion='Start join repaired and two bounded next-capture deadlines met without extra RAM.908 still exceeds display budget; extend causal hint foreground and whole continuous coverage before area architecture changes.',
                pins=PINS)
    (ROOT/'analysis/capture365-verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps({k:result[k] for k in ['timing','continuous_next_capture_attempts','whole_delta_vs362','comb_deficit']},ensure_ascii=False,indent=2))
    print(f'PASS: {len(shared_all)} shared module identities,22 session guards,raw0/1/2,2 capture deadlines; {len(PINS)} pins.')

if __name__=='__main__':main()
