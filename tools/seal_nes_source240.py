# SPDX-License-Identifier: MIT
"""Seal direct record views, exact stream checks and the single board gate."""
from pathlib import Path
import argparse,csv,json,re,shutil
from nes_delta231 import ROOT,BASE,sha


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--temp-root',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    paths={n:a.temp_root/('nes-source240-'+n) for n in ('test01','guards01','board01')}
    joint=read(paths['test01']/'result.json');guards=read(paths['guards01']/'result.json');board=read(paths['board01']/'result.json')
    assert joint['passed'] and joint['frames']==71 and joint['exact_c_files']==355 and guards['passed']
    assert any('VIEWS240 stalled=1111111 immutable publication PASS' in line for line in guards['summary'])
    assert board['joint_result_sha256']==sha(paths['test01']/'result.json')
    assert board['guards_result_sha256']==sha(paths['guards01']/'result.json')
    for obj,key,root in ((joint,'source_pins',BASE),(guards,'pins',ROOT),(board,'source_pins',BASE)):
        for k,h in obj[key].items():assert sha(root/k)==h,k
    prior=read(ROOT/'analysis/source239-verification.json')
    verified={**prior['verified_prior_pins'],**prior['public239_pins']}
    for k,h in verified.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    assert sha(BASE/'probes/nes-source239/manifest.json')==prior['manifest_sha256']
    assert board['map_completed'] and board['new_fit'] and len(board['retired_sdc_rows'])==216
    assert sha(paths['board01']/'cdc181.sdc')==sha(BASE/'probes/nes-source239/board01/cdc181.sdc')
    assert not any('332000' in x or 'Read_sdc failed' in x for x in board['fit_messages'])
    report=(paths['board01']/'output_files/board.map.rpt').read_text(encoding='latin-1')
    fsm_lines=[l.strip() for l in report.splitlines() if 'State Machine - ' in l and 'nes_source_encoder240:encoder|state' in l]
    fit_report=(paths['board01']/'output_files/board.fit.rpt').read_text(encoding='latin-1')
    required_le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',board['fit_summary'])[1].replace(',',''))
    required_labs=int(re.search(r'Fitter requires (\d+) LABs','\n'.join(board['fit_messages']))[1])
    m9ks=int(re.search(r'; M9Ks\s*; (\d+) / 56',fit_report)[1])
    base_rows=[[c.strip() for c in l.split(';')] for l in fit_report.splitlines()
               if '; M9K ' in l and 'encoder240:encoder|altsyncram:base_' in l]
    assert len(base_rows)==2
    base_m9ks=sum(int(row[19]) for row in base_rows)
    pairing={key:int(re.search(re.escape(label)+r'\s*;\s*(\d+)',fit_report)[1])
             for key,label in (('lut_only','-- Combinational with no register'),
                               ('register_only','-- Register only'),
                               ('lut_register','-- Combinational with a register'))}
    assert m9ks==54 and base_m9ks==6 and not board['resource_capacity_pass']
    def cycles(path):
        return [{k:int(v) for k,v in r.items()} for r in csv.DictReader(path.open())]
    rows=cycles(paths['test01']/'cycles.csv');before=cycles(BASE/'probes/nes-source239/test01/cycles.csv')
    assert len(rows)==71 and all(r['total']==sum(r[k] for k in ('prepare','blocked','ackwait','transfer')) for r in rows)
    assert all(r['frame']==b['frame'] and r['queries']==b['queries'] and r['prepare']<b['prepare'] for r,b in zip(rows,before))
    warm=[r for r in rows if r['frame']>=907];old_warm=[r for r in before if r['frame']>=907]
    stats={key:dict(max_cycles=max(r[key] for r in warm),max_ms=max(r[key] for r in warm)*45.454/1e6,
                   sum_cycles=sum(r[key] for r in warm),previous_max_cycles=max(r[key] for r in old_warm),
                   previous_sum_cycles=sum(r[key] for r in old_warm))
           for key in ('total','prepare','blocked','ackwait','transfer')}
    assert all(r['total']<=b['total'] for r,b in zip(rows,before))
    stats.update(all71_prepare_lower=True,all71_total_not_higher=True,overlap_writes=sum(r['overlap'] for r in rows),
        per_frame=[dict(frame=r['frame'],prepare_change=r['prepare']-b['prepare'],total_change=r['total']-b['total']) for r,b in zip(rows,before)],
        window='907..975 same69, excludes cold905 and second-output-bank cold906',
        scope='Source model only; excludes actual ARM computation/shared other SPI/SNES display. ackwait includes final block drain. Poll timing can vary.')
    names=['src/nes/rtl/nes_source_encoder240.sv','src/nes/rtl/nes_source240.sv',
           'tests/nes-functional/source_encoder240_tb.sv','tools/test_nes_source240.py',
           'tools/test_nes_encoder240.py','tools/run_nes_source240.ps1','tools/map_nes_source240_board.py',
           'tools/seal_nes_source240.py','docs/nes-source240-contract.ko.md']
    assert sha(ROOT/'tools/test_nes_source240.py')==joint['runner_sha256']
    assert sha(ROOT/'tools/test_nes_encoder240.py')==guards['runner_sha256']
    assert sha(ROOT/'tools/map_nes_source240_board.py')==board['runner_sha256']
    dest.mkdir(parents=True)
    for n,src in paths.items():shutil.copytree(src,dest/n)
    for n in names:
        target=dest/'source01'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)}
           for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=240,files=files),indent=2)+'\n')
    public=dict(stage=240,functional_passed=True,deployable=False,scope=joint['scope'],
        selected=dict(joint='test01',guards='guards01',board='board01',source='source01'),
        frames=71,records=joint['records'],blocks=joint['blocks'],payload=joint['payload'],exact_c_files=355,
        c_output=joint['c_output'],encoder_guards=41,synthetic_frames=24,stalled_views=7,cycles=stats,
        encoder_fsm_extracted=bool(fsm_lines),encoder_fsm_report_lines=fsm_lines,query_state_fused=False,
        resource={k:board[k] for k in ('map_completed','resource_capacity_pass','le','ff','memory_bits','combinational',
            'baseline_map_le','baseline_map_combinational','baseline_fit_le','ram_rows','source_rows','warnings',
            'fit_returncode','fit_summary','fit_messages')},
        comparison239=dict(map_le=board['le']-prior['resource']['le'],
            combinational=board['combinational']-prior['resource']['combinational'],
            ff=board['ff']-prior['resource']['ff'],required_le=required_le-prior['fit_requirement']['le'],
            required_labs=required_labs-prior['fit_requirement']['labs']),
        fit_requirement=dict(le=required_le,le_capacity=15408,labs=required_labs,lab_capacity=963,
            m9ks=m9ks,m9k_capacity=56,base_m9ks=base_m9ks,placed=False,
            pairing=pairing,previous239_pairing=prior['fit_requirement']['pairing'],
            base_banks=[dict(name=row[1],depth=int(row[5]),m9ks=int(row[19])) for row in base_rows],
            note='Resource requirements from FIT; no successful routing/timing claim from failed FIT.'),
        retired_sdc_identical_to239=True,new_fit=True,new_sta=False,full_arm=False,physical=False,
        fps_proven=False,new_package=False,public240_pins={n:sha(ROOT/n) for n in names},
        verified_prior_pins=verified,prior239_manifest_sha256=prior['manifest_sha256'],prior_full_rehash=False,
        joint_result_sha256=sha(dest/'test01/result.json'),guards_result_sha256=sha(dest/'guards01/result.json'),
        board_result_sha256=sha(dest/'board01/result.json'),evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'))
    for f in (dest/'verification.json',ROOT/'analysis/source240-verification.json'):
        f.write_text(json.dumps(public,indent=2)+'\n')
    for rel,row in files.items():assert sha(dest/rel)==row['sha256'],rel
    progress=dict(status='IMMUTABLE_RECORD_VIEWS_RESOURCE_GATE',selected=public['selected'],
        resource_capacity_pass=False,files=len(files),manifest_sha256=public['manifest_sha256'],
        rehash_files=len(files),public_pins_verified=len(names),pushed=False,pr_updated=False,
        pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next=f'FIT still {required_le-15408}LE/{required_labs-963}LAB minimum deficit, not mapper/timing margin. Direct-copy removal only saves32requiredLE; encoder combinational +4. Keep full codec and immutable views. Next evaluate compact microcontrol/shared datapath with explicit write-before-read/reset-abort-ACK lifetime and actual M9K word/latency budget before one whole-board gate. Multiplexer restructuring baseline/savings are NOT remaining cells (named counters already0 after restructuring); no counter/adder/seed loops. Then inputARM RUN/IRQ,hostNESfirstfault,finaldisplay lease/retire,CDCIOSTA,232 five VBlank bursts before physical scroll.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    print(json.dumps(progress,indent=2))


if __name__=='__main__':main()
