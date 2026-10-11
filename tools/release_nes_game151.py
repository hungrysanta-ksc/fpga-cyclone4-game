# SPDX-License-Identifier: MIT
"""Private, hash-checked actual-game trial. ROM bytes never belong in Git."""
from pathlib import Path
import argparse,hashlib,json,zipfile
from nes_game147 import ROOT,ROM_SHA,sha
from nes_cf68_pair_preflight import decode
from nes_game151 import MODULES

def main():
    p=argparse.ArgumentParser()
    for n in ['baseline','arm','arm-check','asm','video','client','rom-test','rom','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();assert not a.out.exists();assert sha(a.rom)==ROM_SHA
    arm=json.loads((a.arm_check/'result.json').read_bytes());asm=json.loads((a.asm/'result.json').read_bytes())
    video=json.loads((a.video/'result.json').read_bytes());client=json.loads((a.client/'result.json').read_bytes())
    timing=json.loads((a.asm/'timing150-phase.json').read_bytes())
    assert arm['strong_nmi'] and arm['transport_source_matches'] and video['passed'] and client['passed'] and timing['passed']
    assert 'PASS GAME150 ROM32768' in video['results']['rom']
    for n in MODULES:assert sha(a.asm/n)==sha(a.video/n)==sha(ROOT/'src/nes/diagnostic'/n),n
    assert sha(a.asm/'nes_game_bus151.sv')==sha(a.rom_test/'nes_game_bus151.sv')
    assert sha(a.asm/'game-program.hex')==sha(a.client/'client/game-program.hex')==sha(a.rom_test/'game-program.hex')
    fw=a.arm/'src/obj-nes-100/firmware.stm';fpga=a.asm/'fpga_n151.bi3'
    assert sha(fw)==arm['firmware_sha256'] and sha(fpga)==asm['packed_sha256']
    assert decode(fpga.read_bytes())==(a.asm/'output_files/board.rbf').read_bytes()
    old=a.baseline/'nes-run136/evidence/release01/NES136-MINIMUM-RUN-and-RESTORE044.zip'
    assert sha(old)==json.loads((ROOT/'analysis/run136-verification.json').read_bytes())['package']['zip_sha256']
    digest=lambda b:hashlib.sha256(b).hexdigest();blobs={}
    with zipfile.ZipFile(old) as z:
        manifest=json.loads(z.read('manifest.json'))
        for n in ['01-RUN136-SD-ROOT/sd2snes/fpga_base.bi3','01-RUN136-SD-ROOT/sd2snes/m3nu.bin',
                  '02-RESTORE044-SD-ROOT/sd2snes/firmware.stm','02-RESTORE044-SD-ROOT/sd2snes/fpga_base.bi3','02-RESTORE044-SD-ROOT/sd2snes/m3nu.bin']:
            b=z.read(n);assert digest(b)==manifest['files'][n]['sha256'];blobs[n.replace('01-RUN136','01-GAME151')]=b
    blobs.update({'01-GAME151-SD-ROOT/sd2snes/firmware.stm':fw.read_bytes(),
      '01-GAME151-SD-ROOT/sd2snes/fpga_n151.bi3':fpga.read_bytes(),
      '01-GAME151-SD-ROOT/sd2snes/nes/game151.nes':a.rom.read_bytes(),'01-GAME151-SD-ROOT/NES GAME 151.nh1':b'',
      'START-HERE.ko.md':(ROOT/'docs/nes-game151-instructions.ko.md').read_bytes()})
    decision=dict(candidate='NES-GAME-151',board='61',observer='DB',target_rom_sha256=ROM_SHA,
      normal_trial_ready=True,physical=False,display_seconds=60,loading_seconds_measured=None,
      video='Final6-bit PPU index, single frozen256x224 snapshot, forced-blank full DMA',
      visible_hold_vblanks=30,full_speed=False,input=True,audio=False,emphasis=False,save_persistence=False,unchanged044_retest=False,
      timing=timing,screen_telemetry_trusted=False)
    blobs['decision151.json']=(json.dumps(decision,indent=2)+'\n').encode()
    manifest=dict(package='NES151-SMB3-WRITE-END',files={n:dict(bytes=len(b),sha256=digest(b)) for n,b in blobs.items()})
    blobs['manifest.json']=(json.dumps(manifest,indent=2)+'\n').encode()
    a.out.mkdir(parents=True);archive=a.out/'NES151-SMB3-WRITE-END.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for n,b in blobs.items():
            info=zipfile.ZipInfo(n,(2026,10,11,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;z.writestr(info,b)
    with zipfile.ZipFile(archive) as z:
        assert set(z.namelist())==set(blobs)
        for n,b in blobs.items():assert z.read(n)==b,n
    for n in ['START-HERE.ko.md','decision151.json','manifest.json']:(a.out/n).write_bytes(blobs[n])
    result=dict(zip_sha256=sha(archive),zip_bytes=archive.stat().st_size,members=len(blobs),
      firmware_sha256=sha(fw),fpga_sha256=sha(fpga),rom_sha256=ROM_SHA,normal_trial_ready=True,physical=False)
    (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
