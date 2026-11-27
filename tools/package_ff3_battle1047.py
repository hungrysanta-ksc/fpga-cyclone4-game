"""Package the validated FF3 battle rendering board/ARM pair."""
import hashlib
import json
import struct
import tempfile
import zipfile
import zlib
from pathlib import Path

from nes_cf68_pair_preflight import decode, encode
from package_nes_kirby1027 import timing

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent/'probes/nes-ff3-1047'


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def package():
    route=WORK/'lite'
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
    for log in ('nes-progress-ff31047.txt','nes-game-last-ff31047.txt','nes-frame-ff31047.bin'):
        assert log.encode()+b'\0' in fw
    assert read(WORK/'browser.json')['firmware_stm_sha256']==digest(fw)
    io=read(WORK/'io.json')
    ret=read(WORK/'return-final/result.json')
    assert io['state_bytes']==21264 and io['firmware_sha256']==ret['firmware_sha256']==digest(fw)
    assert ret['safe_return'] and ret['base_restored'] and read(WORK/'slots.json')['distinct_slots_reloaded']==4
    assert '0 redundant PSRAM reads' in (WORK/'restart.txt').read_text()
    assert 'changed selected SD file rejected before START' in (WORK/'restart.txt').read_text()
    assert 'PASS cold validation, slot restart' in (WORK/'test/stop.log').read_text(errors='replace')
    assert 'PASS FF3 mask 256 cases' in (WORK/'test/mask.log').read_text(errors='replace')
    assert 'PASS FF3 8192B snapshot' in (WORK/'test/pages.log').read_text(errors='replace')
    assert 'PASS forced blank' in (WORK/'test/closed-test.log').read_text(errors='replace')
    replay=(WORK/'test/vsim-checkpoint.log').read_text(errors='replace')
    assert 'PASS FF3 physical scene replay' in replay and 'PASS FF3 64 reference flash frames' in (WORK/'reference-test/battle-test.log').read_text(errors='replace')
    assert 'PASS FF3 battle palettes' in (WORK/'test/battle-test.log').read_text(errors='replace')
    assert replay.count('# SCENE f=')==65 and '# COLLECT valid=0' not in replay
    results={}
    for stride in (1,3):
        r=read(WORK/f'compare-{stride}.json')
        if stride==1:assert r['checked_flash_cgram_frames']==64
        assert r['stride']==stride and r['frames']>=20 and all(a['image']==b['image'] for a,b in zip(r['before'],r['after'],strict=True))
        assert r['old_firmware_sha256']==read(ROOT/'analysis/ff3-play1046.json')['files']['firmware.stm']
        assert r['new_firmware_sha256']==digest(fw)
        results[str(stride)]={k:{name:sum(x[name] for x in r[k]) for name in ('commands','tile_bytes','descriptor_bytes')} for k in ('before','after')}
        results[str(stride)]['frames']=r['frames']
        assert results[str(stride)]['before']['tile_bytes']>results[str(stride)]['after']['tile_bytes']
    reference=read(WORK/'attack/reference.json')
    assert reference['clean_frames']>0 and reference['changed_screens']>0
    prev=read(ROOT/'analysis/ff3-play1046.json')
    old=WORK.parent/'nes-ff3-1046/FF3-1046-NES-PLAY-SD-ROOT.zip'
    assert digest(old.read_bytes())==prev['ZIP_SHA256']
    with zipfile.ZipFile(old) as z:
        files={k:z.read('sd2snes/'+k) for k in prev['files']}
    assert {k:digest(v) for k,v in files.items()}==prev['files']
    files.update({'firmware.stm':fw,'nes-chrram.bi3':image})
    report=dict(edition=1047,hardware_tested=False,flash_bytes=len(fw),board=board,rbf=digest(raw),
                palette_alternations=32,arm_replay=results,attack_reference=reference,
                physical_battle_fps=None,files={k:digest(v) for k,v in files.items()})
    name='FF3-1047-NES-PLAY-SD-ROOT.zip'
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        dest=Path(tmp)/name
        with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for k,v in files.items():z.writestr('sd2snes/'+k,v)
            guide=(ROOT/'docs/nes-ff3-battle1047.ko.md').read_text(encoding='utf-8')
            guide=guide.split('\n이전 실기판의 슬롯 재시작')[0]
            guide=guide.replace('[검증 결과](../analysis/ff3-battle1047.json)','manifest.json')
            z.writestr('README-KO.txt',guide.encode('utf-8'))
            z.writestr('manifest.json',json.dumps(report,indent=2))
        with zipfile.ZipFile(dest) as z:
            assert z.testzip() is None and all(z.read('sd2snes/'+k)==v for k,v in files.items())
        dest.replace(WORK/name)
    report['ZIP_SHA256']=digest((WORK/name).read_bytes())
    (ROOT/'analysis/ff3-battle1047.json').write_text(json.dumps(report,indent=2)+'\n')
    print(name,report['ZIP_SHA256'])


if __name__=='__main__':package()
