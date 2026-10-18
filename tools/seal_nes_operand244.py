# SPDX-License-Identifier: MIT
"""Seal continuous literal and actual240 byte evidence, not a deployable encoder."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import ROOT,BASE,sha
from nes_operand243 import LAYOUT

PUBLIC=['src/nes/rtl/nes_operand244.sv','tests/nes-functional/operand244_base_tb.sv','tests/nes-functional/literal244_tb.sv',
        'tools/nes_operand244.py','tools/observe_nes_literal244.py','tools/test_nes_operand244.py','tools/run_nes_operand244.ps1',
        'tools/map_nes_operand244.py','tools/seal_nes_operand244.py','docs/nes-operand244-contract.ko.md']

def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    dest=a.archive.resolve();assert not dest.exists();read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    names=['test01','test02','map01'];paths={n:a.temp_root/('nes-operand244-'+n) for n in names}
    t=read(paths['test02']/'result.json');t1=read(paths['test01']/'result.json');m=read(paths['map01']/'result.json')
    assert t['passed'] and t['continuous_commands']==11738 and (t['records'],t['record_bytes'])==(299,4078)
    assert (t['actual240_append_samples'],t['actual240_flush_samples'],t['actual240_flush_records'],t['actual240_flush_bytes'])==(164,166,53,10504)
    assert 'live_cancel=10' in t['summaries'][1] and 'vectors=2798' in t['summaries'][0]
    assert m['passed'] and m['scratch_and_rom_inferred'] and m['test_sha256']==sha(paths['test01']/'result.json')
    for pins in (t['pins'],t['dependency_pins'],m['pins']):
        for f,h in pins.items():assert sha(ROOT/f)==h,f
    for f in ('src/nes/rtl/nes_operand244.sv','tools/nes_operand244.py'):assert t['pins'][f]==t1['pins'][f]==m['pins'][f]
    assert t['program_sha256']==t1['program_sha256']==m['program_sha256']
    assert 'Total logic elements : 373' in m['summary'] and 'Total registers : 102' in m['summary']
    # Stronger than merely replacing all X: every payload byte actually read
    # by a normal/cheap flush must already be initialized in the source240.
    read_payload=0
    for line in (paths['test02']/'baseline/flush-observed.txt').read_text().splitlines():
        flags,res,pre,post,c0,l0,c1,l1,size,packet=line.split()
        prebytes=[pre[i:i+2] for i in range(0,48,2)][::-1]
        used=int(prebytes[LAYOUT['lit_used'][0]-104],16)
        if used and int(res)==0:
            assert 'x' not in l0[-2*used:];read_payload+=used
        if int(size):assert 'x' not in packet[-2*int(size):]
    previous=read(ROOT/'analysis/operand243-verification.json');prior={**previous['verified_prior_pins'],**previous['public243_pins']}
    for f,h in prior.items():assert sha((BASE if f.startswith('probes/') else ROOT)/f)==h,f
    pd=BASE/'probes/nes-operand243';assert sha(pd/'manifest.json')==previous['manifest_sha256'];old=read(pd/'manifest.json')
    for f,v in old['files'].items():assert sha(pd/f)==v['sha256'],f
    dest.mkdir(parents=True)
    for n,path in paths.items():shutil.copytree(path,dest/n)
    for f in PUBLIC:
        q=dest/'source01'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,q)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=244,files=files),indent=2)+'\n')
    for f,v in files.items():assert sha(dest/f)==v['sha256'],f
    result=dict(stage=244,baseline=240,production=227,deployable=False,full_encoder=False,
        selected=dict(test='test02',map='map01',map_bound_test='test01',source='source01'),preserved_sessions=names,
        program_words=301,program_codec_words=268,program_test_words=33,continuous_commands=t['continuous_commands'],command_counts=t['commands'],results=t['results'],
        records=299,record_bytes=4078,actual240_append_samples=164,actual240_flush_samples=166,actual240_flush_records=53,actual240_flush_bytes=10504,
        actual_game_trace=False,semantic_payload_bytes_known=read_payload,unknown_preserved_nibbles_filled_zero=t['unknown_preserved_nibbles_filled_zero'],
        summaries=t['summaries'],map_summary=m['summary'],ram_rows=m['ram_rows'],warnings=m['warnings'],
        existing240_requirement=dict(le_deficit=490,lab_deficit=40,m9k=54),new_fit=False,new_sta=False,new_package=False,physical=False,fps_proven=False,
        public244_pins={f:sha(ROOT/f) for f in PUBLIC},verified_prior_pins=prior,prior243_manifest_sha256=previous['manifest_sha256'],
        prior_full_rehash=len(old['files']),evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'),
        test_sha256=sha(paths['test02']/'result.json'),map_sha256=sha(paths['map01']/'result.json'))
    (ROOT/'analysis/operand244-verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    progress=dict(status='LITERAL_LIFECYCLE_VERIFIED_OUTER_ENCODER_NOT_BOUND',selected=result['selected'],files=len(files),rehash_files=len(files),
        manifest_sha256=result['manifest_sha256'],public_pins_verified=len(PUBLIC),prior_pins_verified=len(prior),prior_full_rehash=len(old['files']),
        pushed=False,pr_updated=False,pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='Bind row/history/shift/raster group/header/trailer/CRC/RAW/ACK flow; remove wide mirrors, account full program301/512 and real cycles; then whole-board gate before71scroll join. Do not repeat isolated literal tests without changes.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
if __name__=='__main__':main()
