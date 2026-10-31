# SPDX-License-Identifier: MIT
"""Bind508 actual ARM costs and same-phase linked M4/65816 schedule."""
import argparse,json,re
from pathlib import Path
from check_nes_supply485_arm import ELFFile,sha
ROOT=Path(__file__).resolve().parents[1]
MASTER=21477272
def read(p):return json.loads(p.read_text(encoding='utf8'))
def ms(v):return v*1000/MASTER
def cost(folder):
    src=folder/'src';r=dict(firmware_B=(src/'obj-nes-100/firmware.stm').stat().st_size,firmware_SHA256=sha(src/'obj-nes-100/firmware.stm'))
    r['Flash_remaining_B']=212992-r['firmware_B']
    vals=list(map(int,re.search(r'(?m)^\s*(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+[a-f0-9]+\s+obj-',(folder/'size.log').read_text()).groups()[:3]))
    r.update(dict(zip(['text_B','data_B','BSS_B'],vals)));r['struct_B']={}
    with (src/'obj-nes-100/sd2snes.elf').open('rb')as f:
        elf=ELFFile(f)
        for cu in elf.get_dwarf_info().iter_CUs():
            for d in cu.iter_DIEs():
                if d.tag!='DW_TAG_structure_type' or not d.attributes.get('DW_AT_name')or not d.attributes.get('DW_AT_byte_size'):continue
                n=d.attributes['DW_AT_name'].value.decode()
                if n in ['nes_native_runtime165','nes_native_sink165','nes_plan200','nes_sink_window184']:r['struct_B'][n]=d.attributes['DW_AT_byte_size'].value
    return r
def activity(e,g):
    spi=[x for x in e if x['generation']==g and x['event']=='SPI']
    ordinary=[x for x in spi if x['packet_opcode']in[2,4,5,6,8]]
    bulk=[x for x in spi if x['packet_opcode']==7]
    end=max(x['clock']for x in spi if x['opcode']=='0xe9')
    first=min(x['start']for x in ordinary);last=max(x['clock']for x in bulk)
    return dict(END_to_first_ordinary_ms=ms(first-end),first_ordinary_before_last_bulk_ms=ms(last-first),ordinary_before_last_bulk=sum(x['start']<last for x in ordinary),wire_B=sum(x['bytes']for x in spi),SPI_counts={op:sum(x['opcode']==op for x in spi)for op in ['0xe0','0xe1','0xe8','0xe9']})
def analyze(a):
    a.out.mkdir(parents=True,exist_ok=False)
    b=read(a.reference/'joint.json');c=read(a.joint/'joint.json');test=read(a.test/'result.json')
    assert b['passed']and c['passed']and test['passed']
    assert b['parameters']==c['parameters'] and b['client_SHA256']==c['client_SHA256']
    assert b['ROM_read_allocations']==c['ROM_read_allocations']==3280
    assert b['vram_DMA_B']==c['vram_DMA_B']==36144 and b['commits']==c['commits']==12
    assert c['future_ACK_filtered']and not c['atomic_DMA_overshoot_charged_to_ARM']and c['native_service_code_executed']>0
    assert c['max_bulk_banks']<=2 and int(c['observed_stack_low'],16)>int(c['workspace_end'],16)
    build=cost(a.arm);old=cost(a.baseline_arm)
    assert build['firmware_SHA256']==c['firmware_SHA256']==test['firmware_SHA256']
    assert build['Flash_remaining_B']>=0
    events=[read(x/'events.json')for x in [a.reference,a.joint]];rows=[]
    for x,y in zip(b['frames'],c['frames']):
        g=x['generation'];assert g==y['generation']
        assert sha(a.reference/f'frame-{g}.rgb')==sha(a.joint/f'frame-{g}.rgb'),g
        rows.append(dict(generation=g,RGB_SHA256=sha(a.joint/f'frame-{g}.rgb'),reference_ACK=x['ACK_masterclock'],candidate_ACK=y['ACK_masterclock'],ACK_delta_ms=ms(y['ACK_masterclock']-x['ACK_masterclock']),reference_activity=activity(events[0],g),candidate_activity=activity(events[1],g)))
    windows={}
    for start,label in [(0,'after_first_11'),(1,'after_two_10')]:
        oldms=ms(b['frames'][-1]['ACK_masterclock']-b['frames'][start]['ACK_masterclock'])
        newms=ms(c['frames'][-1]['ACK_masterclock']-c['frames'][start]['ACK_masterclock'])
        windows[label]=dict(reference_ms=oldms,candidate_ms=newms,delta_ms=newms-oldms,reduction_percent=100*(oldms-newms)/oldms)
    board=read(ROOT/'analysis/fault507-verification.json')
    for n,h in board['FPGA']['source_inputs'].items():assert sha(a.board/n)==h,n
    r=dict(experiment=508,PR=140,baseline_physical='MMC502',physical_FPS=10.59,new_physical_FPS=None,new_installer=False,functional_passed=True,ARM=dict(reference=old,candidate=build,delta={k:build[k]-old[k]for k in ['firmware_B','text_B','data_B','BSS_B']},new_standalone_global_objects=0,static_runtime_is_in_BSS=True),guards=test,FPGA=dict(changed=False,cost=board['FPGA']['cost'],related_paths=board['FPGA']['related_paths'],source_inputs=board['FPGA']['source_inputs'],new_Quartus_run=False,full_reset_CDC_IO_approved=False),SNES=dict(changed=False,SHA256=c['client_SHA256']),schedule=dict(parameters=c['parameters'],windows=windows,frames=rows,reference_wire_B=sum(b['wire_B'].values()),candidate_wire_B=sum(c['wire_B'].values()),wire_delta_B=sum(c['wire_B'].values())-sum(b['wire_B'].values()),reference_wire_by_opcode=b['wire_B'],candidate_wire_by_opcode=c['wire_B'],reference_ARM_instructions=b['ARM_instructions'],candidate_ARM_instructions=c['ARM_instructions'],reference_IRQ=b['SysTick_calls'],candidate_IRQ=c['SysTick_calls'],reference_stack_low=b['observed_stack_low'],candidate_stack_low=c['observed_stack_low'],workspace_end=c['workspace_end'],stack_gap_B=int(c['observed_stack_low'],16)-int(c['workspace_end'],16),max_bulk_banks=c['max_bulk_banks'],VRAM_DMA_B=c['vram_DMA_B'],ROM_read_allocations=c['ROM_read_allocations']),limitations=['CPI,ROM safe-slot density and peripheral responses remain models;not full NES/PSRAM RTL or physical FPS','Fixed12captures;not capture rejection rate,long-game stability or new menu hardware test','FPGA retains per-packet independent ACK checker;partial ARM watermark is not final display ACK','Flash has zero spare bytes;candidate is not a new physical delivery'])
    r['evidence_SHA256']={label:sha(p)for label,p in [('reference_joint',a.reference/'joint.json'),('candidate_joint',a.joint/'joint.json'),('reference_events',a.reference/'events.json'),('candidate_events',a.joint/'events.json'),('guards',a.test/'result.json'),('ARM_recipe',ROOT/'tools/nes_overlap508.py'),('FPGA507_report',ROOT/'analysis/fault507-verification.json')]}
    r['ARM_source_inputs']={n:sha(a.arm/'src'/n)for n in ['nes_native_runtime165.c','nes_native_sink165.c','nes_native_sink165.h','nes_plan_service200.c','nes_plan_service200.h','nes_sink_window184.c','nes_sink_window184.h']}
    (a.out/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,windows=windows,ARM=r['ARM'],wire_delta_B=r['schedule']['wire_delta_B'],stack_gap_B=r['schedule']['stack_gap_B']),ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ['arm','baseline-arm','reference','joint','test','board','out']:p.add_argument('--'+n,type=Path,required=True)
    analyze(p.parse_args())
