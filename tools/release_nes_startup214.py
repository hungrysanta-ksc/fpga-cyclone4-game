# SPDX-License-Identifier: MIT
"""Package214 startup evidence only; unchanged213 FPGA and renderer."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_runtime213 import ROOT,BASE,sha
def read(p):return json.loads(p.read_bytes())
def digest(b):return hashlib.sha256(b).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();assert not a.out.exists()
    d=BASE/'probes/nes-startup214';arm=d/'arm02';prep=read(arm/'preparation-startup214.json')
    for n,h in (prep['copied']|prep['changed']|prep['added']).items():assert sha(arm/n)==h,n
    for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
    check=read(d/'check02/result.json');gate=read(d/'gate01/result.json');bus=read(d/'bus01/result.json')
    assert check['passed'] and gate['passed'] and bus['passed']
    assert check['remaining_margin']==4992 and gate['cases']==11 and 'format_max=2571' in gate['output']
    assert bus['root_cause_reproduced'] is False
    for n,h in check['public_sources'].items():assert sha(ROOT/n)==h,n
    assert gate['source_sha256']==sha(ROOT/'tools/test_nes_startup214_gate.py')
    for n,h in gate['source_pins'].items():assert sha(arm/'src'/n)==h,n
    assert bus['source_sha256']==sha(ROOT/'tools/test_nes_startup214.py')
    for n,h in bus['source_pins'].items():assert sha(BASE/'probes/nes-board207/mapfit02'/n)==h,n
    assert bus['cases'][1]['client_sha256']==sha(BASE/'probes/nes-runtime213/asm01/sink-program.hex')
    old=BASE/'probes/nes-runtime213/release01';oldr=read(old/'result.json');oldz=old/'NES213-SMB3-RESIDENT-DIRTY.zip'
    assert sha(oldz)==oldr['zip_sha256']
    blobs={};preserved={}
    with zipfile.ZipFile(oldz) as z:
        for n,item in read(old/'manifest.json')['files'].items():
            b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
            if n.startswith(('01-GAME213-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
                dst=n.replace('213','214') if n.startswith('01-') else n
                blobs[dst]=b
                if dst!='01-GAME214-SD-ROOT/sd2snes/firmware.stm':preserved[dst]=digest(b)
    fw=(arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256']
    assert sha(arm/'src/obj-nes-100/sd2snes.elf')==check['elf_sha256']
    for marker in [b'NES GAME 214.nh1',b'game214.nes',b'fpga_n214.bi3',b'nes-progress-214.txt',b'nes-game-last-214.txt',b'nes-budget-214.txt',b'boot_reason=']:assert marker in fw,marker
    blobs['01-GAME214-SD-ROOT/sd2snes/firmware.stm']=fw
    fpga=digest(blobs['01-GAME214-SD-ROOT/sd2snes/fpga_n214.bi3']);assert fpga==oldr['fpga_sha256']
    decision=dict(trial_ready=True,root_cause_fixed=False,physical=False,new_fit=False,new_asm=False,unchanged213_fpga=True,unchanged213_renderer=True,boot_limit_ticks=500,remaining_margin=4992,added_static_bytes=24,budget_max=2571,run_ticks=6000)
    blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game214-ready.ko.md').read_bytes()
    blobs['decision214.json']=(json.dumps(decision,indent=2)+'\n').encode()
    manifest=dict(package='NES214-SMB3-BOOT-CAUSE',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
    blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
    zout=a.out/'NES214-SMB3-BOOT-CAUSE.zip'
    with zipfile.ZipFile(zout,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in blobs.items():
            i=zipfile.ZipInfo(n,(2026,10,17,0,0,0));i.compress_type=zipfile.ZIP_DEFLATED;i.external_attr=0o100644<<16;z.writestr(i,b)
    with zipfile.ZipFile(zout) as z:
        assert set(z.namelist())==set(blobs)
        for n,b in blobs.items():assert z.read(n)==b,n
    for n,h in preserved.items():assert digest(blobs[n])==h,n
    public=['tools/nes_startup214.py','tools/test_nes_startup214.py','tools/test_nes_startup214_gate.py','tools/check_nes_startup214_arm.py','tools/release_nes_startup214.py','src/nes/firmware/nes_boot214.h','src/nes/firmware/nes_boot214.inc','docs/nes-game214-ready.ko.md','docs/nes-startup214-contract.ko.md']
    r=dict(passed=True,decision=decision,firmware_sha256=digest(fw),fpga_sha256=fpga,zip_sha256=sha(zout),preserved=preserved,prior213_zip_sha256=sha(oldz),gates={n:sha(d/n/'result.json') for n in ['check02','gate01','bus01']},public_sources={n:sha(ROOT/n) for n in public},bus=bus['cases'],arm={k:check[k] for k in ['firmware_bytes','ram_static','foreground_bound','irq_reserve','remaining_margin']})
    (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n');(a.out/'manifest.json').write_bytes(blobs['manifest.json'])
    (ROOT/'analysis/startup214-verification.json').write_text(json.dumps(r,indent=2)+'\n')
    print(json.dumps(dict(passed=True,zip_sha256=r['zip_sha256'],decision=decision)))
if __name__=='__main__':main()
