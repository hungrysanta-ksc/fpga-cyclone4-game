# SPDX-License-Identifier: MIT
"""Package checked226 ARM with byte-identical225 FPGA/game/restoration assets."""
from pathlib import Path
import argparse,json,hashlib,zipfile
from nes_fast226 import ROOT,BASE,sha

def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    d=BASE/'probes/nes-fast226';arm=d/'arm01';e=read(d/'analysis.json');c=read(d/'check02/result.json')
    assert e['passed'] and e['trial_gates_pass'] and c['passed'] and c['remaining_margin']==1792
    for n,h in e['gates'].items():assert sha(d/n)==h,n
    for n,h in e['public_sources'].items():assert sha(ROOT/n)==h,n
    prep=read(arm/'preparation-fast226.json')
    for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
    fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==c['firmware_sha256']
    assert sha(arm/'src/obj-nes-100/sd2snes.elf')==c['elf_sha256']
    for m in [b'NES GAME 226.nh1',b'game226.nes',b'fpga_n226.bi3',b'nes-progress-226.txt',b'nes-game-last-226.txt',b'nes-budget-226.txt',b'budget_schema=226']:assert m in fw,m
    old=BASE/'probes/nes-scroll225/release01';oldr=read(old/'result.json');oldz=old/'NES225-SMB3-SCROLLMAP.zip';assert sha(oldz)==oldr['zip_sha256']
    blobs={};preserved={}
    with zipfile.ZipFile(oldz) as z:
        for n,item in read(old/'manifest.json')['files'].items():
            b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
            if n.startswith(('01-GAME225-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
                dst=n.replace('225','226') if n.startswith('01-') else n;blobs[dst]=b
                if dst!='01-GAME226-SD-ROOT/sd2snes/firmware.stm':preserved[dst]=digest(b)
    blobs['01-GAME226-SD-ROOT/sd2snes/firmware.stm']=fw
    fpga=blobs['01-GAME226-SD-ROOT/sd2snes/fpga_n226.bi3'];assert digest(fpga)==oldr['fpga_sha256']==e['baseline']['fpga_sha256']
    assert len(blobs['01-GAME226-SD-ROOT/sd2snes/nes/game226.nes'])>393216
    decision=dict(trial_ready=True,physical=False,fps60=False,new_fit=False,new_asm=False,
        fpga_byte_identical225=True,arm_identity=226,wire_version='2231',snes_version='2121',
        budget_schema=226,run_ticks=6000,remaining_margin=1792,save_sram_unchanged=True,gbc164_unchanged=True)
    blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game226-ready.ko.md').read_bytes()
    blobs['decision226.json']=(json.dumps(decision,indent=2)+'\n').encode()
    manifest=dict(package='NES226-SMB3-PLANNERFAST',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
    blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
    zout=a.out/'NES226-SMB3-PLANNERFAST.zip'
    with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in blobs.items():
            i=zipfile.ZipInfo(n,(2026,10,18,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
    with zipfile.ZipFile(zout) as z:
        assert set(z.namelist())==set(blobs)
        for n,b in blobs.items():assert z.read(n)==b,n
    for n,h in preserved.items():assert digest(blobs[n])==h,n
    result=dict(passed=True,decision=decision,zip_sha256=sha(zout),firmware_sha256=digest(fw),fpga_sha256=digest(fpga),
        preserved=preserved,baseline_zip_sha256=sha(oldz),evidence_sha256=sha(d/'analysis.json'),arm=e['arm'],
        public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_fast226.py','docs/nes-game226-ready.ko.md']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');(a.out/'manifest.json').write_bytes(blobs['manifest.json'])
    (ROOT/'analysis/release226-verification.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
    print(json.dumps(dict(passed=True,zip_sha256=result['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
