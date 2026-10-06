# SPDX-License-Identifier: MIT
# Actual physical-pin fit with PLL. Internal STA only; IO board envelope remains open.
from pathlib import Path
import argparse,hashlib,json,re,shutil,subprocess
from nes_h1_qualified import materialize
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ('out','build','quartus-bin','rle'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();repo=Path(__file__).resolve().parents[1];out=a.out.resolve()
 assert str(out).isascii() and not out.exists();out.mkdir()
 files=['src/nes/'+n+'.sv' for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus','fxpak_nes_h1_top']]+['src/fpga/gbc_bus_pll0.v']
 for n in files:shutil.copyfile(repo/n,out/Path(n).name)
 materialize(out)
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
 'set_global_assignment -name GENERATE_RBF_FILE ON',
 'set_global_assignment -name NUM_PARALLEL_PROCESSORS 4','set_global_assignment -name SEED 1','set_global_assignment -name SDC_FILE board.sdc',
 'set_global_assignment -name CYCLONEIII_CONFIGURATION_SCHEME "PASSIVE SERIAL"','set_global_assignment -name USE_CONFIGURATION_DEVICE OFF',
 'set_global_assignment -name CYCLONEII_RESERVE_NCEO_AFTER_CONFIGURATION "USE AS REGULAR IO"',
 'set_global_assignment -name RESERVE_DATA0_AFTER_CONFIGURATION "USE AS REGULAR IO"',
 'set_global_assignment -name RESERVE_DATA1_AFTER_CONFIGURATION "USE AS REGULAR IO"',
 'set_global_assignment -name RESERVE_FLASH_NCE_AFTER_CONFIGURATION "USE AS REGULAR IO"']
 qsf+=assignments
 for n in files:qsf+=['set_global_assignment -name '+('VERILOG_FILE ' if n.endswith('.v') else 'SYSTEMVERILOG_FILE ')+Path(n).name]
 for target in ['*|rd_sync[*]','*|wr_sync[*]','*|sel_sync[*]','*|req_sync[*]','*|ack_sync[*]','*|host_up_q[*]','*|queue_up_h[*]']:
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
 m={'candidate':'NES-H1-QUALIFIED-043','sources':{n:sha(repo/n) for n in files},'compiled_boundary_sha256':sha(out/'nes_h1_board_bus.sv'),'compiled_frontend_sha256':sha(out/'nes_snes_frontend.sv'),'inputs':{n:sha(out/n) for n in ['h1-pattern.hex','h1-program.hex']},'pin_source_sha256':sha(repo/'src/fpga/pin.qsf'),'driver_sha256':sha(__file__),'physical_pin_assignments':sum(s.startswith('set_location') for s in assignments),'phases':{},'hardware_eligible':False,'scope':'Actual physical pins+8MHz/84MHz PLL; internal STA only, no external IO timing envelope or deployed MCU loader. No waiver/exceptions.'}
 for phase in ('map','fit','sta','asm'):
  with (out/(phase+'.log')).open('wb') as log:
   cp=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'board'],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=600)
  m['phases'][phase]=cp.returncode;(out/'result.json').write_text(json.dumps(m,indent=2)+'\n')
  print(phase,cp.returncode,flush=True);assert cp.returncode==0,'Inspect '+phase+'.log'
 print((out/'output_files/board.fit.summary').read_text(encoding='latin-1'),flush=True)
 m.update(finish_image(out,a.rle))
 m['scope']='043 qualified-frontend physical135pin full map/fit/STA/ASM and BI3 exact roundtrip; externalIO unconstrained, no SD deployment or hardware execution'
 (out/'result.json').write_text(json.dumps(m,indent=2)+ '\n')
 print('PASS ASM/RBF/BI3 exact roundtrip',m['bi3_sha256'],flush=True)

def decode_rle(data):
 decoded=bytearray();i=0
 while i<len(data):
  value=data[i];i+=1
  if value==0x9b:decoded.append(data[i]);i+=1
  elif value in (0x5b,0x77):
   byte=data[i];length=data[i+1];i+=2
   if value==0x77:length|=data[i]<<8;i+=1
   assert length>0
   decoded.extend(bytes([byte])*length)
  else:decoded.append(value)
 return bytes(decoded)

def finish_image(out,rle):
 rbf=out/'output_files/board.rbf';bi3=out/'fpga_nh1.bi3'
 original=out/'fpga_nh1.encoder-original.bi3'
 assert rbf.is_file() and not original.exists()
 with (out/'rle-final.log').open('wb') as log:
  cp=subprocess.run([str(rle.resolve()),str(rbf),str(original)],stdout=log,stderr=subprocess.STDOUT,timeout=60)
 assert cp.returncode==0
 raw=rbf.read_bytes();encoded=original.read_bytes();decoded=decode_rle(encoded)
 trimmed=0
 # Pinned upstream encoder fseek(-1) after EOF duplicates the last byte
 # of a final run. Preserve its output and remove ONLY a proved literal FF.
 # C44 build_fpga.py already permits that padding; C44 source/tool is unchanged.
 if decoded!=raw:
  assert raw[-1:]==b'\xff' and encoded[-1:]==b'\xff'
  assert decoded==raw+b'\xff','Unexpected encoder mismatch'
  assert decode_rle(encoded[:-1])==raw,'Not a trailing literal FF'
  encoded=encoded[:-1];trimmed=1
 assert decode_rle(encoded)==raw
 bi3.write_bytes(encoded)
 return dict(rbf_bytes=len(raw),rbf_sha256=sha(rbf),bi3_bytes=len(encoded),
  bi3_sha256=sha(bi3),rle_tool_sha256=sha(rle),encoder_original_sha256=sha(original),
  trailing_literal_ff_trimmed=trimmed,bi3_exact_roundtrip=True)
if __name__=='__main__':main()
