"""Independent original NROM frame comparison and RTL assertion audit. SPDX-License-Identifier: MIT."""
from pathlib import Path
import argparse,hashlib,json,re


def compare_frame(values,chrdata):
    if len(values)!=256*240:return dict(passed=False,error='frame_length',pixels=len(values))
    expected=[]
    for y in range(240):
        for x in range(256):
            # The original smoke ROM fills all nametable entries with tile zero.
            bit=7-x%8
            index=((chrdata[y%8]>>bit)&1)|(((chrdata[y%8+8]>>bit)&1)<<1)
            expected.append([15,33,48,22][index])
    wrong=[i for i,(a,b) in enumerate(zip(values,expected)) if a!=b]
    return dict(passed=not wrong,pixels=len(values),different_pixels=len(wrong),
        first_xy=[wrong[0]%256,wrong[0]//256] if wrong else None,
        expected_index_sha256=hashlib.sha256(bytes(expected)).hexdigest(),
        actual_index_sha256=hashlib.sha256(bytes(values)).hexdigest())


def main():
    p=argparse.ArgumentParser();p.add_argument('--run',type=Path,required=True);a=p.parse_args();out=a.run
    build=json.loads((out/'build.json').read_text())
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['sha256']=='98ecb54846f020d886d32740292999efaad3d3ed4fa6792e7043403fba3854f9'
    log=(out/'simulation.log').read_text(errors='replace')
    m=re.search(r'^# RESULT (.+)$',log,re.M);assert m,'No final RTL result'
    metrics={k:int(v) for k,v in re.findall(r'(\w+)=(\d+)',m[1])}
    colors=[int(v,16) for v in (out/'frame-color.hex').read_text().split()]
    chrdata=bytes(int(v,16) for v in (out/'chr.hex').read_text().split())
    comparison=compare_frame(colors,chrdata)
    assertions=bool(build.get('diagnostic_passed')) and 'PASS NES DIAGNOSTIC' in log and not re.search(r'\*\* (?:Fatal|Error):',log)
    for name in ['badcolors','pixel_errors','cpu_period_errors','unknown_bus','audio_unknown','audio_period_errors']:
        assertions=assertions and metrics.get(name)==0
    assertions=assertions and metrics['pixels']==61440 and 52<=metrics['audio_changes']<=54
    damaged=colors.copy();damaged[0]^=1
    negatives=dict(one_pixel_rejected=not compare_frame(damaged,chrdata)['passed'],truncation_rejected=not compare_frame(colors[:-1],chrdata)['passed'])
    result=dict(candidate='NES-P2-RTL-006',passed=assertions and comparison['passed'] and all(negatives.values()),
        assertions_passed=assertions,metrics=metrics,pixel_comparison=comparison,comparator_negative_tests=negatives,
        expected_pulse_edge_period_master_ticks=24384,expected_cpu_period_master_ticks=12,
        observation_time_ns=120020000,clock_half_period_ns=23.280,
        output_contract='Registered PPU color is sampled at cycle=x+2 (cycles 2..257); all 256x240 source pixels retained.',
        rom_sha256=manifest['sha256'],source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Original NROM checkerboard, ideal synchronous memory, basic joypad and pulse output. Not MMC3, full APU/CPU conformance, board IO, full-fit/STA or hardware verification.')
    (out/'verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8',newline='\n')
    print(json.dumps(result,indent=2))
    raise SystemExit(0 if result['passed'] else 1)

if __name__=='__main__':main()
