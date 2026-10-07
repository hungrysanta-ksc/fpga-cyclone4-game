# SPDX-License-Identifier: MIT
"""Replay frozen060 real C GPIO through068 guarded physical top; bounded phases, not full SPI."""
from pathlib import Path
import argparse, json, os, re, shutil, sys
from nes_diag_safety import materialize
from nes_spi_boot import ROOT, run, sha, put
from nes_rom_geometry import replace
from nes_cf68_mcu import materialize as mcu_materialize
import tempfile


from nes_diag_safety_wave import preflight,testbench

def main():
    p=argparse.ArgumentParser()
    for n in ['out','host-run','questa-bin']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--mutation',choices=['fast-memory','allow-start','connected-start','bypass-startup'])
    a=p.parse_args();assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER',''))
    host=a.host_run.resolve();r=json.loads((host/'result.json').read_text());assert not r['session'] and r['candidate']=='NES-CF68-MCU-069'
    with tempfile.TemporaryDirectory() as d:
        mcu_materialize(Path(d));assert (host/'nes_h1_stm32.c').read_bytes()==(Path(d)/'nes_h1_stm32.c').read_bytes()
    for n,h in r['files'].items():assert sha(host/n)==h,n
    out=a.out.resolve();out.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,out/'executed-driver.py')
    shutil.copy2(ROOT/'tools/nes_diag_safety.py',out/'executed-materializer.py')
    shutil.copy2(ROOT/'tools/nes_diag_safety_wave.py',out/'executed-testbench-generator.py')
    files=materialize(out)
    if a.mutation=='bypass-startup':
        path=out/'nes_h1_spi_boot.sv';put(path,replace(path.read_text(),'||!startup_ready;',';'))
    if a.mutation=='fast-memory':
        path=out/'nes_h1_spi_boot.sv';put(path,replace(path.read_text(),'.mem_clk(nes_clk)', '.mem_clk(clock84)'))
    if a.mutation=='allow-start':
        path=out/'nes_rom_spi.sv';put(path,replace(path.read_text(),"8'h63:fail(8); // 061 diagnostic never permits RUN", "8'h63:if(!verified)fail(8);else start<=1;"))
    if a.mutation=='connected-start':
        path=out/'nes_spi_boot.sv';put(path,replace(path.read_text(),".start(1'b0)",'.start(start)'))
    # This stub checks digital shell wiring/reset only, not analog PLL behavior.
    put(out/'pll_model.sv',"`timescale 1ns/1ps\nmodule gbc_bus_pll0(input areset,inclk0,output reg c0=0,output wire locked);reg enable=1;always #5.952381 if(enable)c0=~c0;assign locked=1'b0;endmodule\n")
    model=(ROOT/'tests/nes-functional/rom_boot_model.sv').read_text().replace('assign #25','assign #(70,70,35)').replace('<35.70','<350')
    put(out/'rom_boot_model.sv',model);put(out/'sd_readback_wave_tb.sv',testbench())
    files+=['pll_model.sv','rom_boot_model.sv','sd_readback_wave_tb.sv']
    run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
    for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
        log=run([a.questa_bin/(tool+'.exe'),*args],out,tool);assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
    cases=[];rom=(host/'banks32/mmc3.nes').read_bytes();assert sha(host/'banks32/mmc3.nes')==r['fixtures']['banks32']
    for mode,wave,key in [('load','load-waveform.txt','load_waveform_sha256'),('check','waveform.txt','waveform_sha256')]:
        c=out/mode;c.mkdir();assert sha(host/wave)==r[key];shutil.copy2(host/wave,c/'waveform.txt')
        for n in ['h1-pattern.hex','h1-program.hex']:shutil.copy2(out/'h1/build'/n,c/n)
        put(c/'expected.hex',''.join(f'{b:02x}\n' for b in rom[16:]))
        put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
        try:
            log=run([a.questa_bin/'vsim.exe','-c','-ini','modelsim.ini','sd_readback_wave_tb','+CHECK='+str(int(mode=='check')),'-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation',1800)
        except RuntimeError:
            if not a.mutation:raise
            log=(c/'simulation.log').read_text(errors='replace')
        if a.mutation:
            # Questa may finish a $fatal with exit0 under run-all/quit-f.
            # Require the causal assertion in the raw transcript either way.
            expected={'bypass-startup':'EARLY_MEMORY_READY','fast-memory':'WRITE pulse too short','allow-start':'061 START rejection missing',
                      'connected-start':'Unexpected RUN'}[a.mutation]
            assert '** Fatal:' in log and expected in log,log[-2000:]
            put(out/'result.json',json.dumps(dict(candidate='NES-CF68-MCU-069',mutation=a.mutation,
              expected_failure=True,assertion=expected,sources={n:sha(out/n) for n in files},
              driver_sha256=sha(out/'executed-driver.py'),materializer_sha256=sha(out/'executed-materializer.py')),indent=2)+'\n')
            print('EXPECTED FAILURE '+a.mutation+': '+expected,flush=True);return
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
        marker=re.search(r'PASS BOARD GPIO[^\r\n]*',log);assert marker
        cases.append(dict(mode=mode,marker=marker[0],waveform_sha256=sha(c/'waveform.txt')));print(marker[0],flush=True)
    assert not a.mutation,'Mutation unexpectedly passed'
    put(out/'result.json',json.dumps(dict(candidate='NES-CF68-MCU-069',cases=cases,
      read_model_ns=70,write_pulse_min_ns=350,output_disable_model_ns=35,
      sources={n:sha(out/n) for n in files},host_result_sha256=sha(host/'result.json'),
      analog_pll=False,hardware_execution=False,driver_sha256=sha(out/'executed-driver.py'),
      materializer_sha256=sha(out/'executed-materializer.py')),indent=2)+'\n')

if __name__=='__main__':main()
