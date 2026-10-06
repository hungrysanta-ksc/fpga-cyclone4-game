# SPDX-License-Identifier: MIT
"""054 materialized044 SPI coexistence and original053 memory boot tests."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess
from nes_h1_sampling import boundary, materialize as h1_materialize

ROOT = Path(__file__).resolve().parents[1]
RTL = ['nes_rom_spi', 'nes_spi_boot', 'nes_rom_loader', 'nes_rom_boot', 'nes_rom_physical']

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def put(path, content):
    path.write_text(content, encoding='utf-8', newline='\n')

def integrated_boundary():
    source = boundary()
    # H1 program-ROM locals must not collide with the new NES backend ports.
    for name in ['rom_data','rom_address']:
        source = re.sub(r'\b'+name+r'\b','h1_'+name,source)
    assert source.count('assign spi_miso=miso_hold;') == 1
    source = source.replace('module nes_h1_board_bus(', '''module nes_h1_spi_boot(
 input wire nes_clk,nes_reset,read_reset,
 output wire load_ready,loaded,nes_run_enable,boot_fault,spi_fault,
 output wire [3:0] boot_error,spi_error,output wire [16:0] loaded_bytes,
 input wire rom_request,input wire [21:0] rom_address,
 output wire rom_ready,rom_response,rom_error,output wire [21:0] rom_response_address,output wire [7:0] rom_data,
 output wire [21:0] psram_address,output wire psram_1ce,psram_2ce,psram_oe,psram_we,psram_bhe,psram_ble,
 inout wire [15:0] psram_data,
''')
    source = source.replace('assign spi_miso=miso_hold;', 'assign spi_miso=loader_selected?loader_miso:miso_hold;')
    source = source.replace(' reg miso_hold=0;', ' wire loader_selected,loader_miso;\n reg miso_hold=0;')
    assert 'wire loader_selected,loader_miso;' in source
    source = source.replace('endmodule', '''
 // H1 diagnostic and NES ROM RUN are distinct; no real NES video consumer here.
 nes_spi_boot loader(.clk(nes_clk),.mem_clk(clock84),.reset(nes_reset||!locked||control_reset),.read_reset(read_reset),
 .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),.spi_miso(loader_miso),.spi_selected(loader_selected),
 .load_ready(load_ready),.loaded(loaded),.run_enable(nes_run_enable),.boot_fault(boot_fault),.spi_fault(spi_fault),
 .boot_error(boot_error),.spi_error(spi_error),.loaded_bytes(loaded_bytes),
 .rom_request(rom_request),.rom_address(rom_address),.rom_ready(rom_ready),.rom_response(rom_response),.rom_error(rom_error),
 .rom_response_address(rom_response_address),.rom_data(rom_data),.psram_address(psram_address),
 .psram_1ce(psram_1ce),.psram_2ce(psram_2ce),.psram_oe(psram_oe),.psram_we(psram_we),
 .psram_bhe(psram_bhe),.psram_ble(psram_ble),.psram_data(psram_data));
endmodule''')
    return source

def run(command, folder, label, timeout=600):
    with (folder / (label + '.log')).open('wb') as log:
        result = subprocess.run([str(x) for x in command], cwd=folder,
                                stdout=log, stderr=subprocess.STDOUT, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f'{label} failed; inspect {folder / (label + ".log")}')
    return (folder / (label + '.log')).read_text(errors='replace')

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--questa-bin',type=Path,required=True)
    p.add_argument('--gcc',type=Path,required=True)
    p.add_argument('--case',choices=['unit','wave'],required=True)
    a=p.parse_args()
    # This host must use the already verified FLOAT route, not inherited files.
    if not re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER','')):
        p.error('Use the existing authorized FLOAT wrapper')
    out=a.out.resolve();out.mkdir()
    for n in RTL:shutil.copyfile(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'))
    shutil.copyfile(ROOT/'tests/nes-functional/rom_boot_model.sv',out/'rom_boot_model.sv')
    files=[n+'.sv' for n in RTL]+['rom_boot_model.sv']
    if a.case=='unit':
        top='rom_spi_tb'
        shutil.copyfile(ROOT/'tests/nes-functional'/f'{top}.sv',out/f'{top}.sv')
    else:
        top='rom_spi_wave_tb'
        for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_h1_pattern_producer']:
            shutil.copyfile(ROOT/'src/nes'/(n+'.sv'),out/(n+'.sv'));files.append(n+'.sv')
        h1_materialize(out)
        for n in ['nes_snes_frontend','nes_transport','nes_h1_pattern']:files.append(n+'.sv')
        put(out/'nes_h1_spi_boot.sv',integrated_boundary());files.append('nes_h1_spi_boot.sv')
        # Original H1 fixtures generated from public sources, no user ROM.
        run([os.sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
        for n in ['h1-pattern.hex','h1-program.hex']:shutil.copyfile(out/'h1/build'/n,out/n)
        shutil.copyfile(ROOT/'tests/nes-functional'/f'{top}.sv',out/f'{top}.sv')
        for n in ['nes_rom_spi.c','nes_rom_spi.h']:shutil.copyfile(ROOT/'src/nes/firmware'/n,out/n)
        shutil.copyfile(ROOT/'tests/nes-functional/rom_spi_capture.c',out/'rom_spi_capture.c')
        run([a.gcc,'-std=c11','-D__USE_MINGW_ANSI_STDIO=1','-Wall','-Wextra','-Werror','-O2',
             'nes_rom_spi.c','rom_spi_capture.c','-o','capture.exe'],out,'host_compile')
        run([out/'capture.exe',out/'waveform.txt'],out,'capture')
    files.append(top+'.sv')
    sources={n:sha(out/n) for n in files}
    for tool,args in [('vlib',['work']),('vlog',['-sv',*files]),('vsim',['-c',top,'-do','onerror {quit -code 1}; run -all; quit -f'])]:
        log=run([a.questa_bin/(tool+'.exe'),*args],out,tool)
        if re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log):raise RuntimeError('Inspect '+tool+'.log')
    marker='PASS SPI BOOT' if a.case=='unit' else 'PASS SPI MCU WAVE'
    match=re.search(marker+r'[^\r\n]*',log)
    if not match:raise RuntimeError('Missing completion marker')
    result=dict(candidate='NES-R1-SPI-BOOT-054',case=a.case,passed=True,marker=match[0],sources=sources,
                hardware_image=False,full_core_execution=False,driver_sha256=sha(Path(__file__)))
    if a.case=='wave':
        result['firmware_sources']={n:sha(out/n) for n in ['nes_rom_spi.c','nes_rom_spi.h','rom_spi_capture.c']}
        result['waveform_sha256']=sha(out/'waveform.txt')
    put(out/'result.json',json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))

if __name__=='__main__':main()
