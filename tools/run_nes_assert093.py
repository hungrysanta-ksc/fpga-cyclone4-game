# SPDX-License-Identifier: MIT
"""Clone immutable CF86 fit, export three SDF corners, audit assertion paths."""
from pathlib import Path
import argparse, json, shutil
from nes_spi_boot import ROOT, run, put, sha
from nes_clock_assert093 import analyze

CORNERS = [('8_1200mv_85c_slow', '8_1200mv_85c_v_slow'),
           ('8_1200mv_0c_slow', '8_1200mv_0c_v_slow'),
           ('min_1200mv_0c_fast', 'min_1200mv_0c_v_fast')]


def main():
    p = argparse.ArgumentParser()
    for n in ['fit', 'out', 'quartus-bin']:
        p.add_argument('--'+n, type=Path, required=True)
    a = p.parse_args(); fit = a.fit.resolve(); out = a.out.resolve()
    assert not out.exists() and str(out).isascii()
    meta = json.loads((fit/'result.json').read_bytes())
    assert meta['identity_hex'] == '86' and meta['phases'] == dict(map=0, fit=0, sta=0)
    for n, h in meta['sources'].items():
        assert sha(fit/n) == h, n
    out.mkdir(parents=True); shutil.copytree(fit/'db', out/'db')
    for n in ['board.qsf', 'board.qpf', 'board.sdc', 'clock-cdc086.sdc']:
        shutil.copy2(fit/n, out/n)
    inventory = {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()}
    assert all(sha(fit/n) == h for n, h in inventory.items())
    put(out/'input-inventory.json', json.dumps(inventory, indent=2)+'\n')
    for n in ['nes_clock_assert093.py', 'run_nes_assert093.py']:
        shutil.copy2(ROOT/'tools'/n, out/('executed-'+n))
    log = run([a.quartus_bin/'quartus_eda.exe', 'board', '--simulation', '--tool=modelsim',
               '--format=verilog', '--output_directory=simulation/modelsim'], out, 'eda', 1800)
    assert 'successful. 0 errors, 0 warnings' in log
    changed = [n for n, h in inventory.items() if sha(out/n) != h]
    assert set(changed) <= {'board.qsf', 'db/board.cmp.hdb', 'db/board.cmp.rdb'}, changed
    if 'board.qsf' in changed:
        suffix = '\nset_global_assignment -name LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"\n'
        suffix += 'set_global_assignment -name EDA_SIMULATION_TOOL "QuestaSim (Verilog)"\n'
        suffix += 'set_global_assignment -name EDA_NETLIST_WRITER_OUTPUT_DIR simulation/modelsim -section_id eda_simulation\n'
        suffix += 'set_global_assignment -name EDA_OUTPUT_DATA_FORMAT "VERILOG HDL" -section_id eda_simulation'
        assert (out/'board.qsf').read_text() == (fit/'board.qsf').read_text() + suffix
    results = []
    for vo, sdf in CORNERS:
        result = analyze(out/'simulation/modelsim'/('board_'+vo+'.vo'),
                         out/'simulation/modelsim'/('board_'+sdf+'.sdo'))
        result['corner'] = vo
        put(out/('assert-'+vo+'.json'), json.dumps(result, indent=2)+'\n')
        results.append(dict(corner=vo, maximum_ps=result['maximum_ps'], paths=len(result['paths']),
                            ce_maximum_ps=max(p['maximum_ps'] for p in result['paths'] if p['target'] in ['ROM_1CE', 'ROM_2CE']),
                            async_cells=result['sdf_async_cells'], arcs=result['arcs'],
                            report_sha256=sha(out/('assert-'+vo+'.json'))))
    put(out/'result.json', json.dumps(dict(candidate='NES-ASSERTION-093', identity_hex='86',
        fit_result_sha256=sha(fit/'result.json'), input_inventory_sha256=sha(out/'input-inventory.json'),
        post_export_changed_inputs=changed, corners=results, path_count=sum(x['paths'] for x in results),
        maximum_ps=max(x['maximum_ps'] for x in results),
        sources={n:sha(ROOT/'tools'/n) for n in ['nes_clock_assert093.py', 'run_nes_assert093.py']},
        new_fit=False, new_sta=False, sdf_simulation=False, external_signoff=False,
        clock_detection_included=False, both_clock_halt_safe=False, installable=False), indent=2)+'\n')
    # Confirm the source DB was not touched, including its original QSF.
    assert all(sha(fit/n) == h for n, h in inventory.items())
    print('PASS 3 corners, '+str(sum(x['paths'] for x in results))+' assertion paths; maximum_ps='+str(max(x['maximum_ps'] for x in results)))


if __name__ == '__main__':
    main()
