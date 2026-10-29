# SPDX-License-Identifier: MIT
"""Audit the actual NROM delivery lineage against production227."""
import argparse,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
arm=BASE/'probes/nes-nrom418/arm01/src';prod=BASE/'probes/nes-repeat227/arm01/src';oldboard=BASE/'probes/nes-repeat227/asm02';manifest=json.loads((ROOT/'analysis/nrom458-artifacts.json').read_text())
assert sha(arm/'obj-nes-100/firmware.stm')==manifest['firmware_stm_sha256']
armnames=['nes_native_runtime165.c','nes_native165.c','nes_native165_bulk.inc','nes_runtime_board165.inc','nes_planner211.c','nes_resident211.c','nes_plan_service200.c','nes_sink_window184.c','nes_native_sink165.c']
rtlnames=['nes_native_frame201.sv','nes_native_export203.sv','nes_native_mailbox206.sv','nes_direct206.sv','nes_plan_batch206.sv','nes_capture_lease201.sv','nes_sink_bridge165.sv','sink-program.hex']
r={'delivered_firmware_sha256':sha(arm/'obj-nes-100/firmware.stm'),'delivered_FPGA_bi3_sha256':manifest['bi3_sha256'],'ARM_compared':{},'FPGA_compared':{}}
for n in armnames:
 assert (arm/n).read_bytes()==(prod/n).read_bytes(),n
 r['ARM_compared'][n]={'actual':sha(arm/n),'production227':sha(prod/n),'identical':True}
for n in rtlnames:
 if n in manifest['qsf_sources']:assert sha(a.board/n)==manifest['qsf_sources'][n],n
 else:assert n=='sink-program.hex' and sha(a.board/n)==manifest['sink_hex_sha256']
 assert (a.board/n).read_bytes()==(oldboard/n).read_bytes(),n
 r['FPGA_compared'][n]={'actual':sha(a.board/n),'production227':sha(oldboard/n),'identical':True}
r['scope']='selected 9 ARM and 8 FPGA/client path files only, not entire design equivalence; mapper/loader/clock reset changes exist; PR131/132 fast research implementations were not substituted into these delivered paths'
r['physical_rate_comparison']={'old227':{'workload':'SMB3','frames':465,'seconds':60.06},'new467':{'workload':'static self-generated NROM','frames':899,'seconds':60.06},'comparable_speedup_percent':None,'physical_60fps_improvement_demonstrated':False}
r['PR_evidence']={'131':{'merge':'914138969246387162bf2c909159824e72a3666d','created':'2026-10-22','merged':'2026-10-25','minimum_comb':17213,'minimum_comb_delta_vs_PR130':-470,'fast_configuration_comb':17724,'fits_device':False,'conditional_warm_ms':12.157717,'physical_test':False},'132':{'merge':'935b7bf4b4243c8881fb443a732ba167ce82fce4','created':'2026-10-25','merged':'2026-10-28','LE':20199,'comb':16508,'MAP_not_FIT':True,'warm_max_observed_gap_ms':34.048237,'physical_test':False},'133':{'merge':'8d472d50df7c396efac8426bb4de62cca8ce0346','created':'2026-10-28','merged':'2026-10-29','LE':14770,'comb':13637,'Lite_FIT':True,'full_STA_CDC_IO_signoff':False,'physical_limited_NROM_smoke':True,'new_optimized_60fps_execution_path':False}}
a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps({'ARM_identical':len(armnames),'FPGA_client_identical':len(rtlnames),'same_workload_speedup':None,'hardware_smoke_passed':True}))
