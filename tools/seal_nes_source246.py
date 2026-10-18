# SPDX-License-Identifier: MIT
"""Seal the full shared encoder and its rejected whole-board resource gate."""
from pathlib import Path
import argparse,json,re,shutil
from nes_delta231 import ROOT,BASE,sha
from test_nes_encoder246 import PUBLIC

FILES=PUBLIC+['tools/map_nes_source246_board.py','tools/seal_nes_source246.py','docs/nes-source246-contract.ko.md']

def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    dest=a.archive.resolve();assert not dest.exists();read=lambda f:json.loads(f.read_text(encoding='utf-8'))
    sessions=['guards01','guards02','guards03','guards04','board01'];paths={s:a.temp_root/('nes-source246-'+s) for s in sessions}
    g=read(paths['guards04']/'result.json');b=read(paths['board01']/'result.json')
    assert g['passed'] and g['program_words']==408
    assert any('PASS ENCODER246 checks=42 normal=25' in s for s in g['summaries'])
    assert any('LASTBYTE246 stall256=1' in s for s in g['summaries'])
    assert any('VIEWS246 stalled=1111111' in s for s in g['summaries'])
    for f,h in g['pins'].items():assert sha(ROOT/f)==h,f
    for f,h in g['fixture_pins'].items():assert sha(BASE/'probes/nes-source240/guards01'/f)==h,f
    for f,h in b['source_pins'].items():assert sha(BASE/f)==h,f
    assert b['runner_sha256']==sha(ROOT/'tools/map_nes_source246_board.py')
    assert b['guards_result_sha256']==sha(paths['guards04']/'result.json')
    assert b['program_sha256']==g['program_sha256']
    assert b['map_completed'] and b['new_fit'] and not b['resource_capacity_pass']
    assert b['preflight_only'] and b['joint_result_sha256'] is None
    assert len(b['retired_sdc_rows'])==216
    assert sha(paths['board01']/'cdc181.sdc')==sha(BASE/'probes/nes-source240/board01/cdc181.sdc')
    fr=(paths['board01']/'output_files/board.fit.rpt').read_text(encoding='latin-1')
    le=int(re.search(r'Total logic elements\s*:\s*([\d,]+)',b['fit_summary'])[1].replace(',',''))
    labs=int(re.search(r'Fitter requires (\d+) LABs','\n'.join(b['fit_messages']))[1])
    m9k=int(re.search(r'; M9Ks\s*; (\d+) / 56',fr)[1]);assert (le,labs,m9k)==(16027,1011,55)
    pairing={k:int(re.search(re.escape(label)+r'\s*;\s*(\d+)',fr)[1]) for k,label in
        [('lut_only','-- Combinational with no register'),('register_only','-- Register only'),('lut_register','-- Combinational with a register')]}
    assert pairing==dict(lut_only=7492,register_only=1000,lut_register=7535)
    previous=read(ROOT/'analysis/operand245-verification.json');prior={**previous['verified_prior_pins'],**previous['public245_pins']}
    for f,h in prior.items():assert sha((BASE if f.startswith('probes/') else ROOT)/f)==h,f
    pd=BASE/'probes/nes-operand245';assert sha(pd/'manifest.json')==previous['manifest_sha256'];old=read(pd/'manifest.json')
    for f,v in old['files'].items():assert sha(pd/f)==v['sha256'],f
    cycles=[int(re.search(r'cycles=(\d+)',s)[1]) for s in g['summaries'] if 'case=' in s]
    assert len(cycles)==25 and min(cycles)==130097 and max(cycles)==1043674
    # The assembler imports245 and the added fixture uses the old234 oracle.
    # Their bytes must already belong to the verified immutable public chain.
    for f in ('tools/nes_operand245.py','tools/nes_stream234.py','tools/test_nes_operand243.py'):assert f in prior,f
    dest.mkdir(parents=True)
    for n,path in paths.items():shutil.copytree(path,dest/n)
    for f in FILES:
        q=dest/'source01'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,q)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=246,files=files),indent=2)+'\n')
    for f,v in files.items():assert sha(dest/f)==v['sha256'],f
    result=dict(stage=246,adopted=False,baseline=240,production=227,deployable=False,full_encoder=True,
        decision='Reject246: shared operands plus external frame controller increase whole-board FIT129LE/8LAB/1M9K versus240.',
        selected=dict(guards='guards04',board='board01',source='source01'),preserved_sessions=sessions,
        program_words=408,program_sha256=g['program_sha256'],normal_frames=25,guard_cases=17,checks=42,stalled_views=7,last_byte_stall_cycles=256,
        full_encoder_cycles=cycles,actual_collector=False,actual_spi=False,new_scroll_integration=False,
        resource={k:b[k] for k in ('le','combinational','ff','memory_bits','source_rows','ram_rows','warnings','fit_summary','fit_messages')},
        fit_requirement=dict(le=le,labs=labs,m9ks=m9k,le_deficit=619,lab_deficit=48,placed=False,pairing=pairing),
        comparison240=dict(map_le=75,combinational=61,ff=-42,required_le=129,required_labs=8,m9ks=1),
        encoder=dict(combinational=1424,ff=367,controller_combinational=827,controller_ff=222,engine_combinational=597,engine_ff=145),
        completed_map_runs=1,fit_runs=1,new_sta=False,full_arm=False,new_package=False,physical=False,fps_proven=False,
        retired_sdc_identical_to240=True,public246_pins={f:sha(ROOT/f) for f in FILES},verified_prior_pins=prior,
        prior245_manifest_sha256=previous['manifest_sha256'],prior_full_rehash=len(old['files']),
        evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'),
        guards_sha256=sha(paths['guards04']/'result.json'),board_sha256=sha(paths['board01']/'result.json'))
    for f in (ROOT/'analysis/source246-verification.json',dest/'verification.json'):f.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    progress=dict(status='FULL_SHARED_ENCODER_REJECTED_RESOURCE_GATE',selected=result['selected'],files=len(files),rehash_files=len(files),
        manifest_sha256=result['manifest_sha256'],public_pins_verified=len(FILES),prior_pins_verified=len(prior),prior_full_rehash=len(old['files']),
        pushed=False,pr_updated=False,pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='Keep240 baseline/227 production. Stop246 microtuning and independent opcode expansion. Compare whole control+datapath consolidation (one sequencer instead of external continuation+engine PC) against240 cross-path dedup, with actual area/512word/1M9K/cycle budget BEFORE implementation. No proven saving. Minimal whole-codec gate then single board gate then71scroll only on fit pass; full ARM/firstfault/displaylease/CDCIOSTA/232fivebursts remain.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
if __name__=='__main__':main()
