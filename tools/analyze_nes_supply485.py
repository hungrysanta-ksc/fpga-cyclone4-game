# SPDX-License-Identifier: MIT
"""485 linked ARM ownership tests +482 RTL/65816 functional join and budgets.

Actual full ARM/IRQ/SPI/ROM time remains a physical trial gate. Host C/RTL/Mesen
transaction timing is not an M4 clock model or a continuous-frame time proof.
"""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter

ROOT=Path(__file__).resolve().parents[1]
sha=lambda q:hashlib.sha256(q.read_bytes()).hexdigest()
read=lambda q:json.loads(q.read_text(encoding='utf8'))
p=argparse.ArgumentParser(description=__doc__)
for n in ['arm','preparation','guards','live','pixels','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args()
old=read(ROOT/'analysis/mmc482-verification.json');base=read(ROOT/'analysis/game484-planner.json')
prep,guard,live,pixels=[read(q) for q in [a.preparation,a.guards/'result.json',a.live/'result.json',a.pixels]]
assert not prep['eager_only'] and prep['trial_labels']
assert guard['passed'] and live['passed'] and pixels['passed'] and pixels['mismatches']==0
assert pixels['pixels']==57344 and live['consumer']['commits']==1 and live['consumer']['acks']==34
assert live['consumer']['retired_chunks']==2 and live['consumer']['vram_bytes']==4416
assert sha(a.arm/'obj-nes-100/firmware.stm')==guard['firmware_SHA256']
for n,h in prep['patch_sources'].items():assert sha(a.arm/n)==h,n
for n,h in old['whole_board_inputs'].items():assert sha(a.live/n)==h,n
for n in ['nes_native_runtime165.c','nes_native_sink165.c','nes_sink_window184.c','nes_plan_service200.c','nes_plan_service200.h']:
    assert sha(a.arm/n)==sha(a.live/n),n
lua=(a.live/'capture.lua').read_text(encoding='utf8')
for check in ['reveal outside vblank','DMA outside vblank','early display ACK']:assert check in lua
assert 'QUIET485 calls=' in live['host'] or 'QUIET485 calls=' in (a.live/'host.log').read_text(encoding='utf8')
counts=Counter();payload=Counter();trace={}
for q in sorted(a.live.glob('H-*.req')):
    b=q.read_bytes()
    if b[0]==1:
        op=b[8];counts[hex(op)]+=1
        if op==0xe1:payload[str(b[9])]+=1
        trace[q.name]={'request':sha(q),'reply':sha(q.with_suffix('.rsp'))}
text,data,bss=map(int,(a.arm.parent/'size.log').read_text(encoding='utf8').splitlines()[1].split()[:3])
size=(a.arm/'obj-nes-100/firmware.stm').stat().st_size
tail=old['ARM']['Flash_tail']-(size-old['ARM']['bytes']);assert tail>=128
assert data==base['ARM']['data'] and bss-base['ARM']['BSS']==20
r={'passed':True,'candidate':'MMC485','physical_baseline':'MMC482','scope':__doc__,
   'hardware_trial_ready':True,'hardware_verified':False,'physical_FPS':None,'full_path_ms':None,
   'ARM':{'firmware_SHA256':guard['firmware_SHA256'],'ELF_SHA256':sha(a.arm/'obj-nes-100/sd2snes.elf'),
          'text':text,'data':data,'BSS':bss,'bytes':size,'Flash_tail':tail,'text_delta_vs484':text-base['ARM']['text'],
          'ownership_state_delta_B':bss-base['ARM']['BSS'],'RUN_workspace':base['ARM']['RUN_workspace'],
          'new_payload_buffer_B':0,'full_stack_proof':False},
   'FPGA':{'changed':False,'BI3_SHA256':old['FPGA']['BI3_SHA256'],'reused482_FIT':old['FIT'],
           'remaining_LE':old['remaining_LE'],'new_Quartus':False,'full_CDC_IO_signoff':False},
   'source_patch_SHA256':prep['patch_sources'],'whole_board_inputs':old['whole_board_inputs'],
   'M4_guards':guard['rows'],'M4_guard_scope':guard['scope'],
   'functional_join':{'consumer':live['consumer'],'host':live['host'],'pixel_comparison':pixels,
                      'VBlank_reveal_DMA_final_ACK_assertions':True,'actual_IRQ_timing':False,'continuous_frame_timing':False,
                      'PSRAM_delay_ns':70,'SPI_opcode_calls':dict(counts),'E1_opcodes':dict(payload)},
   'SPI_trace_SHA256':trace,'evidence_SHA256':{'preparation':sha(a.preparation),'guards':sha(a.guards/'result.json'),
                       'live':sha(a.live/'result.json'),'pixels':sha(a.pixels)},
   'preserved_failures':['armguard01: harness omitted three DWARF types','armguard05: harness did not map inlined DWT read',
                         'live01: function/pixels passed, but E8 busy polling exposed; candidate01/ARM01 and ARM02 not delivered'],
   'limits':['M4 guard endpoint models delayed descriptor/ACK and DWT time, not hardware cycles/IRQ/ROM',
             'Live uses exact C source and actual RTL/65816, with modeled128us quiet and seeded ROM/loader',
             'No measured mean/p95/continuous capture/NES speed or same-phase full M4/IRQ timeline',
             'User must confirm485 menu return and provide new DWT logs; no time or FPS improvement claimed']}
a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n')
print(json.dumps({'passed':True,'Flash_tail':tail,'BSS':bss,'text_delta_vs484':r['ARM']['text_delta_vs484'],
                  'E8':counts['0xe8'],'hardware_verified':False}))
