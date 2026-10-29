# SPDX-License-Identifier: MIT
"""Materialize a fixed NROM16/horizontal 227 loader and FPGA identity.

Experimental sources only: no product package, physical deployment or FIT.
"""
import argparse
import json
import shutil
from pathlib import Path
from nes_delta231 import BASE, ROOT, sha


def once(s, old, new):
    assert s.count(old)==1, (old[:100],s.count(old))
    return s.replace(old,new)


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--out',required=True,type=Path)
    a=p.parse_args()
    d=a.out.resolve()
    d.mkdir(parents=True,exist_ok=False)
    arm=BASE/'probes/nes-repeat227/arm01/src'
    for n in ('nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc'):
        shutil.copyfile(arm/n,d/n)
    make=(arm/'Makefile').read_text()
    make=once(make,'SRC += nes_h1_session.c nes_h1_stm32.c nes_menu_diagnostic.c',
              'SRC += nes_nrom406.c nes_h1_session.c nes_h1_stm32.c nes_menu_diagnostic.c')
    (d/'Makefile').write_text(make,newline='\n')
    shutil.copyfile(ROOT/'src/nes/firmware/nes_nrom406.c',d/'nes_nrom406.c')
    shutil.copyfile(ROOT/'src/nes/firmware/nes_nrom406.h',d/'nes_nrom406.h')
    shutil.copyfile(BASE/'probes/nes-nrom406/cart02/cart_nrom.sv',d/'cart_nrom.sv')
    spi=(BASE/'probes/nes-repeat227/asm02/nes_rom_spi.sv').read_text()
    assert spi.count("8'h74,flags")==2
    spi=spi.replace("8'h74,flags","8'h78,flags")
    (d/'nes_rom_spi.sv').write_text(spi,newline='\n')
    q=d/'nes_h1_stm32.c';s=q.read_text()
    s=once(s,'#include "nes_native165_bulk.inc"','#include "nes_native165_bulk.inc"\n#include "nes_nrom406.h"')
    s=once(s,'rx[1]!=0x74||(rx[4]&0xf8)','rx[1]!=0x78||(rx[4]&0xf8)')
    s=once(s,'uint32_t total,expected_crc,crc,next;uint8_t *buffer;',
           'uint32_t total,expected_crc,crc,next;uint8_t *buffer;struct nes_nrom406_profile profile;')
    s=once(s,'''  if(!load_read(c->file,c->buffer,256,r))return false;
  c->crc=load_crc(c->crc,c->buffer,256);''','''  bool from_file;uint32_t file_offset;
  if(!nes_nrom406_layout(&c->profile,address,&from_file,&file_offset))return false;
  if(from_file) {
   if(f_tell(c->file)!=file_offset){r->result=NES_MCU_LOAD_CHANGED;return false;}
   if(!load_read(c->file,c->buffer,256,r))return false;
   c->crc=load_crc(c->crc,c->buffer,256);
  } else memset(c->buffer,0,256);''')
    s=once(s,'f_size(c->file)!=c->total+16u', 'f_size(c->file)!=c->profile.file_bytes')
    position=s.index('bool nes_menu_sd_probe(')
    prefix, s=s[:position],s[position:]
    s=once(s,'bool opened=false,changed_fpga=false,begin_sent=false;\n if(!r || !path',
           'bool opened=false,changed_fpga=false,begin_sent=false;\n struct nes_nrom406_profile nrom={0};\n if(!r || !path')
    start=s.index(' /* Exact target SMB3(J) header/length/CRC;')
    end=s.index('\n configure116:',start)
    s=s[:start]+''' /* Fixed NROM16 horizontal FPGA profile; status ID 78 is checked after
  * configuration. First pass establishes the file identity; the subsequent
  * passes must match it before END and verified START. CRC is not authentication. */
 if(!nes_nrom406_header(header,(uint32_t)f_size(&file),&nrom) ||
    nrom.prg_bytes!=16384u || nrom.vertical || expected_chr32) {
  r->result=NES_MCU_LOAD_HEADER;goto cleanup;
 }
 r->chr_32k=false;total=0x60000u;
 crc=load_crc(crc,header,16);
 for(uint32_t offset=16;offset<nrom.file_bytes;offset+=sizeof(buffer)) {
  if(!load_read(&file,buffer,sizeof(buffer),r))goto cleanup;
  crc=load_crc(crc,buffer,sizeof(buffer));
  nes_diag_progress(NES_DIAG_VALIDATE,offset+sizeof(buffer)-16,nrom.file_bytes-16);
 }
 expected_crc=crc^0xffffffffu;
 r->file_result=f_lseek(&file,0);
 if(r->file_result!=FR_OK){r->result=NES_MCU_LOAD_SEEK;goto cleanup;}
''' + s[end:]
    old='''  if(!load_read(&file,buffer,sizeof(buffer),r))goto cleanup;
  crc=load_crc(crc,buffer,sizeof(buffer));
  nes_diag_progress(NES_DIAG_LOAD,offset,total);'''
    new='''  bool from_file;uint32_t file_offset;
  if(!nes_nrom406_layout(&nrom,offset,&from_file,&file_offset)){r->result=NES_MCU_LOAD_CHANGED;goto cleanup;}
  if(from_file) {
   if(f_tell(&file)!=file_offset){r->result=NES_MCU_LOAD_CHANGED;goto cleanup;}
   if(!load_read(&file,buffer,sizeof(buffer),r))goto cleanup;
   crc=load_crc(crc,buffer,sizeof(buffer));
  } else memset(buffer,0,sizeof(buffer));
  nes_diag_progress(NES_DIAG_LOAD,offset,total);'''
    s=once(s,old,new)
    s=once(s,'if(f_size(&file)!=total+16u || (crc^0xffffffffu)!=expected_crc)',
           'if(f_size(&file)!=nrom.file_bytes || (crc^0xffffffffu)!=expected_crc)')
    s=once(s,'if(memcmp(buffer,header,16)||f_size(&file)!=total+16u)',
           'if(memcmp(buffer,header,16)||f_size(&file)!=nrom.file_bytes)')
    s=once(s,'struct sd_source_context ctx={&file,r,&opened,total,expected_crc,load_crc(0xffffffffu,buffer,16),0,buffer};',
           'struct sd_source_context ctx={&file,r,&opened,total,expected_crc,load_crc(0xffffffffu,buffer,16),0,buffer,nrom};')
    s=once(s,'/* Qualified only here: exact SMB3 CHR-ROM header, three file CRC passes,',
           '/* Qualified only here: fixed NROM CHR-ROM header, three file CRC passes,')
    q.write_text(prefix+s,newline='\n')
    q=d/'nes_rom_verify.c';s=q.read_text()
    s=once(s,'rx[1]==0x74','rx[1]==0x78')
    s=once(s,'rx[1]!=0x74','rx[1]!=0x78')
    q.write_text(s,newline='\n')
    q=d/'nes_run136.inc';s=q.read_text();s=once(s,'candidate->board_id=0x74','candidate->board_id=0x78');q.write_text(s,newline='\n')
    names=['Makefile','nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc','nes_nrom406.c','nes_nrom406.h','cart_nrom.sv','nes_rom_spi.sv']
    (d/'manifest407.json').write_text(json.dumps({'profile':'NROM16 horizontal CHR-ROM8 no PRG-RAM',
        'board_reply_id':'78','sources':{n:sha(d/n) for n in names},'production_changed':False,
        'physical_hardware':False,'full_loader_test':False},indent=2)+'\n',newline='\n')
    print(json.dumps({'profile':'NROM16 horizontal','board_id':'78','sources':len(names)}))


if __name__=='__main__':main()
