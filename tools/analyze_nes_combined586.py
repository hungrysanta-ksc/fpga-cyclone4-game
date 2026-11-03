# SPDX-License-Identifier: MIT
"""Record the rejected586 linked cost without pricing unimplemented history."""
import argparse,json
from pathlib import Path
from analyze_nes_transport584 import sha,elf_cost
from analyze_nes_ownership585 import inventory

ROOT=Path(__file__).resolve().parents[1]
def run(a):
    report=json.loads((a.test/'result.json').read_text())
    assert report['passed'] and report['checker_SHA256']==sha(ROOT/'tools/check_nes_combined586.py')
    patch=json.loads((a.patch/'manifest.json').read_text())
    for n,h in patch['patched'].items():assert sha(a.arm/n)==h
    prior=json.loads((ROOT/'analysis/transport584-verification.json').read_text())
    assert sha(a.trace)==prior['evidence']['trace_SHA256']
    for g in (951,954):assert sha(a.plans/f'frame{g}/plans.json')==prior['evidence']['plans'][str(g)]
    cost={};modules={}
    for label,src in [('577',a.base),('584',a.prior),('586',a.arm)]:
        f=src/'obj-nes-100/firmware.stm'
        cost[label]=dict(firmware_B=f.stat().st_size,firmware_SHA256=sha(f),**elf_cost(src/'obj-nes-100/sd2snes.elf'))
        modules[label]={n:elf_cost(src/'obj-nes-100'/f'{n}.o') for n in
            ('nes_native165','nes_native_runtime165','nes_plan_service200','nes_sink_window184')}
    excess=cost['586']['firmware_B']-212992
    assert excess>0
    report.update(decision='reject_combined_adapter_envelope_before_history',patch=patch,linked_cost=cost,
        object_cost=modules,layout=inventory(a.arm),capacity_B=212992,capacity_excess_B=excess,
        firmware_delta_from577_B=cost['586']['firmware_B']-cost['577']['firmware_B'],
        stop_rule='Already over cap before history/planner/retained-integrity work; no further ABI/padding/poll/log variants in this boundary',
        limits=report['limits']+['Object totals are not net reclaimed Flash; linked final image is authoritative',
          'Legacy logical_record control remains behind new section admission; no proof a direct semantic replacement cannot fit'],
        fixture_pins=prior['evidence'],tool_pins={n:sha(ROOT/'tools'/n) for n in ('nes_section586.inc','prepare_nes_combined586.py','check_nes_combined586.py',
          'analyze_nes_combined586.py','check_nes_transport584.py','nes_row583.py','nes_row583.c','nes_abi582.py')},
        baseline_evidence={n:sha(ROOT/'analysis'/n) for n in ('transport584-verification.json','ownership585-verification.json')},
        new_FIT=False,new_physical_FPS=False,new_package=False)
    a.out.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(cost=cost,modules=modules,capacity_excess_B=excess)))

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('base','prior','arm','patch','test','plans','trace','out'):p.add_argument('--'+n,type=Path,required=True)
    run(p.parse_args())
