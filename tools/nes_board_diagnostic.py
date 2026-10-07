# SPDX-License-Identifier: MIT
"""061 load/CHECK-only physical shell. External timing qualification is pending."""
from pathlib import Path
import argparse, json, os, re, shutil, sys
from nes_spi_boot import ROOT, RTL, integrated_boundary, h1_materialize, run, sha, put
from nes_spi_readback import materialize as spi_materialize
from nes_rom_geometry import replace


def materialize(out):
    spi_materialize(out)
    h1_materialize(out)
    # Two independent barriers: reject START in the parser and disconnect it
    # from the loader. A verified image never authorizes CPU execution here.
    p=out/'nes_rom_spi.sv'
    put(p,replace(p.read_text(),"8'h63:if(!verified)fail(8);else start<=1;",
                  "8'h63:fail(8); // 061 diagnostic never permits RUN"))
    p=out/'nes_spi_boot.sv'
    before,boot=p.read_text().split('nes_rom_boot boot(',1)
    put(p,before+'nes_rom_boot boot('+replace(boot,'.start(start)',".start(1'b0)"))
    s=integrated_boundary()
    s=replace(s,'input wire nes_clk,nes_reset,read_reset,','input wire nes_clk,nes_reset,read_reset, output wire memory_ready,')
    # clock84 still belongs to unchanged044; all SPI/PSRAM state uses board8.
    s=replace(s,'nes_spi_boot loader(.clk(nes_clk),.mem_clk(clock84),.reset(nes_reset||!locked||control_reset)',
      '''// Each domain releases independently from raw PLL loss. Do not route
 // the84MHz release flop into the8MHz state machine's reset data paths.
 wire memory_reset_raw=nes_reset||!locked;
 (* altera_attribute="-name SYNCHRONIZER_IDENTIFICATION FORCED_IF_ASYNCHRONOUS" *) reg [1:0] memory_release=0;
 always @(posedge nes_clk or posedge memory_reset_raw)
  if(memory_reset_raw)memory_release<=0;else memory_release<={memory_release[0],1'b1};
 wire memory_reset=memory_reset_raw||!memory_release[1];
 assign memory_ready=!memory_reset;
 nes_spi_boot loader(.clk(nes_clk),.mem_clk(nes_clk),.reset(memory_reset)''')
    s=replace(s,'.load_ready(load_ready)', '.rom_chr32(),.load_ready(load_ready)')
    # Preserve F0/F1 and F2 status semantics. Separate physical candidate ID.
    s=replace(s,"wire [7:0] reply=command==8'hf0", "wire [7:0] reply=command==8'hcf ?8'h61:command==8'hf0")
    put(out/'nes_h1_spi_boot.sv',s)
    s=(ROOT/'src/nes/fxpak_nes_h1_top.sv').read_text()
    s=replace(s,'module fxpak_nes_h1_top(', 'module fxpak_nes_diagnostic_top(')
    s=replace(s,'// H1 diagnostic physical pin shell034. No NES game core or external memory service.',
      '// 061 physical load/CHECK-only shell. No NES CPU/PPU; not yet hardware qualified.')
    s=replace(s,'nes_h1_board_bus boundary(', '''wire memory_ready;
 nes_h1_spi_boot boundary(.memory_ready(memory_ready),.nes_clk(CLKIN),.nes_reset(1'b0),.read_reset(1'b1),
  .load_ready(),.loaded(),.nes_run_enable(),.boot_fault(),.spi_fault(),.boot_error(),.spi_error(),.loaded_bytes(),
  .rom_request(1'b0),.rom_address(22'd0),.rom_ready(),.rom_response(),.rom_error(),.rom_response_address(),.rom_data(),
  .psram_address(ROM_ADDR),.psram_1ce(ROM_1CE),.psram_2ce(ROM_2CE),.psram_oe(ROM_OE),.psram_we(ROM_WE),
  .psram_bhe(ROM_BHE),.psram_ble(ROM_BLE),.psram_data(ROM_DATA),''')
    s=replace(s,'assign MCU_RDY=locked;', 'assign MCU_RDY=locked&&memory_ready;')
    s=replace(s,'assign ROM_ADDR=0;assign ROM_1CE=1;assign ROM_2CE=1;assign ROM_ZZ=1;\n assign ROM_OE=1;assign ROM_WE=1;assign ROM_BHE=1;assign ROM_BLE=1;assign ROM_DATA=16\'hzzzz;', 'assign ROM_ZZ=1;')
    put(out/'fxpak_nes_diagnostic_top.sv',s)
    for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_h1_pattern_producer']:
        shutil.copy2(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
    shutil.copy2(ROOT/'src/fpga/gbc_bus_pll0.v',out/'gbc_bus_pll0.v')
    return [n+'.sv' for n in RTL+['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage',
      'nes_h1_pattern_producer','nes_snes_frontend','nes_transport','nes_h1_pattern','nes_h1_spi_boot','fxpak_nes_diagnostic_top']]


def constraints(out):
    top=(out/'fxpak_nes_diagnostic_top.sv').read_text().split('module fxpak_nes_diagnostic_top(',1)[1].split(');',1)[0]
    ports=set(re.findall(r'\b[A-Z][A-Z_0-9]*\b',top))
    assignments=[]
    for line in (ROOT/'src/fpga/pin.qsf').read_text().splitlines():
        if line.startswith('set_location_assignment ') or (line.startswith('set_instance_assignment ') and
           any('-name '+n+' ' in line for n in ['IO_STANDARD','CURRENT_STRENGTH_NEW','WEAK_PULL_UP_RESISTOR'])):
            if line.split(' -to ',1)[-1].strip('"').split('[')[0] in ports:assignments.append(line)
    pins=[s for s in assignments if s.startswith('set_location')]
    assert {s.split(' -to ')[1].split('[')[0] for s in pins}==ports
    # Every scalar/vector bit is assigned exactly once, not just each bus name.
    bits=[]
    for width,names in re.findall(r'(?:input|output|inout)\s+wire\s*(\[[^]]+\])?\s*([A-Z][A-Z_0-9]*(?:\s*,\s*[A-Z][A-Z_0-9]*)*)',top):
        for name in names.replace(' ','').split(','):
            bits.extend([name+f'[{i}]' for i in range(int(width[1:].split(':')[0])+1)] if width else [name])
    targets=[s.split(' -to ')[1] for s in pins]
    assert len(targets)==len(set(targets)) and set(bits)==set(targets),(set(bits)-set(targets),set(targets)-set(bits))
    assert len({s.split()[1] for s in pins})==len(pins),'Duplicate physical pin'
    qsf=['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8',
      'set_global_assignment -name TOP_LEVEL_ENTITY fxpak_nes_diagnostic_top',
      'set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files','set_global_assignment -name NUM_PARALLEL_PROCESSORS 4',
      'set_global_assignment -name SEED 1','set_global_assignment -name SDC_FILE board.sdc',
      'set_global_assignment -name CYCLONEIII_CONFIGURATION_SCHEME "PASSIVE SERIAL"',
      'set_global_assignment -name USE_CONFIGURATION_DEVICE OFF',
      'set_global_assignment -name CYCLONEII_RESERVE_NCEO_AFTER_CONFIGURATION "USE AS REGULAR IO"']
    qsf += ['set_global_assignment -name '+n+' "USE AS REGULAR IO"' for n in
      ['RESERVE_DATA0_AFTER_CONFIGURATION','RESERVE_DATA1_AFTER_CONFIGURATION','RESERVE_FLASH_NCE_AFTER_CONFIGURATION']]
    qsf+=assignments
    qsf += ['set_global_assignment -name '+('VERILOG_FILE ' if n.suffix=='.v' else 'SYSTEMVERILOG_FILE ')+n.name
      for n in sorted(out.glob('*')) if n.suffix in ['.v','.sv']]
    put(out/'board.qsf','\n'.join(qsf)+'\n');put(out/'board.qpf','PROJECT_REVISION = "board"\n')
    put(out/'board.sdc','''# 061 actual board8 PSRAM/SPI and unchanged H1 PLL84.
create_clock -name board8 -period 125 [get_ports CLKIN]
derive_pll_clocks
derive_clock_uncertainty
# NO external IO timing envelope or false-path waiver is invented.
# Unconstrained IO is an explicit hardware-release blocker.
''')
    return len(pins)


def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True)
    p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args()
    out=a.out.resolve();assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'executed-driver.py');files=materialize(out);pins=constraints(out)
    run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
    for n in ['h1-program.hex','h1-pattern.hex']:shutil.copy2(out/'h1/build'/n,out/n)
    m=dict(candidate='NES-BOARD-DIAGNOSTIC-061',hardware_eligible=False,physical_pin_assignments=pins,
      memory_clock_mhz=8,cpu_ppu_present=False,external_io_constrained=False,
      sources={n:sha(out/n) for n in files+['gbc_bus_pll0.v','board.qsf','board.sdc']},
      pin_source_sha256=sha(ROOT/'src/fpga/pin.qsf'),driver_sha256=sha(out/'executed-driver.py'),phases={})
    for phase in ['map','fit','sta']:
        run([a.quartus_bin/('quartus_'+phase+'.exe'),'board'],out,phase,1200)
        m['phases'][phase]=0;put(out/'result.json',json.dumps(m,indent=2)+'\n');print(phase+' completed',flush=True)
    summary=(out/'output_files/board.sta.summary').read_text(encoding='latin-1')
    slacks=[float(v) for v in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',summary,re.M)]
    assert len(slacks)==30,'Expected both clocks at all three timing corners'
    m['internal_min_slack_ns']=min(slacks);m['internal_timing_pass']=min(slacks)>=0
    put(out/'result.json',json.dumps(m,indent=2)+'\n')
    assert m['internal_timing_pass'],'Inspect raw STA; tool exit success is not timing success'
    print((out/'output_files/board.fit.summary').read_text(encoding='latin-1'),flush=True)

if __name__=='__main__':main()
