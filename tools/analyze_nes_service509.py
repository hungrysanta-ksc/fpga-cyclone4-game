# SPDX-License-Identifier: MIT
"""509 evidence: shared E8, exact nominal comparison and boot-trace sensitivity."""
import argparse,json,statistics
from pathlib import Path
from analyze_nes_overlap508 import read,cost,ms,sha,ROOT
def compare(reference,candidate):
    b=read(reference/'joint.json');c=read(candidate/'joint.json')
    assert b['passed']and c['passed']and b['parameters']==c['parameters']
    assert b['client_SHA256']==c['client_SHA256']and b['commits']==c['commits']==12
    assert b['vram_DMA_B']==c['vram_DMA_B']==36144 and b['ROM_read_allocations']==c['ROM_read_allocations']==3280
    rows=[]
    for x,y in zip(b['frames'],c['frames']):
        g=x['generation'];assert g==y['generation'];assert sha(reference/f'frame-{g}.rgb')==sha(candidate/f'frame-{g}.rgb'),g
        rows.append(dict(generation=g,ACK_delta_ms=ms(y['ACK_masterclock']-x['ACK_masterclock']),RGB_SHA256=sha(candidate/f'frame-{g}.rgb')))
    windows={}
    for start,label in [(0,'after_first_11'),(1,'after_two_10')]:
        old=ms(b['frames'][-1]['ACK_masterclock']-b['frames'][start]['ACK_masterclock']);new=ms(c['frames'][-1]['ACK_masterclock']-c['frames'][start]['ACK_masterclock'])
        windows[label]=dict(reference_ms=old,candidate_ms=new,delta_ms=new-old,reduction_percent=(old-new)/old*100)
    assert int(c['observed_stack_low'],16)>int(c['workspace_end'],16)and c['max_bulk_banks']<=2
    return dict(parameters=c['parameters'],windows=windows,frames=rows,reference_Firmware_SHA256=b['firmware_SHA256'],candidate_Firmware_SHA256=c['firmware_SHA256'],reference_wire_B=sum(b['wire_B'].values()),candidate_wire_B=sum(c['wire_B'].values()),instruction_delta=c['ARM_instructions']-b['ARM_instructions'],candidate_stack_low=c['observed_stack_low'],workspace_end=c['workspace_end'],stack_gap_B=int(c['observed_stack_low'],16)-int(c['workspace_end'],16),max_bulk_banks=c['max_bulk_banks'],reference_SHA256=sha(reference/'joint.json'),candidate_SHA256=sha(candidate/'joint.json'))
def analyze(a):
    a.out.mkdir(parents=True,exist_ok=False)
    guards=read(a.guards/'result.json');parity=read(a.parity/'result.json');rom=read(a.rom/'result.json')
    assert guards['passed']and parity['passed']and parity['cases']==40 and rom['passed']
    nominal=compare(a.reference,a.nominal);pressure=compare(a.trace_reference,a.trace_candidate)
    assert pressure['reference_Firmware_SHA256']=='28a4b1655caddca6515529726ac549d28e1d47539dd293bca1ce2fb1112fbe7e'
    arm=cost(a.arm);old=cost(a.baseline_arm)
    assert arm['firmware_SHA256']==guards['firmware_SHA256']==parity['candidate_SHA256']==nominal['candidate_Firmware_SHA256']==pressure['candidate_Firmware_SHA256']
    assert parity['baseline_SHA256']==nominal['reference_Firmware_SHA256']==old['firmware_SHA256']
    for n,h in rom['source_pins'].items():
        if n not in ['prg.hex','chr.hex']:assert sha(a.board/n)==h,n
    board=read(ROOT/'analysis/fault507-verification.json')
    for n,h in board['FPGA']['source_inputs'].items():assert sha(a.board/n)==h,n
    assert arm['Flash_remaining_B']>0 and arm['BSS_B']==old['BSS_B']
    starts={};latencies=[];pending=None
    for line in (a.rom/'fill1/rom.tsv').read_text().splitlines():
        k,t,f,y,x,addr=line.split();t=int(t);f=int(f)
        if k=='G':assert pending is None;pending=t;starts.setdefault(f,[]).append(t)
        else:assert pending is not None;latencies.append(t-pending);pending=None
    assert pending is None
    gaps=[b-a for ts in starts.values()for a,b in zip(ts,ts[1:])]
    r=dict(experiment=509,PR=140,baseline_physical='MMC502',physical_FPS=10.59,new_physical_FPS=None,limited_delivery_gate='analysis/service509-release.json',functional_passed=True,ARM=dict(reference=old,candidate=arm,delta={k:arm[k]-old[k]for k in ['firmware_B','text_B','data_B','BSS_B']},source_SHA256=sha(a.arm/'src/nes_plan_service200.c')),guards=guards,phase_parity=parity,nominal_vs508=nominal,boot_trace_sensitivity_vs506=pressure,ROM=dict(test=rom,transactions=sum(map(len,starts.values())),grants_per_frame={str(k):len(v)for k,v in starts.items()},return_latency_clocks=sorted(set(latencies)),within_window_gap_clocks=dict(min=min(gaps),median=statistics.median(gaps),max=max(gaps)),periodic_replay=True,matched_first_level=False,closed_loop_ARM_NES=False),FPGA=dict(changed=False,new_Quartus_run=False,cost=board['FPGA']['cost'],related_paths=board['FPGA']['related_paths'],full_reset_CDC_IO_approved=False),SNES_changed=False,limitations=['Actual20-frame boot core/ROM contention,not the905..916 game workload','Eight boot windows periodically replayed into M4/65816 sensitivity;not live core feedback or source-byte-cadence proof','CPI and SPI means remain model inputs;no new physical FPS/menu test/capture rejection rate','36B Flash headroom;limited trial needs separate artifact/label/programmer gates and physical gameplay confirmation'])
    r['evidence_SHA256']={name:sha(p)for name,p in [('rom_test',a.rom/'result.json'),('guards',a.guards/'result.json'),('parity',a.parity/'result.json'),('recipe',ROOT/'tools/nes_service509.py'),('trace_tool',ROOT/'tools/trace_nes_service509_rom.py'),('schedule_tool',ROOT/'tools/test_nes_service509_schedule.py')]}
    (a.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,Flash=arm['Flash_remaining_B'],nominal=nominal['windows'],pressure=pressure['windows'],ROM=r['ROM']['within_window_gap_clocks'])))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','baseline-arm','guards','parity','rom','board','reference','nominal','trace-reference','trace-candidate','out']:p.add_argument('--'+n,type=Path,required=True)
    analyze(p.parse_args())
