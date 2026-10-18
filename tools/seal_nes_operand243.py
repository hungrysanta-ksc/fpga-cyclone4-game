# SPDX-License-Identifier: MIT
"""Seal an unbound shared kernel, including the rejected RAM-inference attempt."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import ROOT,BASE,sha

PUBLIC=['src/nes/rtl/nes_operand243.sv','tests/nes-functional/operand243_tb.sv',
        'tools/nes_operand243.py','tools/test_nes_operand243.py','tools/run_nes_operand243.ps1',
        'tools/map_nes_operand243.py','tools/seal_nes_operand243.py','docs/nes-operand243-contract.ko.md']

def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    dest=a.archive.resolve();assert not dest.exists();read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    names=[f'test{i:02d}' for i in range(1,7)]+['map01','map02'];paths={n:a.temp_root/('nes-operand243-'+n) for n in names}
    t=read(paths['test06']/'result.json');t5=read(paths['test05']/'result.json');m=read(paths['map02']/'result.json')
    assert t['passed'] and t['total_vectors']==2798 and sum(t['actual240_sampled_by_command'])==1006
    assert 'publication_cancel=3' in t['kernel_summary'][0] and 'cancel_phases=92' in t['kernel_summary'][0]
    assert m['passed'] and m['scratch_and_rom_inferred'] and m['test_sha256']==sha(paths['test05']/'result.json')
    for pins in (t['pins'],m['pins']):
        for f,h in pins.items():assert sha(ROOT/f)==h,f
    for f in ('src/nes/rtl/nes_operand243.sv','tools/nes_operand243.py'):assert t['pins'][f]==t5['pins'][f]==m['pins'][f]
    assert t['program_sha256']==t5['program_sha256']==m['program_sha256']
    assert 'Total logic elements : 227' in m['summary'] and 'Total registers : 68' in m['summary']
    assert 'RAM logic "scratch" is uninferred due to asynchronous read logic' in (paths['map01']/'map.log').read_text()
    previous=read(ROOT/'analysis/operand242-verification.json')
    prior={**previous['verified_prior_pins'],**previous['public242_pins']}
    for f,h in prior.items():assert sha((BASE if f.startswith('probes/') else ROOT)/f)==h,f
    prior_dir=BASE/'probes/nes-source242';assert sha(prior_dir/'manifest.json')==previous['manifest_sha256']
    oldmanifest=read(prior_dir/'manifest.json')
    for f,v in oldmanifest['files'].items():assert sha(prior_dir/f)==v['sha256'],f
    dest.mkdir(parents=True)
    for n,path in paths.items():shutil.copytree(path,dest/n)
    for f in PUBLIC:
        q=dest/'source01'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,q)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=243,files=files),indent=2)+'\n')
    for f,v in files.items():assert sha(dest/f)==v['sha256'],f
    result=dict(stage=243,baseline=240,production=227,deployable=False,full_encoder=False,new_datapath='unbound_shared_byte_kernel',
        selected=dict(test='test06',map='map02',map_bound_test='test05',source='source01'),preserved_sessions=names,
        operations=t['actual240_sampled_by_command'],randomized_vectors=1792,total_vectors=2798,program_words=95,codec_operation_words=83,
        prepared_rf=True,actual_game_trace=False,kernel_summary=t['kernel_summary'],baseline_summary=t['baseline_summary'],
        unknown_unread_preserved_bytes_filled_zero=1,map_summary=m['summary'],ram_rows=m['ram_rows'],warnings=m['warnings'],
        rejected_map01=dict(reason='scratch uninferred due to asynchronous read logic',logic_elements=7796,registers=4180),
        existing240_requirement=dict(le_deficit=490,lab_deficit=40,m9k=54),new_fit=False,new_sta=False,new_package=False,physical=False,fps_proven=False,
        failures=dict(test01='Observer timescale missing.',test02='IDLE wrongly gated by previous generation lease; zero INIT samples.',test03='Unused preserved X byte could not parse; semantic input and written-result checks added.'),
        public243_pins={f:sha(ROOT/f) for f in PUBLIC},verified_prior_pins=prior,prior242_manifest_sha256=previous['manifest_sha256'],
        prior_full_rehash=len(oldmanifest['files']),evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'),
        test_sha256=sha(paths['test06']/'result.json'),map_sha256=sha(paths['map02']/'result.json'))
    (ROOT/'analysis/operand243-verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    progress=dict(status='SHARED_KERNEL_VERIFIED_NOT_BOUND_TO_ENCODER',selected=result['selected'],files=len(files),rehash_files=len(files),
        manifest_sha256=result['manifest_sha256'],public_pins_verified=len(PUBLIC),prior_pins_verified=len(prior),prior_full_rehash=len(oldmanifest['files']),
        pushed=False,pr_updated=False,pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='Bind hot5 plus kernel RF by replacing wide updates; implement literal/payload port arbitration and full control microprogram; then minimal reference/whole-board resource gate before71frame join.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
if __name__=='__main__':main()
