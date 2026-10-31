# SPDX-License-Identifier: MIT
"""Bind506 RTL/linked ARM/CPU/whole Lite evidence without a physical-FPS claim."""
import argparse,csv,json,re,struct
from pathlib import Path
from check_nes_game478 import sha
from nes_raw506 import encode
from test_nes_raw506_joint import MASTER
ROOT=Path(__file__).resolve().parents[1]

def read(p):return json.loads(p.read_text(encoding='utf8'))
def ms(t):return t/MASTER*1000

def schedule(d):
    r=read(d/'joint.json');assert r['passed'] and r['commits']==12
    assert r['future_ACK_filtered'] and not r['atomic_DMA_overshoot_charged_to_ARM']
    assert r['native_service_code_executed'] and r['max_bulk_banks']<=2
    events=read(d/'events.json');rows=[]
    for frame in r['frames']:
        g=frame['generation'];e=[x for x in events if x['generation']==g];start=next(x for x in e if x['event']=='source_begin')
        spi=[x for x in e if x['event']=='SPI'];first_bg=next(x for x in spi if x['opcode']=='0xe9')
        first_bulk=next((x for x in spi if x['opcode']=='0xe1' and x['packet_opcode']==7),None)
        seal=next(x for x in spi if x['opcode']=='0xe1' and x['packet_opcode']==3)
        row=dict(generation=g,source_begin=start['clock'],capture_ready=start['capture_ready'],first_BG_E9=first_bg['start'],first_bulk_E1=None if first_bulk is None else first_bulk['start'],SEAL_E1_end=seal['clock'],final_ACK=frame['ACK_masterclock'],source_to_ACK_ms=ms(frame['ACK_masterclock']-start['clock']),ready_to_first_BG_ms=ms(first_bg['start']-max(start['clock'],start['capture_ready'])),SEAL_to_ACK_ms=ms(frame['ACK_masterclock']-seal['clock']),wire_B={})
        for x in spi:row['wire_B'][x['opcode']]=row['wire_B'].get(x['opcode'],0)+x['bytes']
        rows.append(row)
    return r,rows

def analyze(a):
    a.out.mkdir(parents=True,exist_ok=False)
    arm=read(a.work/'arm-test02/result.json');guards=read(a.work/'guards01/result.json');clock=read(a.work/'clock01/result.json');rtl=read(a.rtl/'result.json')
    assert arm['passed'] and guards['passed'] and clock['passed'] and rtl['passed']
    words={}
    for x in csv.DictReader((a.rtl/'records.csv').open()):
        g=int(x['generation'])
        if not 905<=g<=916:continue
        w=int(x['word'],16);kind=w>>93;index=(w>>64)&8191;gen=(w>>77)&65535;value=w&((1<<64)-1)
        width=8 if kind==0 and index&4096 else [2,1,7,4,7,1,2,8][kind]
        words.setdefault(g,bytearray()).extend(struct.pack('>HH',kind<<13|index,gen)+value.to_bytes(width,'big'))
    binding=[]
    for g,b in sorted(words.items()):
        packets,_,_=encode((a.data/f'frame{g}.geometry').read_bytes(),(a.data/f'frame{g}.raw').read_bytes(),g)
        assert b==b''.join(packets);binding.append(dict(generation=g,bytes=len(b),exact=True))
    assert len(binding)==12
    old,oldrows=schedule(a.baseline);new,newrows=schedule(a.candidate)
    assert old['firmware_SHA256']==arm['baseline_firmware']==read(ROOT/'analysis/capture502-release-verification.json')['ARM']['firmware_SHA256']
    assert old['parameters']==new['parameters'] and old['client_SHA256']==new['client_SHA256']
    assert old['vram_DMA_B']==new['vram_DMA_B'] and old['ROM_read_allocations']==new['ROM_read_allocations']
    pairs=[]
    for b,c in zip(oldrows,newrows):
        g=b['generation'];assert c['generation']==g
        assert sha(a.baseline/f'frame-{g}.rgb')==sha(a.candidate/f'frame-{g}.rgb'),g
        pairs.append(dict(generation=g,baseline=b,candidate=c,absolute_ACK_delta_ms=ms(c['final_ACK']-b['final_ACK']),source_to_ACK_delta_ms=c['source_to_ACK_ms']-b['source_to_ACK_ms'],ready_to_first_BG_delta_ms=c['ready_to_first_BG_ms']-b['ready_to_first_BG_ms']))
    first0=oldrows[0]['final_ACK'];first1=newrows[0]['final_ACK'];last0=oldrows[-1]['final_ACK'];last1=newrows[-1]['final_ACK'];second0=oldrows[1]['final_ACK'];second1=newrows[1]['final_ACK']
    common=dict(parameters=old['parameters'],frames=pairs,exact_RGB_frames=12,VRAM_DMA_B=new['vram_DMA_B'],ROM_read_allocations=new['ROM_read_allocations'],baseline_wire_B=old['wire_B'],candidate_wire_B=new['wire_B'],whole_ACK_delta_ms=ms(last1-last0),after_first_11=dict(baseline_ms=ms(last0-first0),candidate_ms=ms(last1-first1),delta_ms=ms((last1-first1)-(last0-first0))),after_two_initial_banks_10=dict(baseline_ms=ms(last0-second0),candidate_ms=ms(last1-second1),delta_ms=ms((last1-second1)-(last0-second0))),SysTick_calls=[old['SysTick_calls'],new['SysTick_calls']],SysTick_instructions=[old['SysTick_instructions'],new['SysTick_instructions']],max_emulator_overshoot=[old['max_rendezvous_rounding'],new['max_rendezvous_rounding']],overshoot_added_to_ARM=False,future_ACK_filtered=True,native_service_code_executed=True,observed_ARM_SP_low=[old['observed_stack_low'],new['observed_stack_low']],scope='Actual linked M4 runtime/service/SysTick and489 CPU; measured mean SPI driver overhead plus CPI/ROM-density/capture replay models. Not physical cycles or whole NES/PSRAM RTL.')
    fit=(a.board/'output_files/board.fit.summary').read_text(errors='replace');fullfit=(a.board/'output_files/board.fit.rpt').read_text(errors='replace')
    assert 'Fitter Status : Successful' in fit
    num=lambda pattern,text:int(re.search(pattern,text)[1].replace(',',''))
    area=dict(LE=num(r'Total logic elements\s*:\s*([\d,]+)',fit),comb=num(r'Total combinational functions\s*:\s*([\d,]+)',fit),FF=num(r'Dedicated logic registers\s*:\s*([\d,]+)',fit),RAM_bits=num(r'Total memory bits\s*:\s*([\d,]+)',fit),M9K=num(r'; M9Ks\s*;\s*(\d+)',fullfit))
    area['remaining_LE']=15408-area['LE'];area['baseline']={k:read(ROOT/'analysis/capture502-verification.json')['FPGA'][k]for k in area}
    area['delta']={k:area[k]-area['baseline'][k]for k in area['baseline']}
    views={}
    for view in ['implementation','nominal']:
        rows=list(csv.DictReader((a.board/f'{view}-paths204.tsv').open(),delimiter='\t'))
        related=[x for x in rows if (x['from_clock']=='nes')==(x['to_clock']=='nes')]
        views[view]={k:min((x for x in related if x['kind']==k),key=lambda x:float(x['slack']))for k in ['setup','hold']}
    timing_ok=all(float(x['slack'])>=0 for v in views.values()for x in v.values())
    pins=read(a.board/'source-pins.json');assert pins['changed']==['nes_native_export203.sv']
    for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
    prep=read(a.work/'candidate01/prepare.json');assert sha(a.board/'nes_native_export203.sv')==prep['exporter_SHA256']
    fw=a.work/'ARM02/src/obj-nes-100/firmware.stm';assert sha(fw)==arm['candidate_firmware']==new['firmware_SHA256']
    before=[x['baseline']['receive_instructions'] for x in arm['rows']];after=[x['candidate']['receive_instructions']for x in arm['rows']]
    for x in arm['rows']:
        assert x['baseline']['planner_instructions']==x['candidate']['planner_instructions']
        assert x['baseline']['serializer_instructions']==x['candidate']['serializer_instructions']
    report=dict(experiment=506,baseline='MMC502',PR=140,physical_FPS=10.59,new_physical_FPS=None,new_installer=False,production_selected=False,functional_passed=True,whole_timing_passed=timing_ok,full_60Hz_passed=False,wire_version='2233',raw_expansion='exact span validation once into final array;no per-pixel logical_record call',persistent_RAM_added_B=0,source_RTL=dict(result=rtl,RTL_to_ARM_exact_wire=binding,warnings='rtl02 zero warnings;rtl01 unconnected busy/ack_ready outputs preserved'),ARM=dict(firmware_SHA256=sha(fw),firmware_B=fw.stat().st_size,Flash_remaining_B=212992-fw.stat().st_size,firmware_delta_B=fw.stat().st_size-212844,BSS_B=18572,receive_instruction_savings=[b-c for b,c in zip(before,after)],decoder_cases=len(arm['guards']),additional_input_guards=guards['rows'],linked_unit_rows=arm['rows']),clock_guard=clock,common_schedule=common,FPGA=dict(cost=area,related_clock_paths=views,input_files=len(pins['board_inputs']),changed=pins['changed'],source_inputs=pins['board_inputs'],timing_support_SHA256=sha(a.board/'nominal204.sdc')),decision='Preserve MMC502. Exact compression is a candidate, not a delivery: whole-board setup regression remains.',limits=['ROM safe slots and core-safe density are modeled;fixed captured frames/tile results do not execute full NES/PSRAM competition.','CPI2 is sensitivity, not measured M4 cycles. Driver means include original IRQ; explicit SysTick is conservatively charged at callback boundaries.','GPIO/context and observer/screen peripheral responses are healthy stubs;their measured SPI intervals are charged. No new physical menu-return test.','Capture eligibility follows201 COMMIT/EA ownership, but capture rejection/missed-frame rate is not replayed.','One identical initial ROM phase,continuous twelve-frame schedule;not a universal phase or mapper bound.','Source export record bytes are RTL-bound separately;full source/SPI CDC timing is not on this common emulator clock.','Full reset/CDC/IO timing approval is not asserted.'],excluded_trials={'arm-test01':'Transport token/status CRC differed with packet count; semantic comparison corrected without weakening coverage checks.','ARM01':'subst mapping sandbox denial; ARM02 is selected.','joint01_02':'Endpoint incorrectly returned END flags3;actual ARM rejected retire.','joint03_04':'Windows reply sharing failure; bounded access-denied retry added.','joint05_06':'Functional twelve-frame evidence only: DMA atomic overshoot charged to ARM and capture incorrectly delayed to EA. Timing excluded.','joint07_10_and12':'Initial emulator RPC watchdog,not Questa/firmware failure;raw logs preserved.','first_nominal_STA':'Missing nominal support file;corrected STA on same fitted DB,no refit.'})
    evidence=[a.work/'arm-test02/result.json',a.work/'guards01/result.json',a.work/'clock01/result.json',a.rtl/'result.json',a.rtl/'records.csv',a.rtl/'sim.log',a.baseline/'joint.json',a.baseline/'events.json',a.candidate/'joint.json',a.candidate/'events.json',a.board/'output_files/board.fit.summary',a.board/'output_files/board.fit.rpt',a.board/'output_files/board.map.summary',a.board/'flow.log',a.board/'timing506-corrected.log',a.board/'implementation-paths204.tsv',a.board/'nominal-paths204.tsv']
    report['evidence_SHA256']={str(p.resolve()):sha(p)for p in evidence}
    (a.out/'result.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(functional_passed=True,timing_passed=timing_ok,whole_ACK_delta_ms=common['whole_ACK_delta_ms'],after_first=common['after_first_11'],after_two=common['after_two_initial_banks_10'],FPGA=area),ensure_ascii=False))
    return report

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['work','rtl','board','data','baseline','candidate','out']:p.add_argument('--'+n,type=Path,required=True)
    analyze(p.parse_args())
