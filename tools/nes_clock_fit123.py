# SPDX-License-Identifier: MIT
"""123 feasibility: actual core+safe reader+PLL, physical PSRAM/clock pins.
Virtual control/video observation ports remain. No loader, guard, install image.
"""
from pathlib import Path
import argparse,json,hashlib,shutil,subprocess,re,difflib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')
def main():
 p=argparse.ArgumentParser()
 for n in ('baseline','out','quartus-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();o=a.out.resolve();assert str(o).isascii() and not o.exists();o.mkdir()
 baseline=json.loads((ROOT/'analysis/spi-readback-verification.json').read_bytes())['runs']['fit']
 assert json.loads((a.baseline/'result.json').read_bytes())==baseline
 for n,h in baseline['sources'].items():
  assert sha(a.baseline/n)==h,n
  d=o/n;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(a.baseline/n,d)
 shutil.copy2(__file__,o/'executed-driver.py')
 shutil.copy2(ROOT/'src/nes/diagnostic/nes_diag_safe_rom_physical.sv',o/'nes_rom_physical.sv')
 original=(o/'nes_live_joint.sv').read_text();s=original
 def edit(before,after):
  nonlocal s
  assert s.count(before)==1,before;s=s.replace(before,after)
 edit('input wire  ext_host_clk,','input wire CLKIN,\ninput wire ext_chr32,')
 edit('input wire ext_mem_clk,','')
 edit('wire queue_clk=ext_clk,clk=ext_clk,host_clk=ext_host_clk,boot_reset=ext_reset;',
 '''wire ext_host_clk,ext_mem_clk,locked;
 nes_clock_pll123 pll(.areset(ext_reset),.inclk0(CLKIN),.c0(ext_host_clk),.c1(ext_mem_clk),.locked(locked));
 wire queue_clk=ext_clk,clk=ext_clk,host_clk=ext_host_clk,boot_reset=ext_reset||!locked;''')
 start=s.index('nes_spi_boot physical(');end=s.index('wire rom_cpu_address_valid',start)
 s=s[:start]+'''// Read-only feasibility slice. Virtual ext_arm supplies RUN; no loader.
 assign run_enable=ext_arm&&!boot_reset;
 assign chr_32k=ext_chr32;
 assign load_ready=0;assign loaded=0;assign boot_fault=0;assign boot_error=0;assign loaded_bytes=0;
 assign out_spi_miso=0;assign out_spi_selected=0;assign out_spi_fault=0;assign out_spi_error=0;
 assign ext_psram_data=16'hzzzz;
 nes_rom_physical #(.READ_CYCLES(16)) physical(
 .clk(clk),.mem_clk(mem_clk),.reset(reset),
 .check_mode(1'b0),.check_request(1'b0),.check_address(22'd0),
 .check_ready(),.check_response(),.check_response_address(),.check_data(),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rom_ready),
 .rom_response(rom_response),.rom_error(rom_error),.rom_response_address(rom_response_address),.rom_data(rom_data),
 .psram_address(psram_address),.psram_1ce(psram_1ce),.psram_2ce(psram_2ce),
 .psram_oe(psram_oe),.psram_we(psram_we),.psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(ext_psram_data));
 '''+s[end:]
 # Do not let direct PPU observation aliases turn into extra physical IO.
 # This virtual debug register is outside every functional datapath.
 edit('assign out_ppumem_addr=ppumem_addr;', '''(* preserve *) reg [21:0] debug_ppu_address;
 always @(posedge clk) debug_ppu_address<=ppumem_addr;
 assign out_ppumem_addr=debug_ppu_address;''')
 put(o/'nes_live_joint.sv',s)
 put(o/'top.diff',''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='059/top',tofile='123/top')))
 pll=(ROOT/'src/fpga/gbc_bus_pll0.v').read_text();pll=pll.replace('module gbc_bus_pll0 (','module nes_clock_pll123 (').replace('\tc0,','\tc0,\n\tc1,').replace('\toutput\t  c0;','\toutput\t  c0;\n\toutput wire c1;').replace('\twire  locked = sub_wire5;','\twire  locked = sub_wire5;\n\tassign c1=sub_wire3[1];').replace('altpll_component.port_clk1 = "PORT_UNUSED"','altpll_component.port_clk1 = "PORT_USED"')
 pll=pll.replace('altpll_component.clk0_phase_shift = "0",','''altpll_component.clk0_phase_shift = "0",
        altpll_component.clk1_divide_by = 1,
        altpll_component.clk1_multiply_by = 21,
        altpll_component.clk1_duty_cycle = 50,
        altpll_component.clk1_phase_shift = "0",''')
 put(o/'nes_clock_pll123.v',pll)
 mapping={'CLKIN':'CLKIN','SNES_SYSCLK':'ext_clk','ROM_ADDR':'out_psram_address','ROM_DATA':'ext_psram_data',**{'ROM_'+k:'out_psram_'+v for k,v in [('1CE','1ce'),('2CE','2ce'),('OE','oe'),('WE','we'),('BHE','bhe'),('BLE','ble')]}}
 assignments=[];pins=[]
 for line in (ROOT/'src/fpga/pin.qsf').read_text().splitlines():
  if ' -to ' not in line:continue
  target=line.split(' -to ')[-1].strip('"');bus=target.split('[')[0]
  if bus not in mapping:continue
  if line.startswith('set_location_assignment ') or (line.startswith('set_instance_assignment ') and any('-name '+n+' ' in line for n in ('IO_STANDARD','CURRENT_STRENGTH_NEW','WEAK_PULL_UP_RESISTOR'))):
   line=line[:line.index(' -to ')]+ ' -to '+mapping[bus]+target[len(bus):];assignments.append(line)
   if line.startswith('set_location'):pins.append(line)
 assert len(pins)==46 and len(set(line.split()[1] for line in pins))==46
 q=(o/'live.qsf').read_text().splitlines();physical=set(mapping.values())
 q=[line for line in q if not ('VIRTUAL_PIN' in line and line.split(' -to ')[-1] in physical) and not any(line.endswith(' '+n+'.sv') for n in ('nes_rom_loader','nes_rom_boot','nes_rom_spi','nes_spi_boot'))]
 q+=['set_instance_assignment -name VIRTUAL_PIN ON -to ext_chr32','set_global_assignment -name VERILOG_FILE nes_clock_pll123.v',*assignments]
 q+=['set_global_assignment -name CYCLONEIII_CONFIGURATION_SCHEME "PASSIVE SERIAL"','set_global_assignment -name USE_CONFIGURATION_DEVICE OFF','set_global_assignment -name CYCLONEII_RESERVE_NCEO_AFTER_CONFIGURATION "USE AS REGULAR IO"']
 put(o/'live.qsf','\n'.join(q)+'\n');shutil.copy2(o/'live.qsf',o/'input-live.qsf.txt')
 put(o/'live.sdc','''# Feasibility only: physical clock inputs and PLL-generated84/168MHz.
create_clock -name board8 -period 125 [get_ports CLKIN]
# Conservative22MHz timing target; nominal NES functional clock is21.477MHz.
create_clock -name nes -period 45.454 [get_ports ext_clk]
derive_pll_clocks
derive_clock_uncertainty
# NO blanket false paths or fabricated external IO budgets.
# Raw CDC/recovery/IO limits remain visible; this is not release signoff.
''')
 sources={n:sha(o/n) for n in baseline['sources'] if n not in ('live.qsf',)}
 sources.update({n:sha(o/n) for n in ('input-live.qsf.txt','nes_clock_pll123.v','top.diff','executed-driver.py')})
 m=dict(candidate='NES-CLOCK-FIT-123',sources=sources,baseline_sources=baseline['sources'],public_inputs={n:sha(ROOT/n) for n in ('src/fpga/pin.qsf','src/fpga/gbc_bus_pll0.v','src/nes/diagnostic/nes_diag_safe_rom_physical.sv')},physical_pin_assignments=pins,phases={},installable=False,loader_present=False,guard_present=False,virtual_control_and_observation_ports=True,read_cycles=16,scope='Actual core read-only resource/clock feasibility. Physical PSRAM+clock pins, virtual SNES/control/debug. Not final full board, external IO or CDC signoff.')
 def save():put(o/'result.json',json.dumps(m,indent=2)+'\n')
 save()
 for phase in ('map','fit','sta'):
  with (o/(phase+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/('quartus_'+phase+'.exe')),'live'],cwd=o,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  m['phases'][phase]=r.returncode;save();print(phase,r.returncode,flush=True)
  if r.returncode:raise SystemExit(r.returncode)
 m['fit_summary']=(o/'output_files/live.fit.summary').read_text();m['sta_summary']=(o/'output_files/live.sta.summary').read_text()
 m['raw_slacks_ns']=[float(x) for x in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',m['sta_summary'],re.M)]
 m['all_constrained_timing_pass']=bool(m['raw_slacks_ns']) and min(m['raw_slacks_ns'])>=0
 save();print(m['fit_summary']);print('raw minimum slack',min(m['raw_slacks_ns']),flush=True)
if __name__=='__main__':main()
