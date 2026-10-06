# SPDX-License-Identifier: MIT
"""Standalone045 producer resource cost; not joint NES or board fit."""
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args();out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 src=ROOT/'src/nes/nes_packet_memory_producer.sv';shutil.copy2(src,out/src.name)
 (out/'producer.qpf').write_text('PROJECT_REVISION = "producer"\n')
 (out/'producer.sdc').write_text('create_clock -name queue -period 46.560846 [get_ports queue_clk]\nderive_clock_uncertainty\n')
 qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_packet_memory_producer','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files','set_global_assignment -name NUM_PARALLEL_PROCESSORS 4','set_global_assignment -name SEED 1','set_global_assignment -name SDC_FILE producer.sdc','set_global_assignment -name SYSTEMVERILOG_FILE nes_packet_memory_producer.sv','set_global_assignment -name STRATIX_DEVICE_IO_STANDARD "3.3-V LVTTL"']
 ports='reset reset_epoch desc_valid desc_ready desc_epoch desc_seq desc_base desc_length mem_req_valid mem_req_ready mem_req_address mem_req_epoch mem_rsp_valid mem_rsp_ready mem_rsp_address mem_rsp_epoch mem_rsp_data mem_rsp_error p_op p_epoch p_seq p_length p_data p_accept p_error done producer_fault exhausted producer_error published'.split()
 qsf+=['set_instance_assignment -name VIRTUAL_PIN ON -to '+name for name in ports];(out/'producer.qsf').write_text('\n'.join(qsf)+'\n')
 result={'candidate':'NES-R2-MEMORY-PRODUCER-045','source_sha256':hashlib.sha256(src.read_bytes()).hexdigest(),'phases':{},'hardware_eligible':False,'scope':'Standalone producer only, virtual external pins and declared queue clock; excludes NES core, transport, memory controller, board PLL/pins/IO and STA. Separate resource cost cannot be added to LAB headroom as proof.'}
 for phase in ('map','fit'):
  with (out/(phase+'.log')).open('wb') as f:cp=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'producer'],cwd=out,stdout=f,stderr=subprocess.STDOUT,timeout=300)
  result['phases'][phase]=cp.returncode;(out/'result.json').write_text(json.dumps(result,indent=2)+'\n');assert cp.returncode==0,phase
 print((out/'output_files/producer.fit.summary').read_text())
if __name__=='__main__':main()
