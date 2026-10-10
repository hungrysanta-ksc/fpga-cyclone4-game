# SPDX-License-Identifier: MIT
"""Materialize the pinned131 core with an isolated physical RUN shell and observer."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_cdc125_sta import ROOT,sha,put
from nes_functional import VHDL,SV
from nes_ncr1_live import FILES

def prepare(baseline,o):
 e=baseline/'nes-counter131/evidence'
 meta=json.loads((ROOT/'analysis/counter131-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];o.mkdir();inputs={}
 names=VHDL+SV+['cart_nrom.sv','nes_probe.sv']+[n+'.sv' for n in FILES+['nes_local_memory','nes_rom_service','nes_rom_physical','nes_rom_loader','nes_rom_boot','nes_rom_spi','nes_spi_boot','nes_domain_reset124','nes_diag_clock_guard127','nes_diag_startup_guard','nes_live_joint']]
 for n in names+['nes_clock_pll123.v','live.qsf','live.sdc']:
  p=e/'fit05'/n;assert sha(p)==pins['fit05/'+n],n
  d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,d);inputs['fit05/'+n]=sha(p)
 p=e/'test02/rom_boot_model.sv';assert sha(p)==pins['test02/rom_boot_model.sv'];shutil.copy2(p,o/p.name);inputs['test02/'+p.name]=sha(p)
 p=o/'nes_live_joint.sv';s=p.read_text();decls=[]
 for d in ['wire guard_allow,guard_fault,external_memory_ready,startup_ready,release_memory;',
           'wire rom_cpu_sample,rom_cpu_valid,rom_ppu_valid,rom_fault;',
           'wire [3:0] rom_error_code;','wire rom_request;wire [21:0] rom_address;']:
  assert s.count(d)==1;s=s.replace(d,'');decls.append(d)
 i=s.index(');');s=s[:i]+',output wire out_observe_reset,out_observe_sample,out_observe_ready\n'+s[i:]
 i=s.index(');')+2;s=s[:i]+'\n'+'\n'.join(decls)+s[i:]
 assert s.count('endmodule')==1
 s=s.replace('endmodule','assign out_observe_reset=reset;\nassign out_observe_sample=rom_cpu_sample && rom_cpu_valid && !reset;\nassign out_observe_ready=external_memory_ready;\nendmodule')
 put(p,s)
 for n in ['nes_run_observer134.sv','fxpak_nes_run134_top.sv']:
  shutil.copy2(ROOT/'src/nes/diagnostic'/n,o/n)
 for n in ['board134_tb.sv','run133_pll_model.sv']:shutil.copy2(ROOT/'tests/nes-functional'/n,o/n)
 # Full physical port inventory is derived bit-by-bit, not from debug/virtual ports.
 shell=(o/'fxpak_nes_run134_top.sv').read_text().split('module fxpak_nes_run134_top(',1)[1].split(');',1)[0]
 ports={}
 for direction,width,body in re.findall(r'(input|output|inout)\s+wire\s*(\[\d+:0\])?\s*([^;]*?)(?=(?:input|output|inout)\s+wire|$)',shell,re.S):
  count=int(width[1:].split(':')[0])+1 if width else 1
  for n in body.strip().strip(',').split(','):
   n=n.strip();assert re.fullmatch(r'\w+',n),n
   for i in range(count):ports[n+('['+str(i)+']' if width else '')]=direction
 base=(ROOT/'src/fpga/pin.qsf').read_text();assignments=[];locations={}
 for line in base.splitlines():
  if ' -to ' not in line:continue
  target=line.split(' -to ',1)[1].strip('"')
  if target not in ports:continue
  if line.startswith('set_location_assignment '):locations[target]=line.split()[1];assignments.append(line)
  elif line.startswith('set_instance_assignment ') and any('-name '+n+' ' in line for n in ['IO_STANDARD','CURRENT_STRENGTH_NEW','WEAK_PULL_UP_RESISTOR']):assignments.append(line)
 assert set(locations)==set(ports),(set(ports)-set(locations))
 assert len(set(locations.values()))==len(locations)
 qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
 'set_global_assignment -name TOP_LEVEL_ENTITY fxpak_nes_run134_top','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',
 'set_global_assignment -name NUM_PARALLEL_PROCESSORS 4','set_global_assignment -name SEED 1',
 'set_global_assignment -name VHDL_INPUT_VERSION VHDL_2008','set_global_assignment -name STRATIX_DEVICE_IO_STANDARD "3.3-V LVTTL"',
 'set_global_assignment -name SDC_FILE board.sdc']
 for line in base.splitlines():
  if line.startswith('set_global_assignment ') and any('-name '+n+' ' in line for n in ['CYCLONEIII_CONFIGURATION_SCHEME','USE_CONFIGURATION_DEVICE','RESERVE_DATA0_AFTER_CONFIGURATION','RESERVE_DATA1_AFTER_CONFIGURATION','RESERVE_FLASH_NCE_AFTER_CONFIGURATION']):qsf.append(line)
 qsf.append('set_global_assignment -name CYCLONEII_RESERVE_NCEO_AFTER_CONFIGURATION "USE AS REGULAR IO"')
 qsf.append('set_global_assignment -name RESERVE_ALL_UNUSED_PINS "AS INPUT TRI-STATED"')
 qsf+=assignments
 for n in names+['nes_clock_pll123.v','nes_run_observer134.sv','fxpak_nes_run134_top.sv']:
  kind='VHDL_FILE' if n.endswith('.vhd') else ('VERILOG_FILE' if n=='nes_clock_pll123.v' else 'SYSTEMVERILOG_FILE')
  qsf.append('set_global_assignment -name '+kind+' '+n)
 put(o/'board.qsf','\n'.join(qsf)+'\n');put(o/'board.qpf','PROJECT_REVISION = "board"\n')
 put(o/'board.sdc','# Physical clocks only. External electrical/IO bounds remain open.\ncreate_clock -name board8 -period 125 [get_ports CLKIN]\ncreate_clock -name nes -period 45.454 [get_ports SNES_SYSCLK]\nderive_pll_clocks\nderive_clock_uncertainty\n')
 put(o/'pin-map.json',json.dumps(dict(source_sha256=sha(ROOT/'src/fpga/pin.qsf'),ports={n:dict(direction=ports[n],pin=locations[n]) for n in sorted(ports)},physical_bits=len(ports),virtual_bits=0),indent=2)+'\n')
 put(o/'materialization.json',json.dumps(dict(inputs=inputs,hoisted=decls,core_output_sha256=sha(p),scope='Only three observation output wires added; core functional logic unchanged. New physical shell/observer. No SNES consumer.'),indent=2)+'\n')
 return names

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--questa-bin',type=Path);p.add_argument('--prepare-only',action='store_true')
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists()
 names=prepare(a.baseline,o);shutil.copy2(__file__,o/'executed-board134.py')
 if a.prepare_only:print('PREPARED134 physical candidate; no synthesis or fit performed');return
 assert a.questa_bin and re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
 def run(tool,args,label):
  with (o/(label+'.log')).open('wb') as f:r=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=600)
  assert r.returncode==0,label
  return (o/(label+'.log')).read_text(errors='replace')
 run('vlib',['work'],'vlib')
 for i,n in enumerate(VHDL):run('vcom',['-2008',n],f'vcom-{i}')
 run('vlog',['-sv','-mfcu',*[n for n in names if n not in VHDL],'rom_boot_model.sv','run133_pll_model.sv','nes_run_observer134.sv','fxpak_nes_run134_top.sv','board134_tb.sv'],'compile')
 results={}
 for phase in [0,3500]:
  label='normal-'+str(phase);log=run('vsim',['-c','board134_tb',f'+PHASE_PS={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  assert 'PASS134' in log and '** Fatal:' not in log,label
  results[label]=[x for x in log.splitlines() if 'PASS134' in x]
 # Causal control: serving live samples would tear a multi-byte transaction.
 s=(o/'nes_run_observer134.sv').read_text();assert s.count('7:reply=snapshot[7:0]')==1
 put(o/'torn-observer.sv',s.replace('7:reply=snapshot[7:0]','7:reply=samples[7:0]'))
 run('vlog',['-sv','torn-observer.sv'],'torn-compile')
 log=run('vsim',['-c','board134_tb','+PHASE_PS=3500','-do','onerror {quit -code 1}; run -all; quit -f'],'torn-negative')
 assert '** Fatal: BOARD134 coherent snapshot' in log
 results['torn-negative']='expected coherent snapshot failure'
 put(o/'board134.json',json.dumps(dict(passed=True,results=results,physical_trial=False,full_load_check=False,pll_model=True),indent=2)+'\n')
 print('PASS134 physical shell + coherent SPI RUN observer; negative rejected')
if __name__=='__main__':main()
