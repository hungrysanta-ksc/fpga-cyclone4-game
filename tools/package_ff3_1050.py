"""Verify the final ARM, routed ROM and hardware-log identities before packaging."""
import json
import struct
import zipfile
import zlib
from pathlib import Path

from package_ff3_battle1047 import read, digest
from package_nes_kirby1027 import timing, programmer

def package():
    root=Path(__file__).resolve().parents[1]
    work=root.parent/'probes/nes-ff3-1050'
    old=work.parent/'nes-ff3-1049/FF3-1049-NES-PLAY-SD-ROOT.zip'
    prev=read(root/'analysis/ff3-scroll1049.json')
    assert digest(old.read_bytes())==prev['ZIP_SHA256']
    with zipfile.ZipFile(old) as z:
        files={k:z.read('sd2snes/'+k) for k in prev['files']}
    assert {k:digest(v) for k,v in files.items()}==prev['files']
    cpu=read(work/'client-tests.json')
    assert cpu['pixels_and_wrong_indices']['after']==[51712,0] and cpu['pad_test_fields']==148
    fw=(work/'link/src/obj-nes-100/firmware.stm').read_bytes()
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and zlib.crc32(fw[512:])==crc==inverse^0xffffffff
    for name in ('nes-progress-ff31050.txt','nes-game-last-ff31050.txt','nes-frame-ff31050.bin'):
        assert name.encode()+b'\0' in fw
    io,ret=read(work/'io.json'),read(work/'return/result.json')
    assert io['firmware_sha256']==ret['firmware_sha256']==digest(fw)
    assert io['state_bytes']==21264 and ret['passed'] and ret['safe_return'] and ret['base_restored']
    assert read(work/'slots.json')['distinct_slots_reloaded']==4
    packed,pgm=programmer(work/'route',work,1050)
    files.update({'nes-chrram.bi3':packed,'firmware.stm':fw})
    report={'edition':1050,'hardware_tested':False,'flash_bytes':len(fw),'client_test':cpu,
            'preserved_route':timing(work.parent/'nes-ff3-1048/lite-io'),
            'rbf_sha256':pgm['rbf_sha256'],'files':{k:digest(v) for k,v in files.items()}}
    name='FF3-1050-NES-PLAY-SD-ROOT.zip'
    temp=work/(name+'.tmp')
    with zipfile.ZipFile(temp,'w',compression=zipfile.ZIP_DEFLATED) as z:
        for k,v in files.items():z.writestr('sd2snes/'+k,v)
        z.writestr('README-KO.txt',(root/'docs/nes-ff3-1050.ko.md').read_bytes())
        z.writestr('manifest.json',json.dumps(report,indent=2))
    with zipfile.ZipFile(temp) as z:
        assert z.testzip() is None and all(z.read('sd2snes/'+k)==v for k,v in files.items())
    temp.replace(work/name)
    report['ZIP_SHA256']=digest((work/name).read_bytes())
    (root/'analysis/ff3-1050.json').write_text(json.dumps(report,indent=2)+'\n')
    print(name,report['ZIP_SHA256'])

if __name__=='__main__':package()
