# SPDX-License-Identifier: MIT
"""Audit all unwaived routed reference-domain crossings; reject unlisted paths."""
from pathlib import Path
import argparse,csv,json,shutil
from nes_spi_boot import ROOT,run,sha,put


def classify(rows):
    assert rows
    categories={}
    for r in rows:
        src=r['from'].split('|')[-1];dst=r['to'].split('|')[-1]
        if (src,dst) in [('mem_heartbeat','mem_sync[0]'),('ref_divider[3]','ref_sync[0]')]:
            assert r['type'] in ['setup','hold'],r
            kind='heartbeat_first_stage'
        elif src in ['ref_fault','ref_qualified'] and dst in ['memory_release[0]','memory_release[1]']:
            assert r['type'] in ['recovery','removal'],r
            kind='reset_release_async_clear'
        else:
            raise AssertionError('UNEXPECTED_CROSSING '+str(r))
        categories[kind]=categories.get(kind,0)+1
    assert set(categories)=={'heartbeat_first_stage','reset_release_async_clear'}
    return categories


def main():
    p=argparse.ArgumentParser()
    for n in ['fit','out','quartus-bin']:p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--baseline',action='store_true')
    a=p.parse_args();fit=a.fit.resolve();out=a.out.resolve()
    assert str(out).isascii() and not out.exists()
    result=json.loads((fit/'result.json').read_text())
    assert result['identity_hex']==('85' if a.baseline else '86') and result['phases']==dict(map=0,fit=0,sta=0)
    for n,h in result['sources'].items():assert sha(fit/n)==h,n
    out.mkdir(parents=True);shutil.copytree(fit/'db',out/'db')
    for n in ['board.qsf','board.qpf','board.sdc']:shutil.copy2(fit/n,out/n)
    shutil.copy2(ROOT/'tools/nes_clock_cdc086.sdc' if a.baseline else fit/'clock-cdc086.sdc',out/'clock-cdc086.sdc')
    inputs={p.relative_to(out).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    put(out/'input-inventory.json',json.dumps(inputs,indent=2)+'\n')
    for n in ['nes_clock_audit086.py','nes_clock_audit086.tcl']:shutil.copy2(ROOT/'tools'/n,out/('executed-'+n))
    put(out/'audit-unwaived.sdc',(fit/'board.sdc').read_text().replace('source clock-cdc086.sdc',''))
    shutil.copy2(ROOT/'tools/nes_clock_audit086.tcl',out/'audit.tcl')
    run([a.quartus_bin/'quartus_sta.exe','-t','audit.tcl'],out,'audit',1800)
    with (out/'crossings.tsv').open() as f:rows=list(csv.DictReader(f,delimiter='\t'))
    if a.baseline:
        try:classify(rows)
        except AssertionError as e:
            assert 'UNEXPECTED_CROSSING' in str(e)
            put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-GUARD-085',rows=len(rows),
                expected_failure=True,assertion=str(e),crossings_sha256=sha(out/'crossings.tsv')),indent=2)+'\n')
            print('EXPECTED CF85 raw guard fanout rejection',flush=True);return
        raise AssertionError('Actual CF85 crossing audit unexpectedly passed')
    categories=classify(rows)
    assert len({r['corner'] for r in rows})==3
    put(out/'result.json',json.dumps(dict(candidate='NES-CLOCK-RESET-086',rows=len(rows),categories=categories,
       fit_result_sha256=sha(fit/'result.json'),input_inventory_sha256=sha(out/'input-inventory.json'),
       crossings_sha256=sha(out/'crossings.tsv'),unexpected_crossings=0,
       analog_metastability_verified=False,async_clear_to_q_bound_verified=False,external_io_signoff=False),indent=2)+'\n')
    print('PASS routed crossing audit '+str(categories),flush=True)


if __name__=='__main__':main()
