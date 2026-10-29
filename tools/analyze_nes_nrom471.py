# SPDX-License-Identifier: MIT
"""Same-artifact gate and cost ledger for the471 hardware handoff."""
import argparse,csv,json,re,zlib
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from check_nes_boundary165 import measurements
p=argparse.ArgumentParser()
for n in ['board','arm','core','live','m4','guards','program','suite','out']:p.add_argument('--'+n,required=True,type=Path)
a=p.parse_args();spec=json.loads((ROOT/'analysis/nrom458-artifacts.json').read_text());q=(a.board/'board.qsf').read_text();names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL|SDC|QIP|MIF)_FILE (\S+)',q);sources={n:sha(a.board/n.strip('"')) for n in names};assert len(sources)==66
changed=[n for n,h in sources.items() if h!=spec['qsf_sources'][n]];assert set(changed)=={'nes_native_export203.sv','nes_rom_spi.sv'},changed
for n,h in sources.items():assert sha(a.live/n.strip('"'))==h,n
for n in ['nes_native165.c','nes_native_runtime165.c','nes_planner211.c','nes_resident211.c','nes_plan_service200.c','nes_native_sink165.c','nes_sink_window184.c']:assert sha(a.arm/n)==sha(a.live/n),n
live=json.loads((a.live/'result.json').read_text());m4=json.loads((a.m4/'result.json').read_text());guards=json.loads((a.guards/'result.json').read_text());program=json.loads((a.program/'result.json').read_text());assert all(r['passed'] for r in [live,m4,guards,program]);assert sha(a.arm/'obj-nes-100/firmware.stm')==m4['new']['firmware_sha256'];assert program['image_sha256']==sha(a.board/'fpga_nrom471.bi3') and program['rbf_sha256']==sha(a.board/'board.rbf')
fit=(a.board/'output_files/board.fit.summary').read_text();assert 'Fitter Status : Successful' in fit
def metric(label):return int(re.search(re.escape(label)+r'\s*:\s*([\d,]+)',fit)[1].replace(',',''))
resources={k:metric(label) for k,label in [('LE','Total logic elements'),('comb','Total combinational functions'),('FF','Dedicated logic registers'),('RAM_bits','Total memory bits')]}
timing={}
for view in ['implementation','nominal']:
 rows=list(csv.DictReader((a.board/(view+'-paths204.tsv')).open(),delimiter='\t'));timing[view]={k:min(float(x['slack']) for x in rows if x['kind']==k and ((x['from_clock']=='nes')==(x['to_clock']=='nes'))) for k in ['setup','hold']}
assert timing['nominal']['setup']>=0 and timing['nominal']['hold']>=0
io=measurements(a.board);assert io['conditional_data_bounds_pass'] and io['native_payload_reset_pass']
def blocks(path):
 rows=[x.split() for x in path.read_text().splitlines()];return len(rows),sum(int(x[1]) for x in rows)
old_b,old_n=blocks(BASE/'probes/nes-nrom429/core01/nrom429-blocks.txt');new_b,new_n=blocks(a.core/'nrom429-blocks.txt');assert (old_b,old_n)==(25,5764) and (new_b,new_n)==(10,1926)
oldwire=old_n+19*old_b+40;newwire=new_n+19*new_b+40
sta=(a.board/'output_files/board.sta.summary').read_text();raw={k:min(float(x) for x in re.findall(r'Type\s*:[^\n]*\b'+k+r'\b[^\n]*\nSlack\s*:\s*(-?[\d.]+)',sta)) for k in ['Setup','Recovery']}
r={'passed':True,'selected':'471-04 paired with arm471-04','base':'457/418/428','FPGA_inputs':sources,'changed_FPGA_inputs':changed,'artifacts':{'firmware_stm':sha(a.arm/'obj-nes-100/firmware.stm'),'FPGA_BI3':sha(a.board/'fpga_nrom471.bi3'),'RBF':sha(a.board/'board.rbf'),'SOF':sha(a.board/'output_files/board.sof'),'sink_hex':sha(a.board/'sink-program.hex'),'moving_ROM':live['rom_sha256']},'resources':resources,'delta_vs457':{k:resources[k]-v for k,v in {'LE':14770,'comb':13637,'FF':8037,'RAM_bits':185824}.items()},'timing_ns':timing,'raw_timing_ns':raw,'conditional_IO':{k:io[k] for k in ['psram_conditional_margin_ns','snes_read_envelope_ns','spi_reply_envelope_ns','conditional_data_bounds_pass']},'static_same_canonical_frame':{'old_payload':old_n,'new_payload':new_n,'payload_reduction_percent':100*(1-new_n/old_n),'old_blocks':old_b,'new_blocks':new_b,'old_minimum_successful_source_wire_bytes':oldwire,'new_minimum_successful_source_wire_bytes':newwire,'old_source_wire_ms_at2_625MHz':oldwire*8/2625,'new_source_wire_ms_at2_625MHz':newwire*8/2625,'packet_decoder_old_instructions':m4['old']['packet_instructions'],'packet_decoder_new_instructions':m4['new']['packet_instructions'],'instruction_reduction_percent':100*(1-m4['new']['packet_instructions']/m4['old']['packet_instructions'])},'whole_frame_physical':{'baseline_static_fps':14.968364968364968,'baseline_mean_ms':66.8075639599555,'new_static_fps':None,'new_moving_fps':None,'new_mean_ms':None,'reason':'requires user hardware return; transaction RPC functional duration is not hardware timing'},'live_regression':live,'guards':guards,'ARM_static':{'text':201641,'data':10040,'bss':18468,'delta_text':1580,'delta_bss':392,'runtime_workspace_stack':31848,'report_stack_after_RUN':6912},'cost_meter':'DWT cycle sums are64bit; each measured interval uses modular32bit delta; available flag required; phase and opcode times overlap; original10ms counters preserved','limitations':['implementation guidance setup -0.036ns is disclosed, actual clock nominal passes','raw reset/CDC/IO unconstrained boundaries remain; no full signoff','one live moving frame plus separate NES multi-frame motion/A validation, not physical sustained60fps','input header2232 requires the paired ARM and FPGA; output client2271 unchanged','checker response gains1clock of latency; tag comparison remains independent; unexpected ownership/hard fault/reset/STOP still cancel','report metadata-only scene CRC addition after host live test; seven core C files and all66 FPGA inputs match final artifact']}
suite={}
for key,folder in [('CHECK','compact471-check04'),('clock_stop','compact471-stop04'),('moving_scene','compact471-scene04'),('post_fit_ROM','compact471-eda01/rom-check')]+[('recovery_'+f,'compact471-recovery-final-'+f) for f in ['none','program','done','busy','token']]:
 result=a.suite/folder/'result.json';item=json.loads(result.read_text(encoding='utf8'));assert item['passed'],key
 suite[key]={'result_sha256':sha(result),'result':item}
assert suite['CHECK']['result']['RTL']==sha(a.board/'nes_rom_spi.sv')
assert suite['moving_scene']['result']['rom_sha256']==live['rom_sha256']
assert suite['moving_scene']['result']['one_pixel_each_NES_frame_verified']
assert suite['post_fit_ROM']['result']['expected_hex_sha256']==sha(a.board/'sink-program.hex')
for f in ['none','program','done','busy','token']:
 item=suite['recovery_'+f]['result'];assert item['firmware_sha256']==r['artifacts']['firmware_stm'];assert item['safe_return']==int(f=='none')
r['additional_functional_suite']=suite
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps({'resources':resources,'timing':timing,'static':r['static_same_canonical_frame'],'physical_new_fps':None}))
