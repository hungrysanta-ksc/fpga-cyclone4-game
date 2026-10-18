# SPDX-License-Identifier: MIT
"""Seal row kernel evidence and failed sessions, never a full encoder approval."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import ROOT,BASE,sha
from test_nes_operand245 import PUBLIC

FILES=PUBLIC+['tools/map_nes_operand245.py','tools/seal_nes_operand245.py','docs/nes-operand245-contract.ko.md']

def main():
    p=argparse.ArgumentParser();p.add_argument('--temp-root',type=Path,required=True);p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    dest=a.archive.resolve();assert not dest.exists();read=lambda p:json.loads(p.read_text(encoding='utf-8'))
    names=['test01','test02','test03','test04','map01'];paths={n:a.temp_root/('nes-operand245-'+n) for n in names}
    t=read(paths['test04']/'result.json');t3=read(paths['test03']/'result.json');m=read(paths['map01']/'result.json')
    assert t['passed'] and (t['cases'],t['records'],t['record_bytes'],t['chain_commands'])==(2838,1212,9704,281)
    assert sum(t['observed240'].values())==317 and 'rejected=5' in t['summaries'][-1]
    assert m['passed'] and m['scratch_and_rom_inferred'] and m['test_sha256']==sha(paths['test03']/'result.json')
    assert 'Total logic elements : 551' in m['summary'] and 'Total registers : 148' in m['summary']
    for pins in (t['pins'],t['dependency_pins'],m['pins']):
        for f,h in pins.items():assert sha(ROOT/f)==h,f
    for f in ['src/nes/rtl/nes_operand245.sv','tools/nes_operand245.py']:assert t['pins'][f]==t3['pins'][f]==m['pins'][f]
    assert t['program_sha256']==t3['program_sha256']==m['program_sha256']
    # Shift edge bytes are semantic inputs too, not merely known output bytes.
    for line in (paths['test04']/'baseline/rows-observed.txt').read_text().splitlines():
        kind,arg,res,pre,post,o,n,mask,mask1,size,packet=line.split()
        if int(kind)==3:
            edge=n[:4] if int(arg)==1 else n[-4:]
            assert 'x' not in edge
    previous=read(ROOT/'analysis/operand244-verification.json');prior={**previous['verified_prior_pins'],**previous['public244_pins']}
    for f,h in prior.items():assert sha((BASE if f.startswith('probes/') else ROOT)/f)==h,f
    pd=BASE/'probes/nes-operand244';assert sha(pd/'manifest.json')==previous['manifest_sha256'];old=read(pd/'manifest.json')
    for f,v in old['files'].items():assert sha(pd/f)==v['sha256'],f
    dest.mkdir(parents=True)
    for n,path in paths.items():shutil.copytree(path,dest/n)
    for f in FILES:
        q=dest/'source01'/f;q.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/f,q)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=245,files=files),indent=2)+'\n')
    for f,v in files.items():assert sha(dest/f)==v['sha256'],f
    result=dict(stage=245,baseline=240,production=227,deployable=False,full_encoder=False,
        selected=dict(test='test04',map='map01',map_bound_test='test03',source='source01'),preserved_sessions=names,
        program_words=453,program_codec_words=420,program_test_words=33,counts=t['counts'],chain_commands=281,
        observed240=t['observed240'],observed_records=49,observed_bytes=403,cases=2838,records=1212,record_bytes=9704,
        actual_game_trace=False,unknown_unused_nibbles=t['unknown_unused_nibbles'],summaries=t['summaries'],
        map_summary=m['summary'],ram_rows=m['ram_rows'],warnings=m['warnings'],
        existing240_requirement=dict(le_deficit=490,lab_deficit=40,m9k=54),new_fit=False,new_sta=False,new_package=False,physical=False,fps_proven=False,
        public245_pins={f:sha(ROOT/f) for f in FILES},verified_prior_pins=prior,prior244_manifest_sha256=previous['manifest_sha256'],
        prior_full_rehash=len(old['files']),evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'),
        test_sha256=sha(paths['test04']/'result.json'),map_sha256=sha(paths['map01']/'result.json'))
    (ROOT/'analysis/operand245-verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    progress=dict(status='ROW_SHIFT_RASTER_KERNEL_VERIFIED_FULL_ENCODER_UNBOUND',selected=result['selected'],files=len(files),rehash_files=len(files),
        manifest_sha256=result['manifest_sha256'],public_pins_verified=len(FILES),prior_pins_verified=len(prior),prior_full_rehash=len(old['files']),
        pushed=False,pr_updated=False,pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',
        next='Bind actual frame/base/input/row capture + RF/header/trailer/CRC/RAW/ACK, eliminate wide mirrors;453/512 words and full cycles before minimum codec test+single whole-board gate, then71scroll. No more independent row/literal expansion or control-only/seed loops.')
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
if __name__=='__main__':main()
