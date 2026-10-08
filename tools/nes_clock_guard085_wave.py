# SPDX-License-Identifier: MIT
"""Actual CF85 shell: frozen060 C GPIO plus directed single-clock fault tests.

Digital stimulus only; no hardware/analog PLL/CDC/fit approval. Both-clock stop
is deliberately retained as a counterexample, not classified as safe.
"""
from pathlib import Path
import argparse, json, os, re, shutil, sys
from nes_clock_guard085 import materialize
from nes_diag_safety_wave import testbench as base_tb
from nes_sd_readback import source
from nes_rom_geometry import replace
from nes_spi_boot import ROOT, run, sha, put


def testbench():
    s = base_tb()
    s = replace(s, 'wire clock84;', '''wire clock84;
 reg ref_clk=0,ref_enable=0; real ref_half=25.0;
 initial begin if($value$plusargs("REF_HALF=%f",ref_half))begin end end
 always begin #(ref_half);if(ref_enable)ref_clk=~ref_clk;end''')
    s = replace(s, ".SNES_SYSCLK(1'b0)", '.SNES_SYSCLK(ref_clk)')
    s = s.replace("8'hcf,8'h68", "8'hcf,8'h85")
    s = replace(s, 'rom_boot_model memory(.reset(nes_reset||!locked),.*);',
                'rom_boot_model memory(.reset(nes_reset||!locked||!dut.clock_allowed),.*);')
    s = replace(s, '#500;locked=1;nes_reset=0;#1000;', '''#500;locked=1;nes_reset=0;#10000;
  if(mcu_ready||!psram_1ce||!psram_2ce||!psram_we||!psram_oe)
   $fatal(1,"MISSING_REFERENCE_NOT_BLOCKED");
  ref_enable=1;#10000;
  if(mcu_ready||!dut.clock_fault)$fatal(1,"STARTUP_FAULT_NOT_STICKY");
  locked=0;#100;locked=1;#1000;''')
    old = '''#100;clock_enable=0;#9000;
  // Adversarial locked-high clock halt: internal logic cannot release CE.
  // This is a preserved counterexample, not a timing or hardware pass.
  if(psram_we||(psram_1ce&&psram_2ce))$fatal(1,"CLOCK_HALT_COUNTEREXAMPLE_MISSING");
  $display("CLOCK_HALT_COUNTEREXAMPLE locked_high_ce_low_over_8us=1");
  dut.pll.enable=0;locked=0;#1;'''
    new = '''#100;clock_enable=0;dut.pll.enable=0;#5000;
  if(!psram_we||!psram_1ce||!psram_2ce||mcu_ready||!dut.clock_fault)
   $fatal(1,"SINGLE_CLOCK_HALT_NOT_CONTAINED");
  clock_enable=1;dut.pll.enable=1;#250000;
  if(mcu_ready||!psram_we||!psram_1ce||!psram_2ce||loaded||loaded_bytes)
   $fatal(1,"FAULT_REARMED_WITHOUT_RESET");
  $display("SINGLE_CLOCK_HALT_CONTAINED sticky=1 image_invalid=1");
  dut.pll.enable=0;locked=0;#1;'''
    s = replace(s, old, new)
    s = replace(s, '  // PLL loss invalidates the ROM path and cuts pin/MISO drive immediately.',
                '''  $display("PASS C_PREFIX085 pin_bytes=%0d checked=%0d verified_bytes=%0d",memory.writes,checked,check_mode?256:0);
  // PLL loss invalidates the ROM path and cuts pin/MISO drive immediately.''')
    tasks = (ROOT/'tests/nes-functional/clock_guard085_tasks.svh').read_text()
    s = replace(s, ' task automatic prepare;', tasks+'\n task automatic prepare;')
    s = replace(s, '  $display("PASS BOARD GPIO', '  directed_clock_faults();\n  $display("PASS BOARD GPIO')
    return s


def preflight():
    s = testbench()
    assert s.index('wire [3:0] boot_error,') < s.index('task automatic command(')
    assert s.count('task automatic directed_clock_faults;') == 1


def main():
    p = argparse.ArgumentParser()
    for name in ['out', 'host-run', 'questa-bin']:
        p.add_argument('--'+name, type=Path, required=True)
    p.add_argument('--mutation', choices=['bypass-guard', 'same-clock', 'nonsticky'])
    a = p.parse_args()
    assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)', os.environ.get('SALT_LICENSE_SERVER',''))
    host = a.host_run.resolve()
    r = json.loads((host/'result.json').read_text())
    assert r['host_model_pass'] and r['candidate'] == 'NES-SD-READBACK-060'
    assert (host/'nes_h1_stm32.c').read_text() == source()
    for n,h in r['files'].items(): assert sha(host/n) == h,n
    out = a.out.resolve(); out.mkdir(parents=True,exist_ok=False)
    for path in [Path(__file__), ROOT/'tools/nes_clock_guard085.py',
                 ROOT/'tools/nes_diag_safety_wave.py', ROOT/'tests/nes-functional/clock_guard085_tasks.svh']:
        shutil.copy2(path, out/('executed-'+path.name))
    files = materialize(out)
    top = out/'fxpak_nes_diagnostic_top.sv'
    if a.mutation == 'bypass-guard':
        put(top, replace(top.read_text(), '.nes_reset(!clock_allowed)', ".nes_reset(1'b0)"))
    if a.mutation == 'same-clock':
        put(top, replace(top.read_text(), '.ref_clk(SNES_SYSCLK)', '.ref_clk(CLKIN)'))
    if a.mutation == 'nonsticky':
        guard = out/'nes_diag_clock_guard085.sv'
        text = guard.read_text().replace('else if(!ref_fault)begin', 'else begin').replace('else if(!mem_fault)begin', 'else begin')
        text = replace(text, 'mem_seen<=mem_sync[1];ref_age<=0;', 'mem_seen<=mem_sync[1];ref_age<=0;ref_fault<=0;')
        text = replace(text, 'ref_seen<=ref_sync[1];mem_age<=0;', 'ref_seen<=ref_sync[1];mem_age<=0;mem_fault<=0;')
        put(guard,text)
    put(out/'pll_model.sv', "`timescale 1ns/1ps\nmodule gbc_bus_pll0(input areset,inclk0,output reg c0=0,output wire locked);reg enable=1;always #5.952381 if(enable)c0=~c0;assign locked=1'b0;endmodule\n")
    model = (ROOT/'tests/nes-functional/rom_boot_model.sv').read_text().replace('assign #25','assign #(70,70,35)').replace('<35.70','<350')
    put(out/'rom_boot_model.sv',model); put(out/'sd_readback_wave_tb.sv',testbench())
    files += ['pll_model.sv','rom_boot_model.sv','sd_readback_wave_tb.sv']
    run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
    for tool,args in [('vlib',['work']),('vlog',['-sv',*files])]:
        log = run([a.questa_bin/(tool+'.exe'),*args],out,tool)
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log)
    rom = (host/'banks32/mmc3.nes').read_bytes()
    assert sha(host/'banks32/mmc3.nes') == r['fixtures']['banks32']
    cases = []
    matrix = [('load',25.0),('check',25.0),('load',22.727273),('load',23.280423)]
    if a.mutation: matrix = matrix[:1]
    for index,(mode,half) in enumerate(matrix):
        c = out/f'{index:02d}-{mode}'; c.mkdir()
        wave,key = ('load-waveform.txt','load_waveform_sha256') if mode=='load' else ('waveform.txt','waveform_sha256')
        assert sha(host/wave)==r[key]; shutil.copy2(host/wave,c/'waveform.txt')
        for name in ['h1-pattern.hex','h1-program.hex']: shutil.copy2(out/'h1/build'/name,c/name)
        put(c/'expected.hex',''.join(f'{b:02x}\n' for b in rom[16:]))
        put(c/'modelsim.ini','[Library]\nwork = '+(out/'work').as_posix()+'\nothers = '+(a.questa_bin.parent/'modelsim.ini').as_posix()+'\n')
        try:
            log=run([a.questa_bin/'vsim.exe','-c','-ini','modelsim.ini','sd_readback_wave_tb',
                     '+CHECK='+str(int(mode=='check')),f'+REF_HALF={half}',
                     '-do','onerror {quit -code 1}; run -all; quit -f'],c,'simulation',1800)
        except RuntimeError:
            if not a.mutation: raise
            log=(c/'simulation.log').read_text(errors='replace')
        if a.mutation:
            expected={'bypass-guard':'SINGLE_CLOCK_HALT_NOT_CONTAINED',
                      'same-clock':'STARTUP_FAULT_NOT_STICKY','nonsticky':'STARTUP_FAULT_NOT_STICKY'}[a.mutation]
            assert '** Fatal:' in log and expected in log,log[-2500:]
            cases.append(dict(mutation=a.mutation,expected_failure=True,assertion=expected));break
        assert not re.search(r'\*\* (?:Fatal|Error)(?:\s|:)',log),log[-2500:]
        marker=re.search(r'PASS BOARD GPIO[^\r\n]*',log); assert marker
        faults=re.search(r'PASS CLOCK085 directed=(\d+) max_abort_ns=([0-9.]+) both_stop_counterexample=1',log);assert faults
        ce=re.search(r'PASS CE085 max_low_ns=([0-9.]+) both_stop_excluded=1',log);assert ce
        prefix=re.search(r'PASS C_PREFIX085 pin_bytes=(\d+) checked=(\d+) verified_bytes=(\d+)',log);assert prefix
        assert (int(prefix[1]),int(prefix[2]),int(prefix[3])) == ((98304,43288,256) if mode=='check' else (256,29024,0))
        assert int(faults[1])==32 and float(faults[2])<=5000 and float(ce[1])<=8000
        cases.append(dict(mode=mode,reference_half_ns=half,marker=marker[0],directed_cases=int(faults[1]),
                          max_abort_ns=float(faults[2]),max_ce_low_ns=float(ce[1]),prefix_pin_bytes=int(prefix[1]),
                          checked_response_bits=int(prefix[2]),verified_bytes=int(prefix[3]),waveform_sha256=sha(c/'waveform.txt')))
        print(marker[0]+' '+faults[0],flush=True)
    result=dict(candidate='NES-CLOCK-GUARD-085',cases=cases,mutation=a.mutation,
                sources={n:sha(out/n) for n in files},host_result_sha256=sha(host/'result.json'),
                executed_inputs={p.name:sha(p) for p in out.glob('executed-*')},
                digital_only=True,analog_pll=False,full_spi_session=False,hardware_execution=False,
                fit_sta_verified=False,external_io_signoff=False,both_clock_halt_safe=False,installable=False)
    put(out/'result.json',json.dumps(result,indent=2)+'\n')


if __name__=='__main__': main()
