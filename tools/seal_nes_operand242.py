# SPDX-License-Identifier: MIT
"""Seal measured operand/lifetime evidence; do not manufacture FIT approval."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import ROOT,BASE,sha

PUBLIC=['tools/nes_operand242.py','tools/profile_nes_source242.py',
        'tools/test_nes_operand242.py','tools/run_nes_source242.ps1',
        'tools/run_nes_operand242.ps1','tools/analyze_nes_operand242.py',
        'tools/profile_nes_lifetime242.py','tools/run_nes_lifetime242.ps1',
        'tools/seal_nes_operand242.py','docs/nes-operand242-contract.ko.md']


def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    names=['test01','test02','guards01','guards02','analysis01','analysis02',
           'lifetime-guards01','lifetime-test01','analysis03']
    paths={n:a.temp_root/('nes-source242-'+n) for n in names}
    read=lambda f:json.loads(f.read_text(encoding='utf-8'))
    base=read(paths['analysis02']/'result.json');life=read(paths['analysis03']/'result.json')
    for test,guard,analysis in [('test02','guards02',base),('lifetime-test01','lifetime-guards01',life)]:
        t=read(paths[test]/'result.json');g=read(paths[guard]/'result.json')
        assert t['passed'] and t['baseline240_cycles_exact'] and g['passed']
        assert (t['frames'],t['records'],t['blocks'],t['payload'],t['exact_c_files'])==(71,2229,350,62967,355)
        assert 'reference_checks=4066624' in t['c_output'] and 'faults_and_restart=1459' in t['c_output']
        assert any('PASS ENCODER240 checks=41 normal=24' in x for x in g['summary'])
        assert any('VIEWS240 stalled=1111111' in x for x in g['summary'])
        assert g['missing_initialization_negative_rejected']
        assert t['instrumented_encoder_sha256']==g['instrumented_sha256']
        assert sha(paths[test]/'nes_source_encoder240.sv')==g['instrumented_sha256']
        assert analysis['result_sha256']==sha(paths[test]/'result.json')
        assert analysis['profile_sha256']==sha(paths[test]/'operands.csv')
        assert analysis['analyzer_sha256']==sha(ROOT/'tools/analyze_nes_operand242.py')
        for k,h in t['source_pins'].items():assert sha(BASE/k)==h,k
        for k,h in t['observer_pins'].items():assert sha(ROOT/k)==h,k
        for k,h in g['pins'].items():assert sha(ROOT/k)==h,k
        assert g['runner_sha256']==sha(ROOT/'tools/test_nes_operand242.py')
        assert g['observer_sha256']==sha(ROOT/'tools/nes_operand242.py')
        if test.startswith('lifetime'):
            assert t['lifetime_write_elision'] and g['lifetime_write_elision']
            assert t['lifetime_runner_sha256']==g['lifetime_runner_sha256']==sha(ROOT/'tools/profile_nes_lifetime242.py')
    assert base['inventory']==life['inventory']
    assert base['inventory']['operand_bytes']==29 and base['inventory']['operand_bits']==204
    saved=base['activity']['executed_write_bytes']-life['activity']['executed_write_bytes']
    assert saved==69*(2112+1792)*3,saved
    assert base['activity']['conservative_read_bytes']==life['activity']['conservative_read_bytes']
    assert base['activity']['selected_arithmetic_byte_ops']==life['activity']['selected_arithmetic_byte_ops']
    assert (paths['test02']/'cycles.csv').read_bytes()==(paths['lifetime-test01']/'cycles.csv').read_bytes()==(BASE/'probes/nes-source240/test01/cycles.csv').read_bytes()
    previous=read(ROOT/'analysis/source241-verification.json')
    prior={**previous['verified_prior_pins'],**previous['public241_pins']}
    for k,h in prior.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    assert sha(BASE/'probes/nes-source241/manifest.json')==previous['manifest_sha256']
    assert not (paths['test01']/'result.json').exists()
    assert not (paths['guards01']/'result.json').exists()
    assert not (paths['analysis01']/'result.json').exists()
    dest.mkdir(parents=True)
    for n,src in paths.items():shutil.copytree(src,dest/n)
    for n in PUBLIC:
        target=dest/'source01'/n;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,target)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)}
           for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=242,files=files),indent=2)+'\n')
    hot=['row_i','old1','old2','new1','new2']
    hybrid={};at=104
    for n,w in base['inventory']['fields'].items():
        if n in hot:continue
        count=(w+7)//8;hybrid[n]=list(range(at,at+count));at+=count
    assert at==128
    ratio=sum(base['fields'][n].get('read_bytes',0)+base['fields'][n].get('write_bytes',0) for n in hot)/(base['activity']['executed_write_bytes']+base['activity']['conservative_read_bytes'])
    result=dict(stage=242,baseline=240,production=227,deployable=False,new_datapath=False,
        decision='Measured hybrid candidate: keep hot5, elide dead FSTORE writes, move24B into existing scratch holes; implement shared ALU before next resource gate.',
        selected=dict(baseline='test02',guards='guards02',baseline_analysis='analysis02',
                      lifetime='lifetime-test01',lifetime_guards='lifetime-guards01',lifetime_analysis='analysis03',source='source01'),
        preserved_sessions=names,failures=dict(test01='Observer token whitespace compile error; no DUT conclusion.',
            guards01='Expected negative fatal detected but process exit0 rejected by harness; normal guards passed.',
            analysis01='Python tuple versus JSON list equality before analysis.'),
        observed_frames_each=71,records_each=2229,blocks_each=350,payload_bytes_each=62967,exact_c_files_each=355,
        synthetic_normal_each=24,guard_checks_each=41,stalled_views_each=7,initialization_negatives_each=1,
        outputs_and_cycles_exact_to240=True,inventory=base['inventory'],
        warm69_baseline_activity=base['activity'],warm69_lifetime_activity=life['activity'],
        removed_dead_write_bytes=saved,removed_write_fraction=saved/base['activity']['executed_write_bytes'],
        hot5_access_fraction=ratio,baseline_policy=base['policy_summary'],lifetime_policy=life['policy_summary'],
        proposed_hybrid_layout=hybrid,proposed_hybrid_byte_indices=list(range(8,32)),
        top_access_states=base['top_access_states'],fields=base['fields'],model_limitations=base['model_limitations'],
        existing240_requirement=dict(le=15898,labs=1003,m9ks=54,le_deficit=490,lab_deficit=40,placed=False),
        new_fit=False,new_sta=False,full_arm=False,physical=False,fps_proven=False,new_package=False,
        public242_pins={n:sha(ROOT/n) for n in PUBLIC},verified_prior_pins=prior,
        prior241_manifest_sha256=previous['manifest_sha256'],prior_full_rehash=False,
        evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'),
        baseline_analysis_sha256=sha(dest/'analysis02/result.json'),lifetime_analysis_sha256=sha(dest/'analysis03/result.json'))
    for rel,row in files.items():assert sha(dest/rel)==row['sha256'],rel
    for f in (dest/'verification.json',ROOT/'analysis/operand242-verification.json'):
        f.write_text(json.dumps(result,indent=2)+'\n')
    progress=dict(status='OPERAND_LIFETIME_MEASURED_SHARED_DATAPATH_NOT_IMPLEMENTED',baseline=240,production=227,
        selected=result['selected'],files=len(files),rehash_files=len(files),manifest_sha256=result['manifest_sha256'],
        public_pins_verified=len(PUBLIC),prior_pins_verified=len(prior),pushed=False,pr_updated=False,
        pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='Implement hot5-retained shared ALU/RF kernel and explicit output latch, bounded actual microprogram/ports/clock cycles; then minimal guards and single resource preflight. No seed/control-only loop.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n')
    print(json.dumps(progress,indent=2))


if __name__=='__main__':main()
