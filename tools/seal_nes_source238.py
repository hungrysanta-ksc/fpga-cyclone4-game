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
    paths={n:a.temp_root/('nes-source238-'+n) for n in ('test01','guards01','board01')}
    joint=read(paths['test01']/'result.json');guards=read(paths['guards01']/'result.json');board=read(paths['board01']/'result.json')
    assert joint['passed'] and joint['frames']==71 and joint['exact_c_files']==355 and guards['passed']
    assert board['joint_result_sha256']==sha(paths['test01']/'result.json')
    assert board['guards_result_sha256']==sha(paths['guards01']/'result.json')
    assert (paths['test01']/'cycles.csv').read_bytes()==(BASE/'probes/nes-source237/test04/cycles.csv').read_bytes()
    for obj,key,root in ((joint,'source_pins',BASE),(guards,'pins',ROOT),(board,'source_pins',BASE)):
        for k,h in obj[key].items():assert sha(root/k)==h,k
    prior=read(ROOT/'analysis/source237-verification.json')
    verified={**prior['verified_prior_pins'],**prior['public237_pins']}
    for k,h in verified.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    assert sha(BASE/'probes/nes-source237/manifest.json')==prior['manifest_sha256']
    assert board['map_completed'] and board['new_fit'] and len(board['retired_sdc_rows'])==216
    assert sha(paths['board01']/'cdc181.sdc')==sha(BASE/'probes/nes-source237/board03/cdc181.sdc')
    assert not any('332000' in x or 'Read_sdc failed' in x for x in board['fit_messages'])
    report=(paths['board01']/'output_files/board.map.rpt').read_text(encoding='latin-1')
    fsm_lines=[l.strip() for l in report.splitlines() if 'State Machine - ' in l and 'nes_source_encoder238:encoder|state' in l]
    fit_report=(paths['board01']/'output_files/board.fit.rpt').read_text(encoding='latin-1')
    required_le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',board['fit_summary'])[1].replace(',',''))
    required_labs=int(re.search(r'Fitter requires (\d+) LABs','\n'.join(board['fit_messages']))[1])
    m9ks=int(re.search(r'; M9Ks\s*; (\d+) / 56',fit_report)[1])
    base_row=next([c.strip() for c in l.split(';')] for l in fit_report.splitlines()
                  if '; M9K ' in l and 'encoder238:encoder|altsyncram:base_rtl_0|' in l)
    base_m9ks=int(base_row[19])
    assert required_le==15945 and required_labs==1014 and m9ks==56 and base_m9ks==8
    rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader((paths['test01']/'cycles.csv').open())]
    assert len(rows)==71 and all(r['total']==sum(r[k] for k in ('prepare','blocked','ackwait','transfer')) for r in rows)
    warm=[r for r in rows if r['frame']>=907]
    stats={key:dict(max_cycles=max(r[key] for r in warm),max_ms=max(r[key] for r in warm)*45.454/1e6)
           for key in ('total','prepare','blocked','ackwait','transfer')}
    stats.update(cycle_csv_identical_to237=True,overlap_writes=sum(r['overlap'] for r in rows),
        window='907..975 same69, excludes cold905 and second-output-bank cold906',
        scope='Source model only; excludes actual ARM computation/shared other SPI/SNES display. ackwait includes final block drain.')
    names=['src/nes/rtl/nes_source_encoder238.sv','src/nes/rtl/nes_source238.sv',
           'tests/nes-functional/source_encoder238_tb.sv','tools/test_nes_source238.py',
           'tools/test_nes_encoder238.py','tools/run_nes_source238.ps1','tools/map_nes_source238_board.py',
           'tools/seal_nes_source238.py','docs/nes-source238-contract.ko.md']
    assert sha(ROOT/'tools/test_nes_source238.py')==joint['runner_sha256']
    assert sha(ROOT/'tools/test_nes_encoder238.py')==guards['runner_sha256']
    dest.mkdir(parents=True)
    for n,src in paths.items():shutil.copytree(src,dest/n)
    for n in names:
        target=dest/'source01'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)}
           for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=238,files=files),indent=2)+'\n')
    public=dict(stage=238,functional_passed=True,deployable=False,scope=joint['scope'],
        selected=dict(joint='test01',guards='guards01',board='board01',source='source01'),
        frames=71,records=joint['records'],blocks=joint['blocks'],payload=joint['payload'],exact_c_files=355,
        c_output=joint['c_output'],encoder_guards=36,synthetic_frames=20,cycles=stats,
        encoder_fsm_extracted=bool(fsm_lines),encoder_fsm_report_lines=fsm_lines,query_state_fused=False,
        resource={k:board[k] for k in ('map_completed','resource_capacity_pass','le','ff','memory_bits','combinational',
            'baseline_map_le','baseline_map_combinational','baseline_fit_le','ram_rows','source_rows','warnings',
            'fit_returncode','fit_summary','fit_messages')},
        comparison237=dict(map_le=board['le']-prior['resource']['le'],
            combinational=board['combinational']-prior['resource']['combinational'],
            ff=board['ff']-prior['resource']['ff']),
        fit_requirement=dict(le=required_le,le_capacity=15408,labs=required_labs,lab_capacity=963,
            m9ks=m9ks,m9k_capacity=56,base_m9ks=base_m9ks,placed=False,
            note='Failed fit resource requirement, not a completed placed design. Prior54 M9K arithmetic understated base fragmentation;6144x8 requires8 in this fit.'),
        retired_sdc_identical_to237=True,new_fit=True,new_sta=False,full_arm=False,physical=False,
        fps_proven=False,new_package=False,public238_pins={n:sha(ROOT/n) for n in names},
        verified_prior_pins=verified,prior237_manifest_sha256=prior['manifest_sha256'],prior_full_rehash=False,
        joint_result_sha256=sha(dest/'test01/result.json'),guards_result_sha256=sha(dest/'guards01/result.json'),
        board_result_sha256=sha(dest/'board01/result.json'),evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'))
    for f in (dest/'verification.json',ROOT/'analysis/source238-verification.json'):
        f.write_text(json.dumps(public,indent=2)+'\n')
    # Re-read every archived file independently before marking the seal verified.
    for rel,row in files.items():assert sha(dest/rel)==row['sha256'],rel
    progress=dict(status='SAME_WIRE_CYCLE_STRUCTURAL_RESOURCE_GATE',selected=public['selected'],
        resource_capacity_pass=board['resource_capacity_pass'],files=len(files),manifest_sha256=public['manifest_sha256'],
        rehash_files=len(files),public_pins_verified=len(names),pushed=False,pr_updated=False,
        pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='FIT15945LE/1014LAB exceeds15408/963. M9K56/56: base6144x8 consumes8 not6. Need joint query/cursor/arithmetic/control sharing and base bank organization before another whole-board gate; cannot assume free2M9K for control ROM. Preserve full codec/cycles and future mapper margin. Then actual input ARM RUN/IRQ, host/NES first-fault preservation, final display lease/retire, CDC/IO/STA,232 five VBlank bursts. No seed/clock waiver or unqualified package.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    print(json.dumps(progress,indent=2))


if __name__=='__main__':main()
