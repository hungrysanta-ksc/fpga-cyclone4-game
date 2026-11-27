"""Package the verified debug and release sets; preserve SD saves and the GBC payloads."""
import csv
import hashlib
import json
import struct
import zipfile
import zlib
from prepare_nes_pair1054 import PROBES,ROOT,WORK
from package_nes_kirby1027 import timing,programmer

def digest(data):return hashlib.sha256(data).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf8'))

def package():
    prior=PROBES/'nes-ff3-movement1052'
    known=read(ROOT/'analysis/ff3-movement1052.json')['editions']['1053']
    original=prior/'FF3-1053-MOVEMENT-SD-ROOT.zip'
    assert digest(original.read_bytes())==known['zip_sha256']
    with zipfile.ZipFile(original) as z:
        common={name:z.read('sd2snes/'+name) for name in known['files']}
    assert {n:digest(d) for n,d in common.items()}==known['files']
    results={}
    for profile in ('debug','release'):
        files=common.copy()
        base=WORK/profile
        fw=(base/'link/src/obj-nes-100/firmware.stm').read_bytes()
        size,crc,inv=struct.unpack_from('<III',fw,8)
        assert fw[:4]==b'STM3' and len(fw)==size+512<=212992 and zlib.crc32(fw[512:])==crc==(inv^0xffffffff)
        files['firmware.stm']=fw
        assert read(base/'slots.json')['distinct_slots_reloaded']==4
        proof={}
        if profile=='debug':
            for name,ext in [('progress','txt'),('frame','bin'),('game-last','txt')]:
                assert f'nes-{name}-debug1054.{ext}\0'.encode() in fw
            ret=read(base/'return-final/result.json')
            assert ret['passed'] and ret['safe_return'] and ret['firmware_sha256']==digest(fw)
            proof['windows']=read(base/'windows.json')
        else:
            assert b'Loading NES\0' in fw and not any(n in fw for n in [b'/sd2snes/nes-frame-',b'/sd2snes/nes-progress-',b'/sd2snes/nes-game-last-'])
            proof['preload']=read(WORK/'preload.json')
            proof['return']=read(base/'return.json')
            for kind in ('ram','rom'):
                rpt=WORK/('fit-'+kind+'-retail')
                assert 'PASS1054' in (WORK/('sim-'+kind)/'result.log').read_text(errors='replace')
                proof[kind]=timing(rpt)
                if kind=='ram':
                    with (rpt/'sram.tsv').open() as f: rows=list(csv.DictReader(f,delimiter='\t'))
                    assert len({r['corner'] for r in rows})==3
                    for c in {r['corner'] for r in rows}:
                        assert {(r['group'],r['check']) for r in rows if r['corner']==c}=={(g,k) for g in ('input','output') for k in ('setup','hold')}
                work=base/kind;work.mkdir(exist_ok=True)
                packed,_=programmer(rpt,work,1054)
                files['nes-chr'+kind+'.bi3']=packed
        manifest=dict(edition=1054,profile=profile,firmware_bytes=len(fw),files={n:digest(d) for n,d in files.items()})
        name='NES-1054-'+profile.upper()+'-SD-ROOT.zip'
        target=WORK/name
        tmp=target.with_suffix('.tmp')
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            for n,d in files.items():z.writestr('sd2snes/'+n,d)
            z.writestr('README-KO.txt',(ROOT/'docs/nes-kirby-pair1054.ko.md').read_bytes())
            z.writestr('manifest.json',json.dumps(manifest,indent=2))
        with zipfile.ZipFile(tmp) as z:
            assert not z.testzip() and all(z.read('sd2snes/'+n)==d for n,d in files.items())
        tmp.replace(target)
        results[profile]=dict(manifest,proof=proof,zip=name,sha256=digest(target.read_bytes()))
    (WORK/'package.json').write_text(json.dumps(results,indent=2)+'\n')
    print([(k,v['firmware_bytes'],v['zip']) for k,v in results.items()])

if __name__=='__main__':package()
