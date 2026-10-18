# SPDX-License-Identifier: MIT
"""Seal the same-wire/same-cycle structural encoder reduction and board gate."""
from pathlib import Path
import argparse,csv,json,re,shutil
from nes_delta231 import ROOT,BASE,sha


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--temp-root',type=Path,required=True)
    p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    paths={n:a.temp_root/('nes-source239-'+n) for n in ('test01','guards01','board01')}
    joint=read(paths['test01']/'result.json');guards=read(paths['guards01']/'result.json');board=read(paths['board01']/'result.json')
    assert joint['passed'] and joint['frames']==71 and joint['exact_c_files']==355 and guards['passed']
    assert board['joint_result_sha256']==sha(paths['test01']/'result.json')
    assert board['guards_result_sha256']==sha(paths['guards01']/'result.json')
    assert (paths['test01']/'cycles.csv').read_bytes()==(BASE/'probes/nes-source238/test01/cycles.csv').read_bytes()
    for obj,key,root in ((joint,'source_pins',BASE),(guards,'pins',ROOT),(board,'source_pins',BASE)):
        for k,h in obj[key].items():assert sha(root/k)==h,k
    prior=read(ROOT/'analysis/source238-verification.json')
    verified={**prior['verified_prior_pins'],**prior['public238_pins']}
    for k,h in verified.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    assert sha(BASE/'probes/nes-source238/manifest.json')==prior['manifest_sha256']
    assert board['map_completed'] and board['new_fit'] and len(board['retired_sdc_rows'])==216
    assert sha(paths['board01']/'cdc181.sdc')==sha(BASE/'probes/nes-source238/board01/cdc181.sdc')
    assert not any('332000' in x or 'Read_sdc failed' in x for x in board['fit_messages'])
    report=(paths['board01']/'output_files/board.map.rpt').read_text(encoding='latin-1')
    fsm_lines=[l.strip() for l in report.splitlines() if 'State Machine - ' in l and 'nes_source_encoder239:encoder|state' in l]
    fit_report=(paths['board01']/'output_files/board.fit.rpt').read_text(encoding='latin-1')
    required_le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',board['fit_summary'])[1].replace(',',''))
    required_labs=int(re.search(r'Fitter requires (\d+) LABs','\n'.join(board['fit_messages']))[1])
    m9ks=int(re.search(r'; M9Ks\s*; (\d+) / 56',fit_report)[1])
    base_rows=[[c.strip() for c in l.split(';')] for l in fit_report.splitlines()
               if '; M9K ' in l and 'encoder239:encoder|altsyncram:base_' in l]
    assert len(base_rows)==2
    base_m9ks=sum(int(row[19]) for row in base_rows)
    pairing={key:int(re.search(re.escape(label)+r'\s*;\s*(\d+)',fit_report)[1])
             for key,label in (('lut_only','-- Combinational with no register'),
                               ('register_only','-- Register only'),
                               ('lut_register','-- Combinational with a register'))}
    assert required_le==15930 and required_labs==1006 and m9ks==54 and base_m9ks==6
    assert pairing==dict(lut_only=7319,register_only=953,lut_register=7658)
    rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader((paths['test01']/'cycles.csv').open())]
    assert len(rows)==71 and all(r['total']==sum(r[k] for k in ('prepare','blocked','ackwait','transfer')) for r in rows)
    warm=[r for r in rows if r['frame']>=907]
    stats={key:dict(max_cycles=max(r[key] for r in warm),max_ms=max(r[key] for r in warm)*45.454/1e6)
           for key in ('total','prepare','blocked','ackwait','transfer')}
    stats.update(cycle_csv_identical_to238=True,overlap_writes=sum(r['overlap'] for r in rows),
        window='907..975 same69, excludes cold905 and second-output-bank cold906',
        scope='Source model only; excludes actual ARM computation/shared other SPI/SNES display. ackwait includes final block drain.')
    names=['src/nes/rtl/nes_source_encoder239.sv','src/nes/rtl/nes_source239.sv',
           'tests/nes-functional/source_encoder239_tb.sv','tools/test_nes_source239.py',
           'tools/test_nes_encoder239.py','tools/run_nes_source239.ps1','tools/map_nes_source239_board.py',
           'tools/seal_nes_source239.py','docs/nes-source239-contract.ko.md']
    assert sha(ROOT/'tools/test_nes_source239.py')==joint['runner_sha256']
    assert sha(ROOT/'tools/test_nes_encoder239.py')==guards['runner_sha256']
    dest.mkdir(parents=True)
    for n,src in paths.items():shutil.copytree(src,dest/n)
    for n in names:
        target=dest/'source01'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)}
           for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=239,files=files),indent=2)+'\n')
    public=dict(stage=239,functional_passed=True,deployable=False,scope=joint['scope'],
        selected=dict(joint='test01',guards='guards01',board='board01',source='source01'),
        frames=71,records=joint['records'],blocks=joint['blocks'],payload=joint['payload'],exact_c_files=355,
        c_output=joint['c_output'],encoder_guards=41,synthetic_frames=24,cycles=stats,
        encoder_fsm_extracted=bool(fsm_lines),encoder_fsm_report_lines=fsm_lines,query_state_fused=False,
        resource={k:board[k] for k in ('map_completed','resource_capacity_pass','le','ff','memory_bits','combinational',
            'baseline_map_le','baseline_map_combinational','baseline_fit_le','ram_rows','source_rows','warnings',
            'fit_returncode','fit_summary','fit_messages')},
        comparison238=dict(map_le=board['le']-prior['resource']['le'],
            combinational=board['combinational']-prior['resource']['combinational'],
            ff=board['ff']-prior['resource']['ff']),
        fit_requirement=dict(le=required_le,le_capacity=15408,labs=required_labs,lab_capacity=963,
            m9ks=m9ks,m9k_capacity=56,base_m9ks=base_m9ks,placed=False,
            pairing=pairing,previous238_pairing=dict(lut_only=7290,register_only=830,lut_register=7825),
            base_banks=[dict(name=row[1],depth=int(row[5]),m9ks=int(row[19])) for row in base_rows],
            note='Resource requirements from FIT; no successful routing/timing claim from failed FIT.'),
        retired_sdc_identical_to238=True,new_fit=True,new_sta=False,full_arm=False,physical=False,
        fps_proven=False,new_package=False,public239_pins={n:sha(ROOT/n) for n in names},
        verified_prior_pins=verified,prior238_manifest_sha256=prior['manifest_sha256'],prior_full_rehash=False,
        joint_result_sha256=sha(dest/'test01/result.json'),guards_result_sha256=sha(dest/'guards01/result.json'),
        board_result_sha256=sha(dest/'board01/result.json'),evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'))
    for f in (dest/'verification.json',ROOT/'analysis/source239-verification.json'):
        f.write_text(json.dumps(public,indent=2)+'\n')
    # Re-read every archived file independently before marking the seal verified.
    for rel,row in files.items():assert sha(dest/rel)==row['sha256'],rel
    progress=dict(status='SAME_WIRE_CYCLE_STRUCTURAL_RESOURCE_GATE',selected=public['selected'],
        resource_capacity_pass=board['resource_capacity_pass'],files=len(files),manifest_sha256=public['manifest_sha256'],
        rehash_files=len(files),public_pins_verified=len(names),pushed=False,pr_updated=False,
        pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='FIT15930LE/1006LAB: still522LE/43LAB minimum deficit; MAP minus138comb/44FF became only15 fewer requiredLE, register-only830->953. Inspect control/datapath and register pairing together; consider compact memory-backed control within recovered54/56M9K while preserving mapper headroom and preparation budget, not another small-adder or seed loop. Full codec/cycles remain exact. Then inputARM RUN/IRQ,hostNESfirstfault,finaldisplay lease/retire,CDCIOSTA,232 five VBlank bursts before physical scroll.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    print(json.dumps(progress,indent=2))


if __name__=='__main__':main()
