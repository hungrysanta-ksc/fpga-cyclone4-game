# SPDX-License-Identifier: MIT
"""Characterize CF85 or corrected CF86; exact CDC exceptions require routed audit."""
from pathlib import Path
import argparse,json,re,shutil,sys
from nes_clock_guard085 import materialize as original
from nes_clock_reset086 import materialize as corrected
from nes_board_diagnostic import constraints
from nes_spi_boot import ROOT,put,run,sha


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--quartus-bin',type=Path,required=True)
    p.add_argument('--corrected',action='store_true')
    p.add_argument('--cdc-constraints',action='store_true')
    a=p.parse_args();out=a.out.resolve()
    assert not a.cdc_constraints or a.corrected
    assert str(out).isascii();out.mkdir(parents=True,exist_ok=False)
    shutil.copy2(__file__,out/'executed-driver.py')
    files=(corrected if a.corrected else original)(out);pins=constraints(out)
    # First characterization retains ALL crossings. No blanket clock groups or
    # false paths hide guard qualification/fault/reset paths from inspection.
    with (out/'board.sdc').open('a',encoding='utf-8') as f:
        f.write('\n# 086 measurement assumption: maximum22MHz reference, not measured hardware.\n')
        f.write('create_clock -name snes_ref -period 45.454 [get_ports SNES_SYSCLK]\n')
        if a.cdc_constraints:
            shutil.copy2(ROOT/'tools/nes_clock_cdc086.sdc',out/'clock-cdc086.sdc')
            f.write('source clock-cdc086.sdc\n')
    shutil.copy2(out/'board.qsf',out/'input-board.qsf.txt')
    run([sys.executable,'-B',ROOT/'tools/build_nes_h1_board.py','--out',out/'h1'],out,'fixture')
    for n in ['h1-program.hex','h1-pattern.hex']:shutil.copy2(out/'h1/build'/n,out/n)
    inputs=files+['gbc_bus_pll0.v','board.sdc','input-board.qsf.txt','h1-program.hex','h1-pattern.hex']
    if a.cdc_constraints:inputs.append('clock-cdc086.sdc')
    result=dict(candidate='NES-CLOCK-TIMING-086',rtl_candidate='NES-CLOCK-RESET-086' if a.corrected else 'NES-CLOCK-GUARD-085',identity_hex='86' if a.corrected else '85',
                physical_pins=pins,sources={n:sha(out/n) for n in inputs},phases={},
                reference_period_ns=45.454,asynchronous_crossings_not_waived=not a.cdc_constraints,
                external_io_signoff=False,hardware_execution=False,installable=False)
    for phase in ['map','fit','sta']:
        log=run([a.quartus_bin/('quartus_'+phase+'.exe'),'board'],out,phase,1800)
        result['phases'][phase]=0;put(out/'result.json',json.dumps(result,indent=2)+'\n')
        print(phase+' completed',flush=True)
    summary=(out/'output_files/board.sta.summary').read_text(encoding='latin1')
    slacks=[float(x) for x in re.findall(r'^Slack\s*:\s*(-?[0-9.]+)',summary,re.M)]
    assert len(slacks)>=30
    result.update(summary_slacks=slacks,minimum_reported_slack_ns=min(slacks),
                  negative_summary_count=sum(x<0 for x in slacks),
                  internal_timing_signoff=False)
    put(out/'result.json',json.dumps(result,indent=2)+'\n')
    print((out/'output_files/board.fit.summary').read_text(encoding='latin1'),flush=True)
    print('Characterization minimum='+str(min(slacks))+'ns; unwaived CDC crossings require review',flush=True)


if __name__=='__main__':main()
