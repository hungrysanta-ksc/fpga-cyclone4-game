# SPDX-License-Identifier: MIT
"""Select immutable211 C/ARM evidence; never approve firmware from a host model."""
from pathlib import Path
import argparse,json,re
from nes_resident211 import ROOT,BASE,sha
def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);a=p.parse_args()
    a.archive=a.archive.resolve();out=a.archive/'evidence01';out.mkdir(exist_ok=False)
    test=json.loads((a.archive/'test04/verification.json').read_bytes())
    arm=json.loads((a.archive/'arm03/result.json').read_bytes())
    prep=json.loads((a.archive/'test04/preparation.json').read_bytes())
    for name,digest in prep['inputs'].items():assert sha(BASE/name)==digest,name
    for name,digest in prep['generated'].items():assert sha(a.archive/'test04'/name)==digest,name
    for name,digest in arm['input_pins'].items():
        assert sha(a.archive/'test04'/name)==digest and sha(a.archive/'arm03'/name)==digest,name
    for name,digest in test['logs'].items():assert sha(a.archive/'test04'/name)==digest,name
    for name,digest in test['sources'].items():assert sha(ROOT/name)==digest,name
    assert sha(ROOT/'tools/check_nes_resident211_arm.py')==arm['script_sha256']
    log=test['output'];assert log==(a.archive/'test04/host.log').read_text()
    assert 'frames=129 referenced_bytes=4234944' in log and 'boundaries=11 ' in log
    assert 'synthetic_frames=96 pattern_old=182784 pattern_new=5664 map_new=87040' in log
    assert arm['layout']==dict(resident_bytes=3200,video_bytes=15912)
    sources=['src/nes/firmware/nes_resident211.c','src/nes/firmware/nes_resident211.h',
             'tests/nes-functional/resident211_host.c','tools/nes_resident211.py',
             'tools/test_nes_resident211.py','tools/check_nes_resident211_arm.py',
             'tools/nes_resident211_evidence.py','docs/nes-resident211-contract.ko.md']
    result=dict(passed=True,selected=['test04','arm03'],merged_pr119='e0a924793dfc5f750543ccb84c65fc891fdbf41a',
        branch='codex/nes-resident-slots-211',
        gates={n:sha(a.archive/n) for n in ['test04/verification.json','arm03/result.json']},
        host=test,arm=arm,public_sources={n:sha(ROOT/n) for n in sources},
        synthetic_scroll=dict(frames=96,pattern_before=182784,pattern_after=5664,
            pattern_reduction_percent=100*(1-5664/182784),map_before=393216,map_after=87040,
            map_reduction_percent=100*(1-87040/393216),actual_game=False,physical_fps=False),
        decision=dict(deployable=False,full_arm=False,new_fit=False,new_package=False,
            sparse_snes_consumer=False,source_ingress_unchanged=True,circular_scroll_map=False,
            next='Bind sparse C transport and actual65816 destination-bank dirty consumer; replace full compare/fallback within existing4KiB ROM, preserve base/epoch/coverage/token/STOP/finalACK. Then fullARM and minimal board proof -> paired physical video trial. No isolated cache/FIT/poll loop.'),
        user_next_trial='Video from just before loading ends through menu return; no repeat210 required. Last~5s of210 was first level, per correction.')
    text=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    (out/'verification.json').write_text(text,encoding='utf8',newline='\n')
    (ROOT/'analysis/resident211-verification.json').write_text(text,encoding='utf8',newline='\n')
    files={str(f.relative_to(a.archive)):sha(f) for f in sorted(a.archive.rglob('*')) if f.is_file()}
    (out/'manifest.json').write_text(json.dumps(files,indent=2)+'\n',encoding='utf8')
    (a.archive/'progress.json').write_text(json.dumps(dict(status='candidate_c_verified_not_deployable',
        selected=['test04','arm03','evidence01'],next=result['decision']['next'],
        evidence_sha256=sha(out/'verification.json'),manifest_sha256=sha(out/'manifest.json'),files=len(files)),indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,files=len(files),synthetic_scroll=result['synthetic_scroll'],decision=result['decision'])))
if __name__=='__main__':main()
