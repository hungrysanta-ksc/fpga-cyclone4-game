# SPDX-License-Identifier: MIT
"""Unchanged227 board collector/exporter with observed-game stimulus adapter."""
from pathlib import Path
import argparse, hashlib, json, os, re, shutil, subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser()
    for n in ('stimulus','out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
    p.add_argument('--first',type=int,default=905);p.add_argument('--last',type=int,default=975)
    a=p.parse_args();d=a.out.resolve();assert str(d).isascii()
    assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
    d.mkdir(parents=True,exist_ok=False)
    prepared=json.loads((a.stimulus/'result.json').read_text());assert prepared['passed']
    assert prepared['first']<=a.first<=a.last<=prepared['last']
    pins={};sources=[]
    for n in ['nes_native_frame201','nes_native_planes165','nes_patch_capture181','nes_patch_rows181','nes_native_compact181','nes_native_raster181','nes_native_export203']:
        src=BASE/'probes/nes-counter224/mapfit02'/(n+'.sv');pins[str(src.relative_to(BASE))]=sha(src)
        shutil.copyfile(src,d/src.name);sources.append(src.name)
    src=ROOT/'tests/nes-functional/geometry230_tb.sv';pins[str(src.relative_to(BASE))]=sha(src)
    shutil.copyfile(src,d/src.name);sources.append(src.name)
    for f in prepared['frames']:
        if a.first<=f['frame']<=a.last:
            name=f"frame{f['frame']}";assert sha(a.stimulus/(name+'.hex'))==f['stimulus_sha256']
            for ext in ['hex','palette']:shutil.copyfile(a.stimulus/(name+'.'+ext),d/(name+'.'+ext))
    for tool,args in [('vlib',['work']),('vlog',['-sv',*sources]),('vsim',['-c','work.geometry230_tb',f'+FIRST={a.first}',f'+LAST={a.last}','-do','onerror {quit -code 1}; run -all; quit -f'])]:
        with (d/(tool+'.log')).open('wb') as log:
            run=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=d,stdout=log,stderr=subprocess.STDOUT,timeout=600,creationflags=subprocess.CREATE_NO_WINDOW)
        text=(d/(tool+'.log')).read_text(errors='replace')
        assert run.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-5000:]
    assert f'PASS GEOMETRY230 frames={a.last-a.first+1}' in text
    result=dict(passed=True,first=a.first,last=a.last,source_pins=pins,runner_sha256=sha(Path(__file__)),
                stimulus_result_sha256=sha(a.stimulus/'result.json'),physical=False,
                scope=__doc__,full_core_equivalence=False,display_ack_fixture=True,
                frames={str(f):{'config':(d/f'frame{f}.cfg').read_text().split(),'wire_sha256':sha(d/f'frame{f}.wire')} for f in range(a.first,a.last+1)})
    (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(passed=True,frames=a.last-a.first+1)))


if __name__=='__main__':main()
