# SPDX-License-Identifier: MIT
"""New MCU with byte-identical152 FPGA/ROM/base/restore; no FPGA rebuild."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','arm','arm-check','host','context','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists()
    e=a.baseline/'nes-game152/evidence';meta=json.loads((ROOT/'analysis/game152-verification.json').read_bytes())
    assert sha(e/'manifest.json')==meta['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files']
    # Validate the existing selected FPGA and timing evidence, without reruns.
    for n in ['asm/fpga_n152.bi3','asm/result.json','asm/timing150-phase.json','release/NES152-SMB3-INPUT-CONTEXT.zip']:
        assert sha(e/n)==pins[n],n
    assert json.loads((e/'asm/timing150-phase.json').read_bytes())['passed']
    old=e/'release/NES152-SMB3-INPUT-CONTEXT.zip';assert sha(old)==meta['package']['zip_sha256']
    arm=json.loads((a.arm_check/'result.json').read_bytes());host=json.loads((a.host/'result.json').read_bytes());ctx=json.loads((a.context/'result.json').read_bytes())
    assert arm['strong_nmi'] and arm['transport_source_matches'] and host['passed'] and ctx['passed']
    assert host['actual_sources']['nes_run136.inc']==ctx['source_sha256']==sha(a.arm/'src/nes_run136.inc')
    for n,h in host['actual_sources'].items():assert sha(a.arm/'src'/n)==h,n
    fw=a.arm/'src/obj-nes-100/firmware.stm';assert sha(fw)==arm['firmware_sha256']
    blobs={};digest=lambda b:hashlib.sha256(b).hexdigest()
    with zipfile.ZipFile(old) as z:
        m=json.loads(z.read('manifest.json'))
        for n,item in m['files'].items():
            data=z.read(n);assert digest(data)==item['sha256'] and len(data)==item['bytes'],n
            if n.startswith(('01-GAME152-SD-ROOT/','02-RESTORE044-SD-ROOT/')):
                blobs[n.replace('152','153')]=data
    fpga=blobs['01-GAME153-SD-ROOT/sd2snes/fpga_n153.bi3']
    assert digest(fpga)==sha(e/'asm/fpga_n152.bi3')
    assert digest(blobs['01-GAME153-SD-ROOT/sd2snes/nes/game153.nes'])==ROM_SHA
    assert blobs['01-GAME153-SD-ROOT/NES GAME 153.nh1']==b''
    blobs['01-GAME153-SD-ROOT/sd2snes/firmware.stm']=fw.read_bytes()
    blobs['START-HERE.ko.md']=(ROOT/'docs/nes-game153-instructions.ko.md').read_bytes()
    decision=dict(candidate='NES-GAME-153',ids=['62','DC'],fpga_identical152=True,physical=False,
      tagged_fault_recovery_model_passed=True,ppu_deadline_fixed=False,screen_telemetry_trusted=False,
      display_seconds_max=60,visible_hold_vblanks=30,audio=False,save_persistence=False,full_speed=False,
      prior152_manifest_sha256=meta['manifest_sha256'],fpga_sha256=digest(fpga),rom_sha256=ROM_SHA,
      changed='Accept PPU address tag bit63; other context reply guards retained; new153 filenames only.',
      limitations=['Actual152 fault code/address unknown','SPI engine/GPIO/card/FPGA mocked in host test',
        'Physical PPU root cause unresolved','Input DMA/wait gaps and Start duplicate consumption unconfirmed',
        'Existing152 timing/IO/MTBF limits retained'])
    blobs['decision153.json']=(json.dumps(decision,indent=2)+'\n').encode()
    manifest=dict(package='NES153-SMB3-FAULT-RECOVERY',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
    blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    a.out.mkdir(parents=True);archive=a.out/'NES153-SMB3-FAULT-RECOVERY.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in blobs.items():
            info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(blobs)
        for n,b in blobs.items():assert z.read(n)==b,n
    for n in ['START-HERE.ko.md','decision153.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
    result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),firmware_sha256=sha(fw),
      fpga_sha256=digest(fpga),fpga_identical152=True,normal_trial_ready=True,physical=False,ppu_deadline_fixed=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))

if __name__=='__main__':main()
