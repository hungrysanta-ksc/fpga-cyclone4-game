# SPDX-License-Identifier: MIT
"""Release only a fully paired178 mask path after ARM/fit/IO/packet gates."""
from pathlib import Path
import argparse,json,zipfile,hashlib,re
from nes_game147 import ROOT,sha
from nes_cf68_pair_preflight import encode,decode
from nes_spi_boot import run

def main():
    p=argparse.ArgumentParser()
    for n in ['prior','arm','arm-check','fit','fit-check','report','quartus-bin','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();load=lambda p:json.loads(p.read_bytes());assert not a.out.exists()
    ar=load(a.arm_check/'result.json');f=load(a.fit_check);rp=load(a.report/'result.json')
    assert ar['passed'] and ar['remaining_margin']>=1024 and rp['passed']
    assert f['passed'] and f['nominal']['passed'] and f['io']['conditional_data_bounds_pass'] and f['io']['native_payload_reset_pass']
    assert f['snes_mif_4096_equal'] and f['packets']['passed'] and f['display']['passed']
    for result in [ar,f]:
        for n,h in result['public_sources'].items():assert sha(ROOT/n)==h,n
    assert rp['source_sha256']==sha(a.arm/'src/nes_menu_diagnostic.c') and 'bytes=3925 capacity=4096' in rp['output']
    prep=load(a.arm/'preparation-clip178.json');pins=prep['copied']|prep['changed']|prep['added']
    for n,h in pins.items():assert sha(a.arm/n)==h,n
    permitted={'src/nes_native_video165.c','src/nes_native_video165.h','src/nes_native_sink165.c','src/nes_menu_diagnostic.c','src/nes_checkpoint112.c','src/VERSION'}
    assert set(prep['changed'])==permitted and not prep['added']
    assert prep['seal_bytes']==20 and prep['accepted_masks']==[24,30] and prep['paired_snes_required']
    fpins=load(a.fit/'preparation.json')['sources'];assert fpins==f['sources']
    for n,h in fpins.items():assert sha(a.fit/n)==h,n
    for label,args in [('asm178',['quartus_asm.exe','board']),('cpf178',['quartus_cpf.exe','-c','output_files/board.sof','output_files/board.rbf'])]:
        log=run([a.quartus_bin/args[0],*args[1:]],a.fit,label,300);assert 'successful' in log and '0 errors' in log,log[-2000:]
    for n,h in fpins.items():assert sha(a.fit/n)==h,n
    raw=(a.fit/'output_files/board.rbf').read_bytes();packed=encode(raw);assert decode(packed)==raw
    (a.fit/'fpga_n178.bi3').write_bytes(packed)
    assert sha(a.prior)=='a2c68142f905fb3fc486b746d44ca94000830ab4897c3d5297160b9dcf440902'
    digest=lambda b:hashlib.sha256(b).hexdigest();blobs={};preserved={}
    with zipfile.ZipFile(a.prior) as z:
        for n,item in json.loads(z.read('manifest.json'))['files'].items():
            b=z.read(n);assert len(b)==item['bytes'] and digest(b)==item['sha256']
            if n.startswith(('01-GAME177-SD-ROOT/','02-RESTORE164-SD-ROOT/')):
                dst=n.replace('177','178') if n.startswith('01-') else n;blobs[dst]=b
                if dst not in ['01-GAME178-SD-ROOT/sd2snes/firmware.stm','01-GAME178-SD-ROOT/sd2snes/fpga_n178.bi3']:preserved[dst]=digest(b)
    fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==ar['firmware_sha256']
    assert b'NES GAME 178.nh1' in fw.read_bytes() and b'/sd2snes/fpga_n178.bi3' in fw.read_bytes()
    blobs['01-GAME178-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes();blobs['01-GAME178-SD-ROOT/sd2snes/fpga_n178.bi3']=packed
    assert '01-GAME178-SD-ROOT/NES GAME 178.nh1' in blobs and '01-GAME178-SD-ROOT/sd2snes/nes/game178.nes' in blobs
    blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game178-ready.ko.md').read_bytes()
    decision=dict(trial_ready=True,physical=False,video_fix_proven=False,fps60_proven=False,run_ticks_after_ready=6000,run_sd_writes=False,save_sram_used=False,remaining_margin=ar['remaining_margin'],nominal_setup_ns=float(f['nominal']['worst_setup']['slack']),full_io_signoff=False,history_wire_version=1,history_kind='LAST16_BOUNDARY177_LOW22',seal_bytes=20,uniform_masks=[24,30],other_ppu_modes_supported=False)
    blobs['decision178.json']=(json.dumps(decision,indent=2)+'\n').encode()
    manifest={'package':'NES178-SMB3-CLIP','files':{n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()}}
    blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode();a.out.mkdir(parents=True)
    archive=a.out/'NES178-SMB3-CLIP.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in blobs.items():
            info=zipfile.ZipInfo(n,(2026,10,14,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(blobs)
        for n,b in blobs.items():assert z.read(n)==b,n
    for n,h in preserved.items():assert digest(blobs[n])==h,n
    for n in ['START-HERE.ko.md','manifest.json','decision178.json']:(a.out/n).write_bytes(blobs[n])
    result=dict(passed=True,zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,firmware_sha256=sha(fw),fpga_sha256=digest(packed),rbf_sha256=digest(raw),snes_mif_matches_4096_bytes=True,snes_program_sha256=sha(a.fit/'sink-program.hex'),preserved=preserved,decision=decision,gates=dict(fit_check_sha256=sha(a.fit_check),arm_check_sha256=sha(a.arm_check/'result.json'),report_sha256=sha(a.report/'result.json')),public_sources={n:sha(ROOT/n) for n in ['tools/release_nes_clip178.py','docs/nes-game178-ready.ko.md','tools/nes_cf68_pair_preflight.py','tools/test_nes_startup170_report.py','tools/test_nes_sink168_report.py']})
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS178 PACKAGE',result['zip_sha256'])
if __name__=='__main__':main()
