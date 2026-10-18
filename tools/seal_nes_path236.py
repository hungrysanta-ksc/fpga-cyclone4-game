# SPDX-License-Identifier: MIT
"""Seal236 route decision; keep ROM-derived streams/executables private."""
from pathlib import Path
import argparse,json,shutil
from nes_delta231 import ROOT,BASE,sha

def main():
    p=argparse.ArgumentParser()
    for n in ('map','analysis','archive'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();dest=a.archive.resolve();assert not dest.exists()
    read=lambda f:json.loads(f.read_text(encoding='utf-8'))
    r=read(a.analysis/'result.json');m=read(a.map/'result.json');prior=read(ROOT/'analysis/source235-verification.json')
    assert r['passed'] and m['passed'] and sha(a.map/'result.json')==r['map_result_sha256']
    verified={**prior['verified_prior_pins'],**prior['public235_pins']}
    for k,h in verified.items():assert sha((BASE if k.startswith('probes/') else ROOT)/k)==h,k
    for project in m['projects'].values():
        for k,h in project['pins'].items():assert sha(BASE/k)==h,k
    assert r['prior235_manifest_sha256']==prior['manifest_sha256']==sha(BASE/'probes/nes-source235/manifest.json')
    assert r['resource']['omitted235_le']==269 and r['resource']['mixed_fit_map_residual_arithmetic']==430
    assert [len(r['cases'][n]['over_ready4']) for n in ('full','shift','literal')]==[0,8,22]
    assert len(r['parallel']['output_only_over_60hz'])==69
    sources=[ROOT/'tools'/n for n in ('map_nes_path236.py','analyze_nes_path236.py','seal_nes_path236.py')]+[ROOT/'docs/nes-path236-contract.ko.md']
    dest.mkdir(parents=True);shutil.copytree(a.map,dest/'map01');shutil.copytree(a.analysis,dest/'analysis02')
    failed=dest/'analysis01';failed.mkdir()
    (failed/'failure.txt').write_text('Initial analysis stopped before any C run. Quartus board.fit.rpt was opened with default UTF-8. UnicodeDecodeError: byte0xb0 at position772322. Fixed by explicit latin-1; original report unchanged.\n')
    (failed/'analyzer.py').write_text((ROOT/'tools/analyze_nes_path236.py').read_text().replace("fittext=fit.read_text(encoding='latin-1')","fittext=fit.read_text()"),newline='\n')
    for f in sources:
        to=dest/'source01'/f.relative_to(ROOT);to.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(f,to)
    files={str(f.relative_to(dest)).replace('\\','/'):{'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(dest.rglob('*')) if f.is_file()}
    (dest/'manifest.json').write_text(json.dumps(dict(stage=236,files=files),indent=2)+'\n')
    public=dict(stage=236,passed=True,scope=r['scope'],selected=dict(map='map01',analysis='analysis02',source='source01'),resource=r['resource'],
        candidates={n:{k:v for k,v in case.items() if k!='rows'} for n,case in r['cases'].items()},
        parallel={k:v for k,v in r['parallel'].items() if k!='rows'},
        decision='Retain full A row-shift+raster+literal.235reclaim arithmetic omitted269LE records/ACK mailboxes. Full encoder gate remains open; target old1392LE footprint before spending159LE margin. Reject tested literal-only/shift-only and output-only B. Next fused query/base/encoder/raw->235SPI->actualC,then whole-board resource/CDC/IO/STA/inputRUN before physical trial.',
        source235_modified=False,encoder_rtl_complete=False,new_fit=False,new_sta=False,physical=False,fps_proven=False,new_package=False,
        source_pins=r['pins'],public236_pins={str(f.relative_to(ROOT)).replace('\\','/'):sha(f) for f in sources},verified_prior_pins=verified,
        map_result_sha256=sha(dest/'map01/result.json'),analysis_result_sha256=sha(dest/'analysis02/result.json'),
        prior235_manifest_sha256=r['prior235_manifest_sha256'],prior235_full_rehash=False,evidence_files=len(files),manifest_sha256=sha(dest/'manifest.json'))
    for f in (dest/'verification.json',ROOT/'analysis/path236-verification.json'):f.write_text(json.dumps(public,indent=2)+'\n')
    progress=dict(status='FULL_A_RETAINED_RECLAIM_CORRECTED_ENCODER_GATE_OPEN',selected=public['selected'],files=len(files),manifest_sha256=public['manifest_sha256'],
        next=public['decision'],pr='https://github.com/hungrysanta-ksc/fpga-cyclone4-game/pull/127',pushed=False,pr_updated=False)
    (dest/'progress.json').write_text(json.dumps(progress,indent=2)+'\n');print(json.dumps(progress,indent=2))
if __name__=='__main__':main()
