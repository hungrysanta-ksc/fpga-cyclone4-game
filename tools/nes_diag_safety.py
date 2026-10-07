# SPDX-License-Identifier: MIT
"""068 physical diagnostic: startup guard, preserved067 setup/hold controllers."""
from pathlib import Path
import argparse,json,re,shutil,sys
from nes_diag_memory_timing import materialize as base
from nes_board_diagnostic import constraints
from nes_spi_boot import ROOT,put,run,sha
from nes_rom_geometry import replace

def materialize(out):
    files=base(out)
    name='nes_diag_startup_guard.sv'
    shutil.copy2(ROOT/'src/nes/diagnostic'/name,out/name)
    files.append(name)
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_diag_safe_rom_physical.sv',out/'nes_rom_physical.sv')
    p=out/'nes_h1_spi_boot.sv'
    s=replace(p.read_text(),"command==8'hcf ?8'h67","command==8'hcf ?8'h68")
    s=replace(s,'wire memory_reset=memory_reset_raw||!memory_release[1];',
      '''wire startup_ready;
 nes_diag_startup_guard startup(.clk(nes_clk),.reset(memory_reset_raw),.ready(startup_ready));
 wire memory_reset=memory_reset_raw||!memory_release[1]||!startup_ready;''')
    put(p,s)
    return files

def fit(out,quartus):
    out=out.resolve();assert str(out).isascii();out.mkdir(exist_ok=False,parents=True)
    for n in ['nes_diag_safety.py','nes_diag_memory_timing.py','nes_board_diagnostic.py']:
        shutil.copy2(ROOT/'tools'/n,out/('executed-'+n))
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_diag_startup_guard.sv',out/'executed-guard.txt')
    shutil.copy2(ROOT/'src/nes/diagnostic/nes_diag_safe_rom_physical.sv',out/'executed-reader.txt')
    files=materialize(out);pins=constraints(out)
    run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
    for n in ['h1-program.hex','h1-pattern.hex']:shutil.copy2(out/'h1/build'/n,out/n)
    r=dict(candidate='NES-DIAG-SAFETY-068',identity=0x68,physical_pins=pins,external_io_signoff=False,
           hardware_eligible=False,sources={n:sha(out/n) for n in files+['gbc_bus_pll0.v','board.qsf','board.sdc']},phases={})
    for phase in ['map','fit','sta']:
        run([quartus/('quartus_'+phase+'.exe'),'board'],out,phase,1800)
        r['phases'][phase]=0;put(out/'result.json',json.dumps(r,indent=2)+'\n');print(phase+' complete',flush=True)
    slacks=[float(v) for v in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',(out/'output_files/board.sta.summary').read_text(encoding='latin1'),re.M)]
    assert len(slacks)==30 and min(slacks)>=0
    r['internal_min_slack_ns']=min(slacks)
    put(out/'result.json',json.dumps(r,indent=2)+'\n')
    print((out/'output_files/board.fit.summary').read_text(encoding='latin1'))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--quartus-bin',type=Path)
    a=p.parse_args()
    if a.quartus_bin:fit(a.out,a.quartus_bin)
    else:a.out.mkdir(exist_ok=False,parents=True);materialize(a.out);constraints(a.out)
