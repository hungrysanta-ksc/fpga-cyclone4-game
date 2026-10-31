# SPDX-License-Identifier: MIT
"""Bind507 same-edge loader repair and unchanged506 schedule observations."""
import argparse,csv,json,re,statistics
from pathlib import Path
from check_nes_game478 import sha
ROOT=Path(__file__).resolve().parents[1]
MASTER=21477272
def read(p):return json.loads(p.read_text(encoding='utf8'))
def ms(n):return n/MASTER*1000
def overlap(a,b,c,d):return max(0,min(b,d)-max(a,c))

def analyze(a):
    a.out.mkdir(parents=True,exist_ok=False)
    test=read(a.test/'result.json');trace=read(a.trace/'trace507.json');joint=read(a.trace/'joint.json');events=read(a.trace/'events.json')
    assert test['passed'] and trace['passed'] and trace['unchanged_schedule']
    pins=read(a.board/'source-pins.json');assert pins['changed']==['nes_rom_spi.sv']
    for n,h in pins['board_inputs'].items():assert sha(a.board/n)==h,n
    assert test['candidate_SHA256']==sha(a.board/'nes_rom_spi.sv')
    old=read(ROOT/'analysis/raw506-verification.json')
    assert test['baseline_SHA256']==old['FPGA']['source_inputs']['nes_rom_spi.sv']
    assert sha(a.board/'nominal204.sdc')==sha(a.baseline_board/'nominal204.sdc')==old['FPGA']['timing_support_SHA256']
    assert joint['firmware_SHA256']==old['ARM']['firmware_SHA256']
    assert joint['parameters']==old['common_schedule']['parameters']
    assert len(trace['ROM_model_slots'])==joint['ROM_read_allocations']==3280
    fit=(a.board/'output_files/board.fit.summary').read_text(errors='replace')
    full=(a.board/'output_files/board.fit.rpt').read_text(errors='replace')
    assert 'Fitter Status : Successful' in fit
    num=lambda p,s:int(re.search(p,s)[1].replace(',',''))
    area=dict(LE=num(r'Total logic elements\s*:\s*([\d,]+)',fit),comb=num(r'Total combinational functions\s*:\s*([\d,]+)',fit),FF=num(r'Dedicated logic registers\s*:\s*([\d,]+)',fit),RAM_bits=num(r'Total memory bits\s*:\s*([\d,]+)',fit),M9K=num(r'; M9Ks\s*;\s*(\d+)',full))
    views={}
    for v in ['implementation','nominal']:
        rows=list(csv.DictReader((a.board/f'{v}-paths204.tsv').open(),delimiter='\t'))
        related=[x for x in rows if(x['from_clock']=='nes')==(x['to_clock']=='nes')]
        views[v]={k:min((x for x in related if x['kind']==k),key=lambda x:float(x['slack']))for k in ['setup','hold']}
    timing_ok=all(float(x['slack'])>=0 for v in views.values()for x in v.values())
    stages=[];windows=[]
    for g in range(905,917):
        e=[x for x in events if x['generation']==g and x['event']=='SPI']
        spans=[x for x in trace['intervals']if x['generation']==g];assert len(spans)==3
        slots=[x for x in trace['ROM_model_slots']if x['generation']==g]
        for x in spans:
            start,end=x['start'],x['end'];assert start<=end
            spi=sum(overlap(start,end,y['start'],y['clock'])for y in e)
            rom=sum(overlap(start,end,y['requested'],y['completed']-7)for y in slots)
            stages.append(dict(generation=g,name=x['name'],inclusive_ms=ms(end-start),SPI_nested_ms=ms(spi),ROM_wait_overlap_ms=ms(rom)))
        finish=next(x for x in spans if x['name']=='nes_plan200_finish')
        last_e9=max(x['clock']for x in e if x['opcode']=='0xe9')
        ordinary=[x for x in e if x['opcode']=='0xe1'and x['packet_opcode']not in [1,7,3]]
        seal=next(x for x in e if x['opcode']=='0xe1'and x['packet_opcode']==3)
        assert finish['start']<=last_e9<=finish['end']<=ordinary[0]['start']
        windows.append(dict(generation=g,END_to_finish_return_ms=ms(finish['end']-last_e9),finish_return_to_ordinary_ms=ms(ordinary[0]['start']-finish['end']),END_to_ordinary_ms=ms(ordinary[0]['start']-last_e9),ordinary_to_SEAL_ms=ms(seal['start']-ordinary[0]['start']),ordinary_B=sum(x['bytes']for x in ordinary),ordinary_packets=len(ordinary)))
    steady=[x for x in windows if x['generation']>=907]
    summary={k:dict(mean=statistics.mean(x[k]for x in steady),min=min(x[k]for x in steady),max=max(x[k]for x in steady))for k in ['END_to_finish_return_ms','finish_return_to_ordinary_ms','END_to_ordinary_ms','ordinary_to_SEAL_ms']}
    evidence=[a.test/'result.json',a.test/'normal.log',a.test/'priority-mutant.log',a.trace/'trace507.json',a.trace/'joint.json',a.trace/'events.json',a.board/'source-pins.json',a.board/'flow507.log',a.board/'timing507.log',a.board/'output_files/board.fit.summary',a.board/'implementation-paths204.tsv',a.board/'nominal-paths204.tsv',a.board/'loader507-original.rpt']
    evidence += [a.baseline_board/'loader507-original.rpt',a.board/'nominal204.sdc']
    r=dict(experiment=507,PR=140,baseline_physical='MMC502',physical_FPS=10.59,new_physical_FPS=None,new_installer=False,functional_passed=True,related_timing_passed=timing_ok,full_reset_CDC_IO_approved=False,FPGA=dict(cost=area,delta_vs506={k:area[k]-old['FPGA']['cost'][k]for k in area},remaining_LE=15408-area['LE'],related_paths=views,source_inputs=pins['board_inputs']),test=test,ARM_firmware_SHA256=joint['firmware_SHA256'],ARM_changed=False,SNES_changed=False,additional_state_bits=0,extra_error_latency_clocks=0,observation=dict(unchanged_schedule=True,intervals=stages,windows=windows,after_two_initial_banks=summary,ROM_read_allocations=len(trace['ROM_model_slots']),scope='Actual linked M4 and489 CPU; unchanged506 explicit CPI/SPI-mean/ROM-slot model. Not actual NES arbiter trace or measured physical cycles. Nested SPI and overlapping ROM intervals must not be added to inclusive time.'),next_boundary=dict(candidate='Bounded ordinary submission after END accepted, before all tile consumption;bulk ready/credit first',required_replacement='complete485 cannot use window.last opcode7 when ordinary interleaves. Use validated retired counter and a bounded bulk watermark;retain every endpoint ACK check and final full identity check.',budget=dict(extra_ARM_static_B=0,extra_runtime_struct_max_B=8,extra_ARM_Flash_max_B=140,extra_FPGA_M9K=0,extra_FPGA_control=0,measured=False),gates=['Finite4ordinary/2bulk;one bounded ordinary packet per service turn;no reentrant SPI','Generation/serial/sequence wrap,stale or future completion,STOP during partial ordinary invalidate tentative state','SEAL only after all tile and ordinary consumption;final ACK thenEA;old displayed identity unchanged','Real arbiter trace and long continuous same-phase comparison before performance claim']),evidence_SHA256={str(p.resolve()):sha(p)for p in evidence})
    for n in ['nes_native_runtime165.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_window184.c','nes_native_video165.h']:
        r.setdefault('ARM_source_inputs',{})[n]=sha(a.arm/n)
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(timing_passed=timing_ok,area=area,steady=summary)))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['board','baseline-board','test','trace','arm','out']:p.add_argument('--'+n,type=Path,required=True)
    analyze(p.parse_args())
