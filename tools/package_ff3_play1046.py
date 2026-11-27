"""Package the validated FF3 slot-restart and room-transition board/ARM pair."""
import hashlib
import json
import re
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from nes_cf68_pair_preflight import decode, encode
from package_nes_kirby1027 import timing

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent/'probes/nes-ff3-1046'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package():
    route=WORK/'lite-closed'
    board=timing(route)
    pins=[line.split('\t') for line in (route/'sram.tsv').read_text().splitlines()[1:]]
    assert len({p[0] for p in pins})==3
    assert all({(p[1],p[2]) for p in pins if p[0]==corner}=={
        ('input','setup'),('input','hold'),('output','setup'),('output','hold')} for corner in {p[0] for p in pins})
    raw=(route/'board.rbf').read_bytes()
    image=encode(raw)
    pgm=read(route/'programmer.json')
    assert pgm['passed'] and pgm['rbf_sha256']==digest(raw) and pgm['image_sha256']==digest(image) and decode(image)==raw
    fw=(WORK/'link/src/obj-nes-100/firmware.stm').read_bytes()
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and crc==zlib.crc32(fw[512:])==inv^0xffffffff
    for log in ('nes-progress-ff31046.txt','nes-game-last-ff31046.txt','nes-frame-ff31046.bin'):
        assert log.encode()+b'\0' in fw
    assert read(WORK/'browser-final.json')['firmware_stm_sha256']==digest(fw)
    io=read(WORK/'io-final.json')
    ret=read(WORK/'return-guarded/result.json')
    assert io['state_bytes']==21264 and io['firmware_sha256']==ret['firmware_sha256']==digest(fw)
    assert ret['safe_return'] and ret['base_restored'] and read(WORK/'slots-final.json')['distinct_slots_reloaded']==4
    assert '0 redundant PSRAM reads' in (WORK/'restart-final.txt').read_text()
    assert 'changed selected SD file rejected before START' in (WORK/'restart-final.txt').read_text()
    assert 'PASS cold validation, slot restart' in (WORK/'closed/stop.log').read_text(errors='replace')
    assert 'PASS FF3 mask 256 cases' in (WORK/'closed/mask.log').read_text(errors='replace')
    assert 'PASS FF3 8192B snapshot' in (WORK/'closed/pages.log').read_text(errors='replace')
    assert 'PASS forced blank' in (WORK/'closed/closed-test.log').read_text(errors='replace')
    before=(WORK/'before/vsim-checkpoint.log').read_text(errors='replace')
    replay=(WORK/'closed/vsim-checkpoint.log').read_text(errors='replace')
    pre_drops=before.count('raw_errors=08 raw_rows=7 mask=10')
    # A finite simulation finishes on the last end_scene edge, before that
    # frame's queryable collector state retires. Count actual receipts.
    exits=re.findall(r'COLLECT valid=(\d).*?raw_errors=([0-9a-f]+)',replay)
    rejected=sum(valid=='0' for valid,_ in exits)
    raw_overflow=sum(int(err,16)&8!=0 for _,err in exits)
    scenes=re.findall(r'SCENE f=(\d+) eligible=(\d) conflict=(\d).*?colors=(\d+)',replay)
    unavailable=[int(frame) for frame,ready,_,_ in scenes if ready=='0']
    assert len(scenes)==115 and all(colors=='1' for _,ready,_,colors in scenes if ready=='0')
    assert rejected==0 and raw_overflow==0 and pre_drops and 'PASS FF3 physical scene replay' in replay
    bands=[int(x) for x in re.findall(r'CHECKED_BACKDROP rows=(\d+)',replay)]
    peak=bands.index(max(bands))
    assert len(bands)==len(exits)-rejected and max(bands)>=190 and any(0<x<60 for x in bands[:peak]) and any(0<x<60 for x in bands[peak+1:]) and bands[-1]==0
    assert 'PASS captured frame' in (WORK/'planner-final.txt').read_text()
    prev=read(ROOT/'analysis/ff3-play1045.json')
    old=WORK.parent/'nes-ff3-1045/FF3-1045-NES-PLAY-SD-ROOT.zip'
    assert digest(old.read_bytes())==prev['ZIP_SHA256']
    with zipfile.ZipFile(old) as z:
        files={k:z.read('sd2snes/'+k) for k in prev['files']}
    assert {k:digest(v) for k,v in files.items()}==prev['files']
    files.update({'firmware.stm':fw,'nes-chrram.bi3':image})
    report=dict(edition=1046,hardware_tested=False,flash_bytes=len(fw),board=board,rbf=digest(raw),
                prior_observed_raw_overflows=pre_drops,checked_captures=len(bands), rejected_captures=rejected, raw_overflows=raw_overflow, maximum_backdrop_rows=max(bands),
                observed_frames=len(scenes), unavailable_single_colour_frames=unavailable, physical_load_time_ms=None,files={k:digest(v) for k,v in files.items()})
    name='FF3-1046-NES-PLAY-SD-ROOT.zip'
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        dest=Path(tmp)/name
        with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for k,v in files.items():z.writestr('sd2snes/'+k,v)
            z.writestr('README-KO.txt',(ROOT/'docs/nes-ff3-play1046.ko.md').read_bytes())
            z.writestr('manifest.json',json.dumps(report,indent=2))
        with zipfile.ZipFile(dest) as z:
            assert z.testzip() is None and all(z.read('sd2snes/'+k)==v for k,v in files.items())
        dest.replace(WORK/name)
    report['ZIP_SHA256']=digest((WORK/name).read_bytes())
    (ROOT/'analysis/ff3-play1046.json').write_text(json.dumps(report,indent=2)+'\n')
    print(name,report['ZIP_SHA256'])


if __name__=='__main__':package()
