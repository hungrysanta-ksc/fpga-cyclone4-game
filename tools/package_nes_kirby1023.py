"""Gate and package the Kirby timing baseline, retaining verified menu, base and GBC assets."""
import argparse
import json
import re
import struct
import zlib
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from check_nes_kirby1023_release import WORK, PROOF, SRC
from cross_nes1022 import GAMES, rom_path
from package_nes_trial704 import ROOT, digest, read, save
from verify_nes_kirby1023_arm import compare_rtl

def package(build,image,capture):
    board=WORK/'board'
    for f in board.rglob('*'):
        if f.is_file() and f.suffix in ('.sv','.v','.vhd','.sdc','.qsf','.qip','.hex','.mif','.tcl'):
            assert f.read_bytes()==(build/f.relative_to(board)).read_bytes(),f
    fit=(build/'output_files/board.fit.summary').read_text()
    sta=(build/'output_files/board.sta.summary').read_text()
    slack=[float(v) for v in re.findall(r'^Slack : ([-.\d]+)',sta,re.M)]
    assert 'Fitter Status : Successful' in fit and '15,309 / 15,408' in fit
    assert slack and min(slack)>=0 and all(float(v)==0 for v in re.findall(r'^TNS +: ([-.\d]+)',sta,re.M))
    io={}
    for line in (build/'kirby1023-io.tsv').read_text().splitlines():
        corner,group,ns=line.split()
        io.setdefault(corner,{})[group]=float(ns)
    assert len(io)==3 and all(set(v)=={'address','upper','active','capture'} for v in io.values())
    for v in io.values():
        for group,edges in [('upper',17),('address',17),('active',16)]:
            v[group+'_margin_ns']=round(edges*5.952-70-4-v[group]-v['capture'],3)
            assert v[group+'_margin_ns']>0
    b=(image/'fpga_mmc1023.bi3').read_bytes()
    programmer=read(image/'image.json')
    assert programmer['programmer']['passed'] and programmer['BI3']==digest(b)
    assert programmer['SOF']==digest((build/'output_files/board.sof').read_bytes())
    fw=(SRC/'obj-nes-100/firmware.stm').read_bytes()
    hash_fw=digest(fw)
    size,crc,inverse=struct.unpack_from('<III',fw,8)
    assert fw[:4]==b'STM3' and size+512==len(fw)<=212992 and zlib.crc32(fw[512:])==crc==inverse^0xffffffff
    for name in (' 1023.nh1','mmc1023.nes','fpga_mmc1023.bi3','nes-frame-mmc1023.bin',*(f'nes-{k}-mmc1023.txt' for k in ('budget','game-last','progress'))):
        assert name.encode()+b'\0' in fw,name
    checks={k:read(PROOF/(k+'.json')) for k in ('menu','timer','windows','base-result','sram','loader','trace')}
    assert checks['menu']['firmware']==checks['timer']['firmware']==checks['windows']['firmware_SHA256']==checks['base-result']['firmware_sha256']==hash_fw
    assert checks['menu']['rows']['normal']['released'] and checks['base-result']['safe_return'] and checks['timer']['passed']
    assert checks['sram']['cases']['normal']['checked_retire'] and checks['sram']['cases']['normal']['static_gap_bytes']>0
    assert checks['loader']['kirby']['program'] and checks['loader']['bad-last']['error']==4
    rom=rom_path(Path.home()/'Downloads/test','kirby')
    assert digest(rom.read_bytes())==GAMES['kirby']
    compare_rtl(WORK/'arm',capture,rom)
    pixels=read(WORK/'arm/rtl-pixels.json')
    plans=read(WORK/'arm/pixels.json')
    expected=sum(r['plans'] for r in plans)
    match=re.search(r'PASS1023 tiles=(\d+) upper_reads=(\d+) wrong_bank_rejected STOP',(WORK/'tile-run.log').read_text())
    assert match and int(match[1])==expected and int(match[2])>0
    reference=read(ROOT/'analysis/trial1012-package.json')
    source=WORK.parent/'nes-tail1012-final/MMC1012-ADVENTURE-60SEC-SD-ROOT.zip'
    assert digest(source.read_bytes())==reference['ZIP_SHA256']
    files={}
    with ZipFile(source) as old:
        for name,sha in reference['files'].items():
            data=old.read(name)
            assert digest(data)==sha
            if name=='README-KO.txt':
                data=(ROOT/'docs/nes-mmc1023-trial.ko.md').read_text(encoding='utf-8').encode('utf-8')
            elif name.endswith('/firmware.stm'):
                data=fw
            elif name.endswith('/fpga_mmc1012.bi3'):
                data=b
            elif name.endswith('/ROM-NOT-INCLUDED.txt'):
                data=('Place your matching Japanese Kirby ROM here as mmc1023.nes.\nSHA-256 '+GAMES['kirby']+'\n').encode()
            files[name.replace('1012','1023').replace('ADVENTURE','KIRBY')]=data
    assert len(files)==len(reference['files']) and not any(n.lower().endswith('.nes') or 'restore' in n.lower() for n in files)
    report=dict(edition=1023,physical=False,baseline=1012,policy=0,remember=0,client=reference['client'],
                flash_B=len(fw),flash_free_B=212992-len(fw),firmware=hash_fw,board_BI3=digest(b),SOF=programmer['SOF'],
                LE=15309,LAB=963,M9K=53,min_slack_ns=min(slack),STA_checks=len(slack),routed_PSRAM_70ns=io,source_ROM=GAMES['kirby'],
                frame_comparison=pixels,plans=expected,high_plans=sum(row['upper'] for row in plans),
                high_reads=int(match[2]),irq_stack_test_gap_B=checks['sram']['cases']['normal']['static_gap_bytes'],
                receiver='actual SPI D1 with CRC; original PPU traces; linked ARM; FPGA plan and tile outputs',
                guard_trace='First-frame ACK, CRC error, delayed input and IRQ stack use the translated lower-bank control fixture. Menu peripherals are modeled.',
                original_archive=reference['ZIP_SHA256'],files={n:digest(data) for n,data in files.items()})
    files['manifest.json']=(json.dumps(report,indent=2)+'\n').encode()
    out=WORK/'MMC1023-KIRBY-60SEC-SD-ROOT.zip'
    partial=out.with_suffix('.partial')
    with ZipFile(partial,'w') as z:
        for n,data in files.items():
            z.writestr(ZipInfo(n),data,compress_type=ZIP_DEFLATED)
    with ZipFile(partial) as z:
        assert z.testzip() is None and z.namelist()==list(files) and all(z.read(n)==data for n,data in files.items())
    partial.replace(out)
    report.update(ZIP_SHA256=digest(out.read_bytes()),ZIP_B=out.stat().st_size)
    save(ROOT/'analysis/trial1023-package.json',report)
    print(out,report['ZIP_SHA256'])

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for arg in ('build','image','capture'):
        p.add_argument(arg,type=Path)
    a=p.parse_args()
    package(a.build,a.image,a.capture)
