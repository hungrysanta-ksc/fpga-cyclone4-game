# SPDX-License-Identifier: MIT
"""MCU-only182 package. Preserve exact181 FPGA, original ROM and164 restore."""
from pathlib import Path
import argparse,json,zipfile,hashlib
from nes_game147 import ROOT,sha
from nes_dma182 import bulk

def main():
    p=argparse.ArgumentParser()
    for n in ['prior','arm','check','test','report','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    load=lambda p:json.loads(p.read_bytes())
    digest=lambda b:hashlib.sha256(b).hexdigest()
    assert sha(a.prior)=='274489a0106c2a82457e8a157883f60e545f0691737ad1a1452139b0b9e27f71'
    prep=load(a.arm/'preparation-dma182.json');pins=prep['copied']|prep['changed']|prep['added']
    for n,h in pins.items():assert sha(a.arm/n)==h,n
    assert set(prep['changed'])=={'src/nes_native165_bulk.inc','src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION'}
    assert set(prep['added'])=={'src/nes_dma182.inc'}
    for n,h in prep['public_sources'].items():assert sha(ROOT/n)==h,n
    check=load(a.check/'result.json');test=load(a.test/'result.json');report=load(a.report/'result.json')
    assert check['passed'] and test['passed'] and report['passed'] and check['remaining_margin']>=1024
    for r in [check,test]:
        for n,h in r['public_sources'].items():assert sha(ROOT/n)==h,n
    assert sha(a.arm/'src/nes_native165_bulk.inc')==test['driver_sha256']
    assert sha(a.arm/'src/nes_menu_diagnostic.c')==report['source_sha256']
    fw=(a.arm/'src/obj-nes-100/firmware.stm').read_bytes();assert digest(fw)==check['firmware_sha256']
    assert (a.arm/'src/nes_dma182.inc').read_bytes()==(ROOT/'src/nes/firmware/nes_dma182.inc').read_bytes()
    baseline=ROOT.parent/'probes/nes-paired181/evidence/arm02/src/nes_native165_bulk.inc'
    assert (a.arm/'src/nes_native165_bulk.inc').read_text()==bulk(baseline.read_text())
    for m in [b'NES GAME 182.nh1',b'/sd2snes/fpga_n182.bi3',b'/sd2snes/nes/game182.nes',b'nes-progress-182.txt',b'nes-game-last-182.txt']:
        assert m in fw,m
    blobs={};preserved={}
    with zipfile.ZipFile(a.prior) as z:
        for n,item in load_zip(z,'manifest.json')['files'].items():
            b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256'],n
            if n.startswith(('01-GAME181-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
                dst=n.replace('181','182') if n.startswith('01-') else n
                blobs[dst]=b
                if not dst.endswith('/firmware.stm') or dst.startswith('02-'):preserved[dst]=digest(b)
    blobs['01-GAME182-SD-ROOT/sd2snes/firmware.stm']=fw
    assert digest(blobs['01-GAME182-SD-ROOT/sd2snes/fpga_n182.bi3'])=='6cb2235de30a12f8dbae084beb56c3d1f58efb14ed7039ef6a298b39504c5d50'
    assert digest(blobs['01-GAME182-SD-ROOT/sd2snes/nes/game182.nes'])=='dbb1cb5e18b091ca9101b1c2f5a5d6bdbeaa4a30ae1a504251310f6765cabb49'
    blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game182-ready.ko.md').read_bytes()
    decision=dict(trial_ready=True,physical=False,fps60_proven=False,firmware_only=True,fpga_unchanged=True,
                  spi_hz=2625000,spi_min_ss_high_ns=2000,max_dma_bytes=259,ingress_version='1813',sink_version='1815',
                  run_ticks_after_ready=6000,save_sram_used=False,run_sd_writes=False,remaining_margin=check['remaining_margin'])
    blobs['decision182.json']=(json.dumps(decision,indent=2)+'\n').encode()
    manifest=dict(package='NES182-SMB3-DMA-VIDEO',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
    blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
    archive=a.out/'NES182-SMB3-DMA-VIDEO.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in blobs.items():
            info=zipfile.ZipInfo(n,(2026,10,15,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED
            info.external_attr=0o100644<<16;z.writestr(info,b)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(blobs)
        for n,b in blobs.items():assert z.read(n)==b,n
    for n,h in preserved.items():assert digest(blobs[n])==h,n
    result=dict(passed=True,zip_sha256=sha(archive),firmware_sha256=digest(fw),firmware_bytes=len(fw),
                fpga_sha256=digest(blobs['01-GAME182-SD-ROOT/sd2snes/fpga_n182.bi3']),preserved=preserved,
                decision=decision,source_pins=len(pins),gates={k:sha(v/'result.json') for k,v in [('check',a.check),('test',a.test),('report',a.report)]},
                public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_dma182.py','docs/nes-game182-ready.ko.md']})
    for n,b in [('result.json',(json.dumps(result,indent=2)+'\n').encode()),('manifest.json',blobs['manifest.json']),('START-HERE.ko.md',blobs['START-HERE.ko.md'])]:(a.out/n).write_bytes(b)
    print(json.dumps({k:v for k,v in result.items() if k not in ['preserved','public_sources']}))

def load_zip(z,n):return json.loads(z.read(n))
if __name__=='__main__':main()
