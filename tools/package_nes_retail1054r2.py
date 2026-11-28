"""Build a replacement retail archive using the original paired board images."""
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import zipfile
import zlib
from prepare_nes_retail1054r2 import ROOT, WORK, OUT
from check_nes_retail1054r2 import check

def sha(data):
    return hashlib.sha256(data).hexdigest()

def package():
    prior=json.loads((ROOT/'analysis/kirby-pair1054.json').read_text(encoding='utf8'))
    artifacts={k:WORK/v['zip'] for k,v in prior.items()}
    for k,path in artifacts.items():
        assert sha(path.read_bytes())==prior[k]['sha256']
    src=OUT/'release/link/src'
    proof=check()
    slots=OUT/'release/slots.json'
    subprocess.run([sys.executable,str(ROOT/'tools/check_ff3_menu_arm.py'),str(src),str(slots)],check=True)
    assert json.loads(slots.read_text())['distinct_slots_reloaded']==4
    fw=(src/'obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992
    assert zlib.crc32(fw[512:])==crc==(inverse^0xffffffff)
    assert b'Starting NES\0' in fw
    assert not any(x in fw for x in (b'/sd2snes/nes-progress-',b'/sd2snes/nes-frame-',b'/sd2snes/nes-game-last-'))
    debug=OUT/artifacts['debug'].name
    shutil.copyfile(artifacts['debug'],debug)
    assert sha(debug.read_bytes())==prior['debug']['sha256']
    target=OUT/'NES-1054r2-RELEASE-SD-ROOT.zip'
    tmp=target.with_suffix('.tmp')
    with zipfile.ZipFile(artifacts['release']) as old, zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as new:
        files={}
        for name,h in prior['release']['files'].items():
            entry='sd2snes/'+name
            data=old.read(entry)
            assert sha(data)==h
            if name=='firmware.stm':
                data=fw
            files[name]=sha(data)
            new.writestr(entry,data)
        manifest=dict(edition=1054,revision=2,profile='release',firmware_bytes=len(fw),files=files)
        new.writestr('manifest.json',json.dumps(manifest,indent=2))
        new.writestr('README-KO.txt',(ROOT/'docs/nes-retail1054r2.ko.md').read_bytes())
    with zipfile.ZipFile(tmp) as z:
        assert not z.testzip() and len(z.namelist())==len(files)+2
        assert all(sha(z.read('sd2snes/'+n))==h for n,h in files.items())
    tmp.replace(target)
    summary=dict(manifest,sha256=sha(target.read_bytes()),debug_sha256=sha(debug.read_bytes()),tests=proof,
                 slots=json.loads(slots.read_text()))
    (ROOT/'analysis/nes-retail1054r2.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf8')
    print(target,len(fw),summary['sha256'])

if __name__=='__main__':
    package()
