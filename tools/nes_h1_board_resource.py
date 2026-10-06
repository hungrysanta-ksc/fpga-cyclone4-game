# SPDX-License-Identifier: MIT
# Actual physical-pin fit with PLL. Internal STA only; IO board envelope remains open.
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','build','quartus-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();repo=Path(__file__).resolve().parents[1];out=a.out.resolve()
 assert str(out).isascii() and not out.exists();out.mkdir()
 files=['src/nes/'+n+'.sv' for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus','fxpak_nes_h1_top']]+['src/fpga/gbc_bus_pll0.v']
 for n in files:shutil.copyfile(repo/n,out/Path(n).name)
 for n in ['h1-pattern.hex','h1-program.hex']:shutil.copyfile(a.build/n,out/n)
 base=(repo/'src/fpga/pin.qsf').read_text()
 top=(repo/'src/nes/fxpak_nes_h1_top.sv').read_text().split('module fxpak_nes_h1_top(',1)[1].split(');',1)[0]
 ports=set(re.findall(r'\b[A-Z][A-Z_0-9]*\b',top))
 assignments=[]
 for line in base.splitlines():
  if line.startswith('set_location_assignment ') or (line.startswith('set_instance_assignment ') and any('-name '+n+' ' in line for n in ['IO_STANDARD','CURRENT_STRENGTH_NEW','WEAK_PULL_UP_RESISTOR'])):
   target=line.split(' -to ',1)[-1].strip('"').split('[')[0]
   if target in ports:assignments.append(line)
 pin_ports={line.split(' -to ',1)[1].split('[')[0] for line in assignments if line.startswith('set_location')}
 assert pin_ports==ports,(ports-pin_ports,pin_ports-ports)
 qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
 'set_global_assignment -name TOP_LEVEL_ENTITY fxpak_nes_h1_top','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
 'set_global_assignment -name NUM_PARALLEL_PROCESSORS 4','set_global_assignment -name SEED 1','set_global_assignment -name SDC_FILE board.sdc',
 'set_global_assignment -name CYCLONEIII_CONFIGURATION_SCHEME "PASSIVE SERIAL"','set_global_assignment -name USE_CONFIGURATION_DEVICE OFF',
 'set_global_assignment -name CYCLONEII_RESERVE_NCEO_AFTER_CONFIGURATION "USE AS REGULAR IO"',
 'set_global_assignment -name RESERVE_DATA0_AFTER_CONFIGURATION "USE AS REGULAR IO"',
 'set_global_assignment -name RESERVE_DATA1_AFTER_CONFIGURATION "USE AS REGULAR IO"',
 'set_global_assignment -name RESERVE_FLASH_NCE_AFTER_CONFIGURATION "USE AS REGULAR IO"']
 qsf+=assignments
 for n in files:qsf+=['set_global_assignment -name '+('VERILOG_FILE ' if n.endswith('.v') else 'SYSTEMVERILOG_FILE ')+Path(n).name]
 for target in ['*|rd_sync[*]','*|wr_sync[*]','*|req_sync[*]','*|ack_sync[*]','*|host_up_q[*]','*|queue_up_h[*]']:
  qsf+=['set_instance_assignment -name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS -to "'+target+'"']
 (out/'board.qsf').write_text('\n'.join(qsf)+'\n')
 (out/'board.qpf').write_text('PROJECT_REVISION = "board"\n')
 (out/'board.sdc').write_text('''# Actual8MHz board source and generated84MHz PLL. No fabricated external timing envelope.
create_clock -name board8 -period 125 [get_ports CLKIN]
derive_pll_clocks
derive_clock_uncertainty
# No false-path or clock-period relaxation. External asynchronous IO remains unconstrained,
# explicitly reported as pending board qualification; positive internal slack is not signoff.
''')
 m={'candidate':'NES-H1-BOARD-034','sources':{n:sha(repo/n) for n in files},'inputs':{n:sha(out/n) for n in ['h1-pattern.hex','h1-program.hex']},'pin_source_sha256':sha(repo/'src/fpga/pin.qsf'),'driver_sha256':sha(__file__),'physical_pin_assignments':sum(s.startswith('set_location') for s in assignments),'phases':{},'hardware_eligible':False,'scope':'Actual physical pins+8MHz/84MHz PLL; internal STA only, no external IO timing envelope or deployed MCU loader. No waiver/exceptions.'}
 for phase in ('map','fit','sta'):
  with (out/(phase+'.log')).open('wb') as log:
   cp=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'board'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  m['phases'][phase]=cp.returncode;(out/'result.json').write_text(json.dumps(m,indent=2)+'\n')
  print(phase,cp.returncode,flush=True);assert cp.returncode==0,'Inspect '+phase+'.log'
 print((out/'output_files/board.fit.summary').read_text(encoding='latin-1'),flush=True)
if __name__=='__main__':main()
