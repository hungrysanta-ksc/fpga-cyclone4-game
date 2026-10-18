# SPDX-License-Identifier: MIT
"""Seal a rejected control-only ROM candidate; baseline remains source240."""
from pathlib import Path
import argparse,json,re,shutil
from nes_delta231 import ROOT,BASE,sha


def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    sessions=[f'guards{i:02d}' for i in range(1,6)]+['board01','board02']
    paths={s:a.temp_root/('nes-source241-'+s) for s in sessions}
    guards=read(paths['guards05']/'result.json');board=read(paths['board02']/'result.json')
    assert guards['passed'] and any('REFERENCE241 cycles=1278508 states=58 RAM/interface/PC exact' in x for x in guards['summary'])
    assert any('VIEWS241 stalled=1111111' in x for x in guards['summary'])
    for k,h in guards['pins'].items():assert sha(ROOT/k)==h,k
    for k,h in board['source_pins'].items():assert sha(BASE/k)==h,k
    assert sha(ROOT/'tools/test_nes_encoder241.py')==guards['runner_sha256']
    assert sha(ROOT/'tools/map_nes_source241_board.py')==board['runner_sha256']
    assert board['guards_result_sha256']==sha(paths['guards05']/'result.json')
    assert board['preflight_only'] and board['joint_result_sha256'] is None
    assert board['map_completed'] and board['new_fit'] and not board['resource_capacity_pass']
    assert not read(paths['board01']/'result.json')['map_completed']
    assert not (a.temp_root/'nes-source241-test01').exists(), 'Do not report uninspected integration results.'
    prior=read(ROOT/'analysis/source240-verification.json')
    verified={**prior['verified_prior_pins'],**prior['public240_pins']}
    for k,h in verified.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    assert sha(BASE/'probes/nes-source240/manifest.json')==prior['manifest_sha256']
    assert len(board['retired_sdc_rows'])==216
    assert sha(paths['board02']/'cdc181.sdc')==sha(BASE/'probes/nes-source240/board01/cdc181.sdc')
    fr=(paths['board02']/'output_files/board.fit.rpt').read_text(encoding='latin-1')
    required_le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',board['fit_summary'])[1].replace(',',''))
    required_labs=int(re.search(r'Fitter requires (\d+) LABs','\n'.join(board['fit_messages']))[1])
    m9ks=int(re.search(r'; M9Ks\s*; (\d+) / 56',fr)[1])
    rom_rows=[[c.strip() for c in l.split(';')] for l in fr.splitlines()
              if '; M9K ' in l and 'encoder241:encoder|altsyncram:program_rom' in l]
    assert len(rom_rows)==1;rom=rom_rows[0]
    pairing={key:int(re.search(re.escape(label)+r'\s*;\s*(\d+)',fr)[1])
             for key,label in (('lut_only','-- Combinational with no register'),('register_only','-- Register only'),('lut_register','-- Combinational with a register'))}
    assert (required_le,required_labs,m9ks)==(16218,1022,55)
    assert int(rom[19])==1 and int(rom[14])==128 and int(rom[15])==30
    names=['src/nes/rtl/nes_source_encoder241.sv','src/nes/rtl/nes_source241.sv',
           'tests/nes-functional/source_encoder241_tb.sv','tools/test_nes_source241.py',
           'tools/test_nes_encoder241.py','tools/run_nes_source241.ps1','tools/map_nes_source241_board.py',
           'tools/seal_nes_source241.py','docs/nes-source241-contract.ko.md']
    dest.mkdir(parents=True)
    for n,src in paths.items():shutil.copytree(src,dest/n)
    for n in names:
        target=dest/'source01'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=241,files=files),indent=2)+'\n')
    result=dict(stage=241,adopted=False,baseline_stage=240,production_stage=227,deployable=False,
        decision='Reject this control-only ROM candidate: FIT requirement increases320LE/19LAB and one M9K versus240.',
        selected=dict(guards='guards05',board='board02',source='source01'),preserved_sessions=sessions,
        failures=dict(guards01='declaration order compile error',guards02='240-byte literal threshold transcription caught by PC reference',
                      guards03='intermediate reference pass',guards04='intermediate RAM reference pass but duplicate PC drivers survived',
                      board01='elaboration multiple drivers, not capacity evidence'),
        reference_cycles=1278508,reference_states=58,synthetic_frames=24,encoder_guards=41,stalled_views=7,
        pc_ram_interface_byte_exact=True,static_single_pc_driver=True,
        new_scroll_integration=False,scroll_runner_prepared_not_run=True,new_frame_timing=False,
        instruction=dict(declared_depth=128,declared_width=32,inferred_depth=int(rom[14]),inferred_width=int(rom[15]),
                         m9ks=int(rom[19]),states=58,predicates=30,ram_commands=17,return_resolvers=9),
        resource={k:board[k] for k in ('map_completed','resource_capacity_pass','le','ff','memory_bits','combinational',
            'source_rows','ram_rows','warnings','fit_returncode','fit_summary','fit_messages')},
        fit_requirement=dict(le=required_le,labs=required_labs,m9ks=m9ks,le_capacity=15408,lab_capacity=963,m9k_capacity=56,
                             pairing=pairing,placed=False),
        comparison240=dict(map_le=board['le']-prior['resource']['le'],combinational=board['combinational']-prior['resource']['combinational'],
                           ff=board['ff']-prior['resource']['ff'],required_le=required_le-prior['fit_requirement']['le'],
                           required_labs=required_labs-prior['fit_requirement']['labs'],m9ks=m9ks-prior['fit_requirement']['m9ks']),
        retired_sdc_identical_to240=True,completed_map_runs=1,elaboration_failed_map_runs=1,fit_runs=1,new_sta=False,
        full_arm=False,physical=False,fps_proven=False,new_package=False,
        public241_pins={n:sha(ROOT/n) for n in names},verified_prior_pins=verified,
        prior240_manifest_sha256=prior['manifest_sha256'],prior_full_rehash=False,
        guards_result_sha256=sha(dest/'guards05/result.json'),board_result_sha256=sha(dest/'board02/result.json'),
        evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'))
    for f in (dest/'verification.json',ROOT/'analysis/source241-verification.json'):f.write_text(json.dumps(result,indent=2)+'\n')
    for rel,row in files.items():assert sha(dest/rel)==row['sha256'],rel
    progress=dict(status='CONTROL_ONLY_ROM_REJECTED',baseline=240,production=227,selected=result['selected'],
        files=len(files),manifest_sha256=result['manifest_sha256'],rehash_files=len(files),public_pins_verified=9,
        prior_pins_verified=len(verified),pushed=False,pr_updated=False,pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='Keep240 and its490LE/40LAB deficit. Do not tune241 PC/ROM/seed or repeat full71/hardware for rejected candidate. Evaluate memory-backed operands plus shared narrow ALU replacing actual wide datapath, with immutable start snapshots/32-bit protocol and port/word/cycle budgets on recorded first-level scroll before next candidate. No proven area/speed gain yet. Then resource gate and actual71 integration, full ARM/IRQ,firstfault/finaldisplay/CDCIOSTA/232fivebursts.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))


if __name__=='__main__':main()
