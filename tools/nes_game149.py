# SPDX-License-Identifier: MIT
"""Materialize a non-installable game MCU candidate from frozen146.

No new FPGA protocol. Game video/top integration is deliberately a later step.
The target ROM is read locally for identification; no ROM bytes are published.
"""
from pathlib import Path
import argparse, difflib, hashlib, json, shutil, zlib
from nes_game147 import ROOT, ROM_SHA, sha

def prepare(baseline, rom, out):
    assert not out.exists()
    image=rom.read_bytes()
    assert sha(rom)==ROM_SHA and len(image)==0x60010
    e=baseline/'nes-display146/evidence'
    assert sha(e/'manifest.json')==json.loads((ROOT/'analysis/screen146-verification.json').read_bytes())['manifest_sha256']
    pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
    for n,h in pins.items():
        if not n.startswith('arm/'):continue
        rel=n[4:];p=Path(rel)
        if any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']:continue
        assert sha(e/n)==h,n
        d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
    patches=[]
    def edit(n,changes):
        p=out/'src'/n;old=new=p.read_text(encoding='utf8')
        for before,after,count in changes:
            assert new.count(before)==count,(n,before,new.count(before),count)
            new=new.replace(before,after)
        p.write_text(new,encoding='utf8',newline='\n')
        patches.extend(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='146/'+n,tofile='149/'+n))
    p=out/'src/nes_rom_spi.c';s=p.read_text();start=s.index('bool nes_rom_spi_transfer(');end=s.index('bool nes_rom_spi_query(',start)
    edit('nes_rom_spi.c',[(s[start:end],'''extern bool nes_game149_transfer(const struct nes_rom_spi_io *,const uint8_t [8],uint8_t [8]);
bool nes_rom_spi_transfer(const struct nes_rom_spi_io *io,const uint8_t tx[8],uint8_t rx[8]) {
 return nes_game149_transfer(io,tx,rx);
}
''',1)])
    # Only the menu game path is widened. Historical unreachable load-only APIs
    # remain strict; don't make unrelated legacy callers accept new identities.
    edit('nes_h1_stm32.c',[
        ('static bool sd_query(', '#include "nes_game149_spi.inc"\n\nstatic bool sd_query(',1),
        ('rx[1]!=0x5e||(rx[4]&0xfe)','rx[1]!=0x5f||(rx[4]&0xf8)',1),
        ('return s->count<=0x18000;','return s->count<=0x60000;',1),
        ('/* Exact synthetic RUN136 geometry, no trainer/battery/NES2,\n  * no extra flags or trailing data. CRC32 identifies the two original public\n  * fixtures against accidental changes; it is not a security signature. */',
         '/* Exact target SMB3(J) header/length/CRC; CRC detects accidental changes, not authenticity. */',1),
        ('/* Exact target SMB3(J) header/length/CRC; CRC detects accidental changes, not authenticity. */\n if(memcmp(header,"NES\\032",4) || header[4]!=4 ||\n    (header[5]!=2 && header[5]!=4) || header[6]!=0x40 || header[7]!=0)',
         '/* Exact target SMB3(J) header/length/CRC; CRC detects accidental changes, not authenticity. */\n if(memcmp(header,"NES\\032",4) || header[4]!=16 || header[5]!=16 ||\n    header[6]!=0x%02x || header[7]!=0x%02x)'%(image[6],image[7]),1),
        ('r->chr_32k=header[5]==4;\n if(r->chr_32k||expected_chr32){r->result=NES_MCU_LOAD_HEADER;goto cleanup;}\n total=65536u+(r->chr_32k?32768u:16384u);\n expected_crc=0xe2534ecdu;',
         'r->chr_32k=false;\n if(expected_chr32){r->result=NES_MCU_LOAD_HEADER;goto cleanup;}\n total=0x60000u;\n expected_crc=0x%08xu;'%zlib.crc32(image),1),
        ('sd_command(&io,NES_ROM_BEGIN,0,r->chr_32k,&status)', 'sd_command(&io,NES_ROM_BEGIN,0,2,&status)',1)])
    assert not any(image[8:16]), 'Target header reserved bytes changed'
    edit('nes_rom_verify.c', [('0x5e','0x5f',2),('(length!=0x14000&&length!=0x18000)','length!=0x60000',1),('(length==0x14000||length==0x18000)','(length==0x60000)',1)])
    edit('nes_run136.inc',[('candidate->board_id=0x5e','candidate->board_id=0x5f',1)])
    edit('nes_menu_diagnostic.c',[
        ('"NES SCREEN 146.nh1")?80:0','"NES GAME 149.nh1")?384:0',1),
        ('NES-SCREEN-146','NES-GAME-149',1),('board_expected_hex=5e','board_expected_hex=5f',1),
        ('nes-screen-last-146.txt','nes-game-last-149.txt',1),
        ('printf("NES146 load/verify/bounded RUN: %uKiB; RESET held; no pad cancel; wire delays >=%us plus SD/configuration.\\n",\n  geometry,geometry==80?113:136);',
         'printf("NES149 %uKiB; SPI1 mode0 PCLK2/32; duration not yet measured on hardware.\\n",geometry);',1),
        ('geometry==80?"/sd2snes/nes/screen146.nes":"/sd2snes/nes/banks32.nes"','"/sd2snes/nes/game149.nes"',1),
        ('"/sd2snes/fpga_n146.bi3",geometry==96','"/sd2snes/fpga_n149.bi3",false',1)])
    edit('nes_checkpoint112.c',[('NES146','NES149',1),('nes-progress-146.txt','nes-progress-149.txt',1)])
    edit('VERSION',[('NES-SCREEN146','NES-GAME149-DEV',1)])
    source=ROOT/'src/nes/firmware/nes_game149_spi.inc'
    shutil.copy2(source,out/'src'/source.name)
    (out/'changes149.diff').write_text(''.join(patches),encoding='utf8',newline='\n')
    result=dict(candidate='NES-GAME-149',installable=False,rom_sha256=ROM_SHA,rom_crc32=f'{zlib.crc32(image):08x}',
        payload_bytes=0x60000,spi_hz=2625000,begin_argument=2,board_id=0x5f,
        copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h},
        added={'src/'+source.name:sha(source)},remaining=['game top','game video','pad','fit','hardware'])
    (out/'preparation149.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8',newline='\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['baseline','rom','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.baseline,a.rom,a.out)
