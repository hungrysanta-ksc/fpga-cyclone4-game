# SPDX-License-Identifier: MIT
"""Clone finalCF86 routed DB, record inputs before analysis, extract FPGA budget."""
from pathlib import Path
import argparse,json,shutil
from nes_spi_boot import ROOT,run,sha,put
from nes_diag_io_budget import calculate

def main():
    p=argparse.ArgumentParser();p.add_argument('--fit',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--quartus-bin',type=Path,required=True);a=p.parse_args()
    fit=a.fit.resolve();out=a.out.resolve();assert str(out).isascii();assert not out.exists()
    source=json.loads((fit/'result.json').read_text())
    assert source['candidate']=='NES-CLOCK-TIMING-086' and source['identity_hex']=='86' and source['phases']==dict(map=0,fit=0,sta=0)
    for n,h in source['sources'].items():assert sha(fit/n)==h,n
    out.mkdir(parents=True)
    shutil.copytree(fit/'db',out/'db')
    for n in ['board.qsf','board.qpf','board.sdc','clock-cdc086.sdc']:shutil.copy2(fit/n,out/n)
    inventory={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    for n,h in inventory.items():assert sha(fit/n)==h,n
    put(out/'input-fit-inventory.json',json.dumps(inventory,indent=2)+'\n')
    for n in ['nes_clock_io086.py','nes_diag_io_budget.py','nes_diag_io_paths.tcl']:
        shutil.copy2(ROOT/'tools'/n,out/('executed-'+n))
    shutil.copy2(ROOT/'tools/nes_diag_io_paths.tcl',out/'io.tcl')
    log=run([a.quartus_bin/'quartus_sta.exe','-t','io.tcl'],out,'io',1800)
    assert 'successful. 0 errors, 0 warnings' in log
    changed=[n for n,h in inventory.items() if sha(out/n)!=h]
    if 'board.qsf' in changed:
        original=(fit/'board.qsf').read_text()
        assert (out/'board.qsf').read_text()==original+'\nset_global_assignment -name LAST_QUARTUS_VERSION "25.1std.0 Standard Edition"'
    allowed={'board.qsf','db/board.cmp.rdb','db/board.cycloneive_io_sim_cache.31um_ss_1200mv_85c_slow.hsd'}
    assert set(changed)<=allowed,changed
    budget=calculate(out/'io-paths.tsv',20,5);outside=calculate(out/'io-paths.tsv',60,5)
    budget['candidate']=outside['candidate']='NES-CLOCK-RESET-086'
    import csv
    with (out/'io-paths.tsv').open() as f: rows=list(csv.DictReader(f,delimiter='\t'))
    read_controls=[r for r in rows if r['to'] in ['ROM_OE','ROM_1CE','ROM_2CE'] and 'nes_rom_physical:reader|' in r['from']]
    assert any(r['from'].endswith('|reading_active') for r in read_controls)
    assert not any('|state.' in r['from'] for r in read_controls),'Read controls decode state directly after fit'
    assert budget['scenario_positive'] and not outside['scenario_positive']
    put(out/'budget.json',json.dumps(budget,indent=2)+'\n');put(out/'budget-outside.json',json.dumps(outside,indent=2)+'\n')
    put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-RESET-086',fit_result_sha256=sha(fit/'result.json'),
        input_inventory_sha256=sha(out/'input-fit-inventory.json'),post_analysis_changed_inputs=changed,
        paths_sha256=sha(out/'io-paths.tsv'),path_rows=budget['path_rows'],external_io_signoff=False,
        measurement_overlay_only=True,registered_read_controls=True,source_hashes={n:sha(out/('executed-'+n)) for n in ['nes_clock_io086.py','nes_diag_io_budget.py','nes_diag_io_paths.tcl']}),indent=2)+'\n')
    print('PASS FPGA-only extraction rows='+str(budget['path_rows'])+' signoff=false',flush=True)
if __name__=='__main__':main()
