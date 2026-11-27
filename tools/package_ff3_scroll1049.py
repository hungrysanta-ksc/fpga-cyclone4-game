"""Bundle the tested ARM link with the exact hardware-confirmed FF3 1048 board."""
from pathlib import Path
import json
import struct
import tempfile
import zipfile
import zlib

from package_ff3_battle1047 import digest, read

ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT.parent/'probes/nes-ff3-1049'


def package():
    prev=read(ROOT/'analysis/ff3-walk1048.json')
    old=WORK.parent/'nes-ff3-1048/FF3-1048-NES-PLAY-SD-ROOT.zip'
    assert digest(old.read_bytes())==prev['ZIP_SHA256']
    with zipfile.ZipFile(old) as z:
        files={k:z.read('sd2snes/'+k) for k in prev['files']}
    assert {k:digest(v) for k,v in files.items()}==prev['files']
    fw=(WORK/'link-D/src/obj-nes-100/firmware.stm').read_bytes()
    size,crc,inv=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and crc==zlib.crc32(fw[512:])==inv^0xffffffff
    for name in ('nes-progress-ff31049.txt','nes-game-last-ff31049.txt','nes-frame-ff31049.bin'):
        assert name.encode()+b'\0' in fw
    pair=read(WORK/'final.json')
    io=read(WORK/'io.json')
    ret=read(WORK/'return/result.json')
    assert pair['firmware']==[prev['files']['firmware.stm'],digest(fw)]
    assert io['firmware_sha256']==ret['firmware_sha256']==digest(fw)
    assert ret['passed'] and ret['safe_return'] and ret['base_restored'] and io['state_bytes']==21264
    assert read(WORK/'slots.json')['distinct_slots_reloaded']==4
    assert len(pair['scenes'])==3 and pair['battle_checked_frames']>=20
    totals={name:row['scores'] for name,row in pair['scenes'].items()}
    assert all(new<before for before,new in totals.values())
    files['firmware.stm']=fw
    hashes={k:digest(v) for k,v in files.items()}
    assert [k for k in hashes if hashes[k]!=prev['files'][k]]==['firmware.stm']
    report=dict(edition=1049,board_from=1048,flash_bytes=len(fw),files=hashes,
                hardware_fps=None,arm_planner_instructions=totals,battle_checked_frames=pair['battle_checked_frames'])
    name='FF3-1049-NES-PLAY-SD-ROOT.zip'
    with tempfile.TemporaryDirectory(dir=WORK) as tmp:
        path=Path(tmp)/name
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as dst:
            for k,v in files.items():
                dst.writestr('sd2snes/'+k,v)
            dst.writestr('README-KO.txt',(ROOT/'docs/nes-ff3-scroll1049.ko.md').read_bytes())
            dst.writestr('manifest.json',json.dumps(report,indent=2))
        with zipfile.ZipFile(path) as dst:
            assert dst.testzip() is None and all(dst.read('sd2snes/'+k)==v for k,v in files.items())
        path.replace(WORK/name)
    report['ZIP_SHA256']=digest((WORK/name).read_bytes())
    (ROOT/'analysis/ff3-scroll1049.json').write_text(json.dumps(report,indent=2)+'\n')
    print(name,report['ZIP_SHA256'])


if __name__=='__main__':
    package()
