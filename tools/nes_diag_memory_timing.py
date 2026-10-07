# SPDX-License-Identifier: MIT
"""067: diagnostic-only setup/hold phases; historical061/full-core stay unchanged."""
from pathlib import Path
import argparse, shutil, json, sys, re
from nes_board_diagnostic import materialize as base, constraints
from nes_spi_boot import ROOT, put, run, sha
from nes_rom_geometry import replace


def materialize(out):
    files = base(out)
    for role in ['loader', 'physical']:
        shutil.copy2(ROOT/'src/nes/diagnostic'/('nes_diag_rom_'+role+'.sv'),
                     out/('nes_rom_'+role+'.sv'))
    p = out/'nes_h1_spi_boot.sv'
    put(p, replace(p.read_text(), "command==8'hcf ?8'h61", "command==8'hcf ?8'h67"))
    return files


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--quartus-bin', type=Path)
    a = p.parse_args()
    a.out.mkdir(parents=True, exist_ok=False)
    files=materialize(a.out)
    pins=constraints(a.out)
    if a.quartus_bin:
        assert str(a.out.resolve()).isascii()
        shutil.copy2(__file__,a.out/'executed-driver.py')
        run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',a.out/'h1'],a.out,'fixture')
        for n in ['h1-program.hex','h1-pattern.hex']:
            shutil.copy2(a.out/'h1/build'/n,a.out/n)
        result=dict(candidate='NES-DIAG-MEMORY-067',physical_pins=pins,external_io_constrained=False,
                    hardware_eligible=False,phases={},sources={n:sha(a.out/n) for n in files+['board.qsf','board.sdc','gbc_bus_pll0.v']})
        for phase in ['map','fit','sta']:
            run([a.quartus_bin/('quartus_'+phase+'.exe'),'board'],a.out,phase,1800)
            result['phases'][phase]=0
            put(a.out/'result.json',json.dumps(result,indent=2)+'\n')
            print(phase+' complete',flush=True)
        summary=(a.out/'output_files/board.sta.summary').read_text(encoding='latin-1')
        slacks=[float(v) for v in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',summary,re.M)]
        assert len(slacks)==30
        result['internal_min_slack_ns']=min(slacks)
        put(a.out/'result.json',json.dumps(result,indent=2)+'\n')
        assert min(slacks)>=0, 'Negative internal timing; inspect raw STA'
        print((a.out/'output_files/board.fit.summary').read_text(encoding='latin-1'),flush=True)
