# SPDX-License-Identifier: MIT
"""Causal failures on actual exported SDF/VO; no production RTL modifications."""
from pathlib import Path
import argparse, json, re, shutil
from nes_clock_assert093 import analyze, digest


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--export', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args(); assert not a.out.exists(); a.out.mkdir(parents=True)
    src = a.export/'simulation/modelsim'
    vo = src/'board_8_1200mv_85c_slow.vo'; sdf = src/'board_8_1200mv_85c_v_slow.sdo'
    text = sdf.read_text(); original = analyze(vo, sdf)
    assert len(original['paths']) == 88
    # Removing the actual asynchronous assertion arcs must not be masked by
    # clock-to-Q arcs when the relevant clock has halted.
    removed, count = re.subn(r'\s*\(IOPATH \(negedge clrn\) q[^\n]*', '', text)
    assert count > 0
    inflated, count2 = re.subn(r'\(IOPATH \(negedge clrn\) q[^\n]*',
        '(IOPATH (negedge clrn) q (100000:100000:100000) (100000:100000:100000))', text)
    assert count2 == count
    results = []
    for name, mutant, expected in [('no-async', removed, 'MISSING_ASYNC_ARC'),
                                  ('excess-delay', inflated, 'PROPAGATION_ALLOCATION_EXCEEDED'),
                                  ('wrong-timescale', text.replace('(TIMESCALE 1 ps)', '(TIMESCALE 1 ns)'), 'Only integer ps')]:
        d = a.out/name; d.mkdir(); mp = d/'mutant.sdo'; mp.write_text(mutant)
        try:
            analyze(vo, mp)
        except AssertionError as e:
            assert expected in str(e), str(e)
            result = dict(case=name, expected_failure=True, assertion=str(e), mutant_sha256=digest(mp))
            (d/'failure.json').write_text(json.dumps(result, indent=2)+'\n'); results.append(result)
        else:
            raise AssertionError('MUTATION_NOT_DETECTED '+name)
    # Break the real async connection while retaining all SDF cells/arcs.
    original_vo = vo.read_text()
    expression = r'(dffeas \\boundary\|memory_release\[1\] \(.*?\.clrn\()[^)]*(\))'
    broken, count = re.subn(expression, r'\g<1>vcc\2', original_vo, flags=re.S)
    assert count == 1
    d = a.out/'disconnect-clear'; d.mkdir(); mv = d/'mutant.vo'; mv.write_text(broken)
    try:
        analyze(mv, sdf)
    except AssertionError as e:
        assert 'UNREACHABLE' in str(e), str(e)
        results.append(dict(case='disconnect-clear', expected_failure=True, assertion=str(e), mutant_sha256=digest(mv)))
    else:
        raise AssertionError('MUTATION_NOT_DETECTED disconnected clear')
    for name in ['nes_clock_assert093.py', 'test_nes_assert093.py']:
        shutil.copy2(Path(__file__).parent/name, a.out/('executed-'+name))
    (a.out/'result.json').write_text(json.dumps(dict(controls=results, original_paths=88,
        original_vo_sha256=digest(vo), original_sdf_sha256=digest(sdf)), indent=2)+'\n')
    print('PASS actual-export causal controls='+str(len(results)))


if __name__ == '__main__':
    main()
