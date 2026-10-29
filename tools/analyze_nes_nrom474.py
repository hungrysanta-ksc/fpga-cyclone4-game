# SPDX-License-Identifier: MIT
"""Gate exact474 ARM/471 FPGA artifacts and keep component vs physical costs separate."""
import argparse,json,re
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
p=argparse.ArgumentParser()
for n in ['arm','board','live','native','static','moving','recovery','out']:p.add_argument('--'+n,type=Path,required=True)
a=p.parse_args();old=json.loads((ROOT/'analysis/nrom471-verification.json').read_text(encoding='utf8'))
load=lambda path:json.loads(path.read_text(encoding='utf8'))
live,native,static,moving=[load(d/'result.json') for d in [a.live,a.native,a.static,a.moving]]
assert all(x['passed'] for x in [live,native,static,moving])
fw=a.arm/'obj-nes-100/firmware.stm';firmware=sha(fw)
for n,h in old['FPGA_inputs'].items():assert sha(a.board/n.strip('"'))==sha(a.live/n.strip('"'))==h,n
for n,h in native['ARM_inputs'].items():assert sha(a.arm/n)==sha(a.live/n)==h,n
for n in ['nes_native165.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c','nes_native_runtime165.h']:
 assert sha(a.arm/n)==sha(a.live/n),n
for item in [static,moving]:
 assert item['new']['firmware_sha256']==firmware
 assert len(item['new']['frames'])==15
for n in ['nes_native165.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c']:
 assert sha(a.arm/n)==sha(BASE/'probes/nes-nrom418/arm471-04/src'/n),n
assert sha(a.board/'fpga_nrom471.bi3')==old['artifacts']['FPGA_BI3']
assert sha(a.board/'board.rbf')==old['artifacts']['RBF']
recovery={}
for f in ['none','program','done','busy','token']:
 item=load(a.recovery/('recovery474-'+f)/'result.json');assert item['passed'] and item['firmware_sha256']==firmware and item['safe_return']==int(f=='none');recovery[f]=item
assert live['rom_sha256']==old['artifacts']['moving_ROM']
size=(a.arm.parent/'size.log').read_text();m=re.search(r'\n\s*(\d+)\s+(\d+)\s+(\d+)\s+\d+\s+[\da-f]+\s+obj-nes-100',size);assert m
sizes=dict(zip(['text','data','bss'],map(int,m.groups())))
symbols=(a.arm.parent/'symbols.log').read_text()
symbol=lambda name:int(re.search(r'^([0-9a-f]+)\s+\w\s+'+re.escape(name)+r'$',symbols,re.M)[1],16)
flash_tail=0x34000-fw.stat().st_size;RAM_gap=symbol('__stack')-symbol('__bss_end__')-31848
assert flash_tail>=0 and RAM_gap>=4000
def profile(item):
 rows=[]
 for x,y in zip(item['old']['frames'],item['new']['frames']):
  assert x['plans']==y['plans'] and x['state_sha256']==y['state_sha256']
  rows.append({'case':y['case'],'old_instructions':x['planner_instructions'],'new_instructions':y['planner_instructions'],'reduction_percent':100*(1-y['planner_instructions']/x['planner_instructions'])})
 return rows
native_files={n:sha(a.arm/n) for n in ['nes_native165.c','nes_native_runtime165.c','nes_runtime_board165.inc','nes_game149_spi.inc','nes_native165_bulk.inc','nes_budget210.c','nes_cost471.h','nes_cost471.c','nes_planner211.c','nes_sink_window184.c','nes_sink_window184.h']}
r={'passed':True,'selected':'arm474-02 with byte-identical FPGA471-04 and scene02',
 'artifacts':{'firmware_stm':firmware,'FPGA_BI3':old['artifacts']['FPGA_BI3'],'RBF':old['artifacts']['RBF'],'moving_ROM':live['rom_sha256']},
 'FPGA_inputs':old['FPGA_inputs'],'ARM_changed_inputs':native_files,
 'FPGA_resources':old['resources'],'FPGA_timing_ns':old['timing_ns'],
 'FPGA_note':'identical471 bitstream/source reused, no new Quartus compile; raw CDC/IO signoff remains open',
 'ARM_sizes':sizes,'ARM_delta_vs471':{k:sizes[k]-v for k,v in {'text':201641,'data':10040,'bss':18468}.items()},
 'device_budget':{'configured_flash_bytes':0x40000,'firmware_origin':0x0800c000,'firmware_file_bytes':fw.stat().st_size,'firmware_file_tail_to_configured_flash_end':flash_tail,'configured_RAM_bytes':0x10000,'bss_end':hex(symbol('__bss_end__')),'stack_top':hex(symbol('__stack')),'RAM_gap_after_RUN_workspace_before_nested_calls_IRQ':RAM_gap},
 'ARM_stack_bytes':{'RUN_workspace':31848,'runtime_step':64,'planner':280,'planner_old':272,'quiet_wait':32,'cost_formatter':72},
 'static_M4_profile':profile(static),'moving_M4_profile':profile(moving),
 'native_validation':native,'live_validation':live,'recovery_validation':recovery,
 'physical_comparison':{'baseline471_scene':'same moving scene','baseline471_fps':1178/60.07,'baseline471_mean_ms':60070/1178,'new474_fps':None,'new474_mean_ms':None,'reason':'requires user hardware logs; M4 instruction counts and deterministic quiet model are not physical full-frame timing'},
 'unchanged':{'input_header':'2232','output_client':'2271','loader_profile':'78','credit_slots':4,'independent_validation':True,'STOP_and_finalACK':True,'same_moving_ROM':True},
 'limits':['group reuse is exact within a committed frame; no cross-frame history shortcut',
           'search stops after first4 different initial groups unless reuse found; distinct rows have measured overhead',
           'quiet128us is a nominal between-query budget; IRQ/guard/service can extend it; report actual cycles',
           'quiet fallback with unavailable DWT uses immediate polling and original guard',
           'live C host has no DWT clock so quiet timing is covered separately by deterministic native model',
           'single live frame plus15 M4 cases/static+moving and129 independent-renderer cases, not sustained hardware60Hz',
           'preserve471 delivered bytes and physical473 raw evidence']}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8')
print(json.dumps({'passed':True,'firmware':firmware,'ARM':sizes,'moving_warm_instruction_reduction_percent':r['moving_M4_profile'][1]['reduction_percent'],'FPGA_unchanged':True,'physical_new_fps':None}))
