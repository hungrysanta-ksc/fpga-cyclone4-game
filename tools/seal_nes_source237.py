# SPDX-License-Identifier: MIT
"""Seal actual237 source join and resource gate without shipping game data."""
from pathlib import Path
import argparse,csv,json,shutil,statistics
from nes_delta231 import ROOT,BASE,sha

def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    paths={n:a.temp_root/('nes-encoder237-'+n) for n in ('test01','test02','test03','test04','guards01','guards02','board01','board02','board03')}
    joint=read(paths['test04']/'result.json');guards=read(paths['guards02']/'result.json');board=read(paths['board03']/'result.json')
    assert joint['passed'] and joint['frames']==71 and joint['exact_c_files']==355 and guards['passed']
    assert board['joint_result_sha256']==sha(paths['test04']/'result.json') and board['guards_result_sha256']==sha(paths['guards02']/'result.json')
    assert (paths['test03']/'cycles.csv').read_bytes()==(paths['test04']/'cycles.csv').read_bytes(),'RAM port repair changed cycle behavior'
    for k,h in joint['source_pins'].items():assert sha(BASE/k)==h,k
    for k,h in guards['pins'].items():assert sha(ROOT/k)==h,k
    for k,h in board['source_pins'].items():assert sha(BASE/k)==h,k
    prior=read(ROOT/'analysis/path236-verification.json');verified={**prior['verified_prior_pins'],**prior['public236_pins']}
    for k,h in verified.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    assert sha(BASE/'probes/nes-path236/manifest.json')==prior['manifest_sha256']
    assert board['fit_returncode']!=0 and len(board['retired_sdc_rows'])==216
    assert any('170011' in x and '15664' in x and '15408' in x for x in board['fit_messages'])
    assert not any('332000' in x or 'Read_sdc failed' in x for x in board['fit_messages'])
    rows=[{k:int(v) for k,v in r.items()} for r in csv.DictReader((paths['test04']/'cycles.csv').open())]
    assert len(rows)==71 and all(r['total']==sum(r[k] for k in ('prepare','blocked','ackwait','transfer')) for r in rows)
    warm=[r for r in rows if r['frame']>=907];stats={}
    for key in ('total','prepare','blocked','ackwait','transfer'):
        v=[r[key] for r in warm];stats[key]=dict(min_cycles=min(v),mean_cycles=statistics.mean(v),max_cycles=max(v),max_ms=max(v)*45.454/1e6)
    stats['cold905']=rows[0];stats['worst']=max(warm,key=lambda r:r['total']);stats['overlap_writes']=sum(r['overlap'] for r in rows)
    stats['window']='907..975, same69 comparison frames; only905 is source-cold,906 is second output-bank cold'
    stats['scope']='source clock45.454ns model, host11.904ns, SPI2.625MHz bit stimulus; no ARM processing/shared other SPI traffic or actual SNES/display timing. ackwait includes last block draining, not ACK latency alone.'
    names=['src/nes/rtl/nes_source_encoder237.sv','src/nes/rtl/nes_source237.sv',
        'tests/nes-functional/source_encoder237_tb.sv',
        'tools/test_nes_source237.py','tools/test_nes_encoder237.py','tools/run_nes_source237.ps1',
        'tools/map_nes_source237_board.py','tools/seal_nes_source237.py','docs/nes-source237-contract.ko.md']
    assert sha(ROOT/'tools/test_nes_source237.py')==joint['runner_sha256']
    assert sha(ROOT/'tools/test_nes_encoder237.py')==guards['runner_sha256']
    dest.mkdir(parents=True)
    for n,src in paths.items():shutil.copytree(src,dest/n)
    for n in names:
        target=dest/'source01'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=237,files=files),indent=2)+'\n')
    public=dict(stage=237,functional_passed=True,deployable=False,scope=joint['scope'],
        selected=dict(joint='test04',guards='guards02',board='board03',source='source01'),
        frames=71,records=joint['records'],blocks=joint['blocks'],payload=joint['payload'],exact_c_files=355,c_output=joint['c_output'],
        encoder_guards=36,synthetic_frames=20,cycles=stats,query_state_fused=False,
        resource={k:board[k] for k in ('map_completed','resource_capacity_pass','le','ff','memory_bits','combinational',
            'baseline_map_le','baseline_map_combinational','baseline_fit_le','ram_rows','source_rows','warnings','fit_returncode','fit_summary','fit_messages')},
        retired_sdc_rows=216,retired_sdc_sha256=sha(dest/'board03/cdc181.sdc'),
        resource_blocker='Fitter170011:15664 combinational nodes vs15408 capacity;256 is only a minimum deficit, not a sufficient LE/LAB/timing/headroom reduction target.',
        new_fit=board['new_fit'],new_sta=False,full_arm=False,physical=False,fps_proven=False,new_package=False,
        public237_pins={n:sha(ROOT/n) for n in names},verified_prior_pins=verified,
        prior236_manifest_sha256=prior['manifest_sha256'],prior_full_rehash=False,
        joint_result_sha256=sha(dest/'test04/result.json'),guards_result_sha256=sha(dest/'guards02/result.json'),board_result_sha256=sha(dest/'board03/result.json'),
        evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'))
    for f in (dest/'verification.json',ROOT/'analysis/source237-verification.json'):f.write_text(json.dumps(public,indent=2)+'\n')
    progress=dict(status='ENCODER_SPI_C_EXACT_RESOURCE_GATE_OPEN',selected=public['selected'],files=len(files),manifest_sha256=public['manifest_sha256'],
        next='Use measured whole-board resource gap to fuse query/cursor/copy/control state while retaining full shift+raster+literal and RAM ports. No FIT seed loop or hardware package before resource/ARM/CDC/IO/STA and final display lifecycle gates. Preserve232 five VRAM bursts as independent open work.',
        pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',pushed=False,pr_updated=False)
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
if __name__=='__main__':main()
