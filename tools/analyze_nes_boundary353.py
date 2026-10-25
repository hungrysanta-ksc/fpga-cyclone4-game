# SPDX-License-Identifier: MIT
"""Measured preparation/port review; budgets are not synthesized savings."""
import argparse,collections,csv,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from analyze_nes_receipt335 import load_image

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',type=Path,default=BASE/'probes/nes-boundary353');a=ap.parse_args();pins={}
    def read(p):pins[str(p)]=sha(p);return p.read_text(encoding='utf-8-sig')
    def js(p):return json.loads(read(p))
    base=js(ROOT/'analysis/raw352-verification.json')
    for n,h in base['pins'].items():assert sha(Path(n))==h,n;pins[n]=h
    d=a.root/'fixed01';b=BASE/'probes/nes-raw352/fixed02';r=js(d/'result.json');br=js(b/'result.json')
    assert r['passed'] and r['rtl_hashes']==br['rtl_hashes'] and r['ARM']==br['ARM']
    assert load_image(d/'output.elf')==load_image(b/'output.elf');pins[str(d/'output.elf')]=sha(d/'output.elf')
    for n,h in r['rtl_hashes'].items():assert sha(d/n)==h;read(d/n)
    for n in ('joint-events.csv','cycles.csv','blocks.txt','calls337.json','metadata317.json','source-cost280.hex'):
        assert sha(d/n)==sha(b/n),(n,'passive trace changed baseline');read(d/n)
    assert 'PASS REFILL267 frames=3' in read(d/'vsim.log') and 'Errors: 0, Warnings: 0' in read(d/'vlog.log')
    trace=list(csv.DictReader(read(d/'boundary353.csv').splitlines()));rows=[]
    for f in (905,906,907):
        tr=[x for x in trace if x['frame']==str(f)];n=[x for x in tr if x['domain']=='N'];h=[x for x in tr if x['domain']=='H']
        pending=None;latencies=collections.Counter()
        for x in n:
            if x['response']=='1':assert pending is not None;latencies[int(x['time'])-pending]+=1;pending=None
            if x['query']=='1':assert pending is None;pending=int(x['time'])
        assert pending is None
        aw=[x for x in n if x['we']=='1'];bw=[x for x in h if x['we']=='1'];steps=[x for x in n if x['plan_step']=='1'];zeros=[x for x in n if x['plan_zero']=='1']
        assert all(x['phase']=='0' and 512<=int(x['addr'])<1024 for x in aw)
        assert all(x['phase']=='1' for x in steps+zeros)
        hi=0;concurrent=0
        for x in steps:
            while hi+1<len(h) and int(h[hi+1]['time'])<=int(x['time']):hi+=1
            if h and int(h[hi]['time'])<=int(x['time']) and h[hi]['state'] not in ('0','16'):concurrent+=1
        rows.append(dict(frame=f,queries=sum(latencies.values()),query_latency_observed_ps=dict(latencies),source_A_writes=len(aw),first_source_A_write_ps=min(int(x['time']) for x in aw),last_input_phase_B_write_ps=max([int(x['time']) for x in bw if x['phase']=='0'],default=None),validator_B_writes=len(bw),validator_B_input_phase_writes=sum(x['phase']=='0' for x in bw),source_A_address_min=min(int(x['addr']) for x in aw),source_A_address_max=max(int(x['addr']) for x in aw),plan_steps=len(steps),plan_resets=len(zeros),plan_steps_while_host_busy=concurrent,queue_writes=sum(x['queue_write']=='1' for x in h)))
    profile=js(a.root/'arm03/result.json');assert profile['passed']
    for n,h in profile['pins'].items():assert sha(Path(n))==h;pins[n]=h
    measured=[]
    for tag,ref in [('window02','window02'),('fixed02','fixed02'),('normal02','normal02')]:
        q=BASE/'probes/nes-raw352'/tag;ev=list(csv.reader(read(q/'joint-events.csv').splitlines()));e=[x for x in ev if len(x)>1 and x[1]=='907']
        req=int(next(x for x in e if x[0]=='firstreq305' and x[2]=='0')[-1]);done=int(next(x for x in e if x[0]=='input_done337')[-1])
        completed=[x for x in e if x[0]=='arm267' and int(x[4])<req];checks=[x for x in e if x[0]=='checkpoint287' and int(x[2])<req];waits=[x for x in e if x[0]=='wait284' and int(x[3])<req]
        inst=sum(int(x[5]) for x in completed)+sum(int(x[3]) for x in checks)+sum(int(x[4]) for x in waits)
        exceptions=sum(int(x[6]) for x in completed)+sum(int(x[5]) for x in waits);wireps=0
        for x in completed:
            start=max(int(y[-1]) for y in e if y[0]=='ARM_wire_start334' and int(y[-1])<int(x[4]));wireps+=int(x[4])-start
        before=(req-done)/1e9;cpu=(inst+exceptions)/84000
        measured.append(dict(mode=tag,baseline=base['runs'][ref]['rows'][-1],source_done_to_request_ms=before,ARM_instructions=inst,exception_cycles=exceptions,ARM_ms=cpu,SPI_ms=wireps/1e9,residual_ms=before-cpu-wireps/1e9,checkpoints=len(checks),waits=len(waits)))
    warm=[x for x in profile['rows'] if x['frame']==907]
    mem=sum(x['exclusive_function_instructions'].get('memcpy',0)+x['exclusive_function_instructions'].get('memset',0) for x in warm)
    assert mem==33530
    budget=dict(whole=base['whole'],comb_deficit=1866,whole_cap=15253,required_net_deletion=2021,source_host_cap_including_new_CDC=2035,queue_SPI_cap=650,retained_plan=459,retained_checker_aperture=1159,outside=10950,new_bridge_comb=None,new_engine_comb=None,synthesized_saving=0)
    # Declared storage in the existing mailbox: two WIDTH words, twelve
    # synchronizer/release bits and four protocol bits. Not a MAP estimate.
    cdc=dict(request_width=32,response_width=65,new_mailbox_declared_bits=2*(32+65)+2*16,old_source_mailbox_declared_bits=2*(2*40+16)+(2*17+16),NES_plan_cursor_retained_bits=10,scope='Structural storage inventory only; aliases/constant pruning and new phase/lease control unmeasured. No FF-to-comb conversion or area claim.')
    critical=dict(first_BG_advance_needed_ms=1.128168,minimum_net_ARM_instructions_at_CPI1=94767,initial_prepare_instructions=167639,three_preparation_calls_instructions=sum(x['instructions'] for x in warm),memory_routine_impossible_free_upper_bound_ms=mem/84000,remaining_after_free_memory_ms=1.128168-mem/84000,post_ROM_gap_ms=0.653568)
    # Preserve the prior frontier counterexample rather than proposing it anew.
    for n in ('docs/nes-frontier342-contract.ko.md','docs/nes-record344-contract.ko.md','tools/probe_nes_boundary353.py','tools/profile_nes_prepare353.py','tools/analyze_nes_boundary353.py'):read(ROOT/n)
    result=dict(stage=353,passed=True,selected_RTL=338,selected_ARM=352,passive_observations=3,reused_schedule_observations=9,unique_frames=3,ports=rows,preparation=profile,measured_schedules=measured,critical_budget=critical,whole_budget=budget,CDC_inventory=cdc,RTL_and_ARM_load_image_unchanged=True,original_timeline_byte_exact=True,new_RTL=False,new_ARM=False,new_MAP=False,FIT=False,STA=False,physical=False,pins=pins)
    (ROOT/'analysis/boundary353-verification.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')
    print(json.dumps(dict(passed=True,ports=rows,critical=critical,CDC=cdc,first_BG=measured,pins=len(pins)),indent=2))
if __name__=='__main__':main()
