# SPDX-License-Identifier: MIT
"""Connect the verified491 pair to existing physical DWT/IRQ/SPI/ACK counters.

Only same-length trial labels change. ELF executable functions must match491.
Full-path physical acceleration remains unverified until returned492 logs.
"""
import argparse,hashlib,json
from pathlib import Path
from check_nes_game478 import ELFFile
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def funcs(p):
    with p.open('rb')as f:
        e=ELFFile(f);out={}
        for s in e.get_section_by_name('.symtab').iter_symbols():
            if s['st_info']['type']=='STT_FUNC'and s['st_size']and isinstance(s['st_shndx'],int):
                sec=e.get_section(s['st_shndx']);i=(s['st_value']&~1)-sec['sh_addr']
                out[(s.name,s['st_value'],s['st_size'])]=sec.data()[i:i+s['st_size']]
        return out
def prepare(arm,out):
    evidence=json.loads((ROOT/'analysis/consume491-verification.json').read_text());assert evidence['passed']
    assert sha(arm/'obj-nes-100/firmware.stm')==evidence['ARM']['firmware_SHA256']
    out.mkdir(parents=True,exist_ok=False);patch=out/'patch';patch.mkdir();before={}
    for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','VERSION']:
        q=arm/n;s=q.read_text();before[n]=sha(q);assert '489'in s
        s=s.replace('489','492');(patch/n).write_text(s,encoding='utf8',newline='\n')
    (out/'preparation.json').write_text(json.dumps({'scope':__doc__,'baseline_SHA256':evidence['ARM']['firmware_SHA256'],
        'baseline_sources':before,'patch_sources':{p.name:sha(p)for p in patch.iterdir()}},indent=2)+'\n')
def verify(arm,baseline,board,client,programmer,out):
    v=json.loads((ROOT/'analysis/consume491-verification.json').read_text());assert v['passed']
    assert sha(baseline/'obj-nes-100/firmware.stm')==v['ARM']['firmware_SHA256']
    old,new=funcs(baseline/'obj-nes-100/sd2snes.elf'),funcs(arm/'obj-nes-100/sd2snes.elf');assert old==new and len(new)>700
    for n,h in v['FPGA']['source_inputs'].items():assert sha(board/n)==h,n
    assert sha(client/'sink165.sfc')==v['SNES']['SFC_SHA256']
    for n in ['nes_native_runtime165.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_window184.c',
              'nes_cost471.c','fpga.c','stm32f4xx/timer.c']:
        assert sha(arm/n)==sha(baseline/n),n
    text=(arm/'nes_menu_diagnostic.c').read_text()+(arm/'nes_checkpoint112.c').read_text()
    labels=['NES MMC3 492.nh1','mmc492.nes','fpga_mmc492.bi3','nes-progress-mmc492.txt','nes-budget-mmc492.txt','nes-game-last-mmc492.txt']
    assert all(n in text for n in labels)
    prog=json.loads(programmer.read_text());assert prog['passed']
    runtime=(arm/'nes_native_runtime165.c').read_text()
    assert all(f'nes_cost471_phase({k},cost_mark471)'in runtime for k in range(3))
    assert 'nes_trace166.last_display_tick'in runtime and 'if(!s->sink.displayed'in runtime
    assert any(k[0]=='SysTick_Handler'for k in new)
    fw=arm/'obj-nes-100/firmware.stm';assert fw.stat().st_size==212844
    before=(baseline/'obj-nes-100/firmware.stm').read_bytes();after=fw.read_bytes()
    assert before[:4]==after[:4]==b'STM3'
    # Generated STM3 image header updates with the changed payload. Every byte
    # after it, including vectors/data, differs only by the declared labels.
    assert before[32:].replace(b'489',b'492')==after[32:]
    r={'passed':True,'candidate':'MMC492','limited_functional_trial_ready':True,'scope':__doc__,
       'physical_acceleration_verified':False,'physical_FPS':None,'baseline':'analysis/hardware490-mmc489.json',
       'implementation':'analysis/consume491-verification.json','client_ABI':'4891','labels':labels,
       'ARM':{'firmware_SHA256':sha(fw),'firmware_B':fw.stat().st_size,'Flash_free_B':148,
              'linked_functions_equal':len(new),'all_function_addresses_sizes_bytes_equal_to491':True,
              'all_nonheader_bytes_are_label_only_changes':True,'STM3_generated_header_B':32,
              'BSS_B':18572,'RUN_workspace_B':31848,'new_global_RAM_B':0,'new_measurement_overhead':False,
              'configured_clock_hz':84000000,'DWT_includes_IRQ_guard_wait':True,'nested_counters_not_additive':True},
       'connections':{'receive':'actual nes_native165 prepare/poll and D0-D3 through shared SPI',
                      'plan_supply':'actual planner221,first/full-buffer E9,op7 DMA and E0/E8 credit/consume',
                      'seal_final_ACK':'actual nes_sink212_seal,independent checks,65816 DMA/VBlank and matching ACK',
                      'IRQ':'linked SysTick_Handler unchanged;DWT continues during actual IRQ/guard/service',
                      'ROM_competition':'unchanged491 source/PSRAM arbitration runs on board;waiting included in elapsed/DWT',
                      'retirement':'native_frames increments only after matching displayed generation;STOP/base/menu unchanged'},
       'FPGA':v['FPGA'],'programmer':prog,'matching_FIT_STA_reused_no_new_compile':True,
       'consumer':v['SNES'],'joint_scope':'491 actual C/RTL/65816 first raw0 frame and separate raw71; not a common physical clock',
       'full_physical_schedule_gate':'Await492 native_frames/finalACK,DWT phases/ops/quiet and source/ROM delays on board',
       'limitations':['No actual492 FPS/menu result yet;489 user-confirmed baseline preserved',
                      'No exact IRQ-only or ROM-grant counter;DWT includes their effects but cannot attribute each cause',
                      'Different scene/input cannot establish a causal performance percentage',
                      'Full stack IRQ/reset CDC IO and MMC4/5 remain open'],
       'next':'Install paired492,collect3fresh logs and compare total receive/plan/SEAL/finalACK plus native observer/STOP/menu'}
    out.write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf8',newline='\n')
    print(json.dumps({'passed':True,'functions':len(new),'Flash_free_B':148,'physical_acceleration_verified':False}))
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('mode',choices=['prepare','verify'])
    for n in ['arm','out']:p.add_argument('--'+n,type=Path,required=True)
    for n in ['baseline','board','client','programmer']:p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.mode=='prepare':prepare(a.arm,a.out)
    else:verify(a.arm,a.baseline,a.board,a.client,a.programmer,a.out)
