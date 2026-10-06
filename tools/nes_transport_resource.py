# SPDX-License-Identifier: MIT
# Resource-only fit of the same original031 transport wrapper used in simulation.
from pathlib import Path
import argparse,hashlib,json,shutil,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args()
 repo=Path(__file__).resolve().parents[1];out=a.out.resolve();assert str(out).isascii() and not out.exists();out.mkdir()
 files=['nes_packet_queue_ram.sv','nes_packet_cdc_ram.sv','nes_host_stage.sv','nes_snes_frontend.sv','nes_transport.sv']
 for name in files:shutil.copyfile(repo/'src/nes'/name,out/name)
 (out/'transport.qpf').write_text('PROJECT_REVISION = "transport"\n')
 (out/'transport.sdc').write_text('create_clock -name queue -period 46.560846 [get_ports queue_clk]\ncreate_clock -name host -period 11.904762 [get_ports host_clk]\nderive_clock_uncertainty\n')
 qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
 'set_global_assignment -name TOP_LEVEL_ENTITY nes_transport','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
 'set_global_assignment -name NUM_PARALLEL_PROCESSORS 4','set_global_assignment -name SEED 1','set_global_assignment -name SDC_FILE transport.sdc',
 'set_global_assignment -name STRATIX_DEVICE_IO_STANDARD "3.3-V LVTTL"']
 qsf += ['set_global_assignment -name SYSTEMVERILOG_FILE '+f for f in files]
 ports='reset reset_epoch p_op p_epoch p_seq p_length p_data p_accept p_error snes_addr read_n write_n romsel_n snes_data_in bus_data databus_oe_n databus_dir ready busy fault host_read_owned bus_error frontend_error'.split()
 qsf += ['set_instance_assignment -name VIRTUAL_PIN ON -to '+n for n in ports]
 (out/'transport.qsf').write_text('\n'.join(qsf)+'\n')
 m={'candidate':'NES-H1-SNES-FRONTEND-031','sources':{f:sha(out/f) for f in files},'driver_sha256':sha(__file__),'phases':{},'hardware_eligible':False,
 'scope':'Transport-only resource fit,virtual external pins,2declared clocks. No NES core/producer/loader/PPU consumer/PLL/physical pins or IO constraints. No STA signoff. Do not add LAB counts to018 as an integration guarantee.'}
 for phase in ('map','fit'):
  with (out/(phase+'.log')).open('wb') as log:
   proc=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'transport'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=300)
  m['phases'][phase]=proc.returncode;(out/'result.json').write_text(json.dumps(m,indent=2)+'\n')
  print(phase,proc.returncode,flush=True);assert proc.returncode==0,'Inspect '+phase+'.log'
 print((out/'output_files/transport.fit.summary').read_text(),flush=True)
if __name__=='__main__':main()
