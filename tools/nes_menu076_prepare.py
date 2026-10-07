# SPDX-License-Identifier: MIT
"""Additive076 menu profile to pinned069; compile-only, no SD driver change."""
from pathlib import Path
import argparse,json,shutil
from nes_sd_inventory_prepare import digest,BASE_MANIFEST,ROOT
def once(s,a,b):assert s.count(a)==1,a;return s.replace(a,b,1)
def adapt(src):
 for n in ['nes_menu076.c','nes_menu076.h']:shutil.copy2(ROOT/'src/nes/firmware'/n,src/n)
 p=src/'memory.c';s=p.read_text();s=once(s,'#include "nes_menu_return.h"','#include "nes_menu_return.h"\n#include "nes_menu076.h"')
 s=once(s,'strcmp((const char *)filename,MENU_FILENAME)||flags)','strcmp((const char *)filename,MENU_FILENAME)||flags||base_addr)')
 start=s.index('  sgb_id(&sgb_romprops, sgb_filename);',s.index('uint32_t load_rom('));end=s.index('\n\n  if(flags & LOADROM_WITH_COMBO)',start)
 old=s[start:end];assert 'romprops.header.carttype>2' in old
 s=s[:start]+'''  if(nes_diag_active()) {
    /* The global read-only file is already open. On a shared failure do not
     * perform another file operation; the RESET-held caller blocks recovery. */
    if(!nes_menu_classify076(&romprops))return 0;
    file_close();
    if(file_res!=FR_OK||nes_return_failed()||!nes_menu_approved076(&romprops)){
      nes_return_fail(NES_DIAG_MENU);return 0;
    }
  } else {
'''+old+'''
  }'''+s[end:];p.write_text(s,encoding='utf-8',newline='\n')
 p=src/'nes_menu_return.c';s=p.read_text();s=once(s,'#include "nes_menu_return.h"','#include "nes_menu_return.h"\n#include "nes_menu076.h"')
 s=once(s,'uint32_t copied=0;','uint32_t copied=0,crc=0xffffffffu;')
 s=once(s,' if(r!=FR_OK){nes_return_fail(NES_DIAG_MENU);return 0;}',' if(r!=FR_OK||nes_return_failed()){nes_return_fail(NES_DIAG_MENU);return 0;}')
 s=once(s,'bool ok=size>offset&&size-offset<=0x400000u&&address<=0xffffffu-(size-offset-1u);','bool ok=size==NES_MENU076_SIZE&&!offset&&!address;')
 s=once(s,'  UINT n=size-offset-copied;','  if(!nes_return_io_step()){ok=false;break;}\n  UINT n=size-offset-copied;')
 s=once(s,'  if(r!=FR_OK||got!=n){ok=false;break;}','  if(r!=FR_OK||got!=n||nes_return_failed()){ok=false;break;}\n  crc=nes_menu_crc076(crc,data,n);')
 s=once(s,' if(f_size(&file)!=size)ok=false;',' if(f_size(&file)!=size||(crc^0xffffffffu)!=NES_MENU076_CRC)ok=false;')
 s=once(s,' if(f_close(&file)!=FR_OK)ok=false;',' if(!nes_return_failed()){if(f_close(&file)!=FR_OK)ok=false;}else ok=false;\n if(nes_return_failed())ok=false;')
 p.write_text(s,encoding='utf-8',newline='\n')
 p=src/'Makefile';p.write_text(once(p.read_text(),'nes_menu_return.c','nes_menu_return.c nes_menu076.c'),encoding='utf-8',newline='\n')
 # Keep069 marker names and CF68 protocol for this compile-only integration;
 # no new SD pair is delivered. VERSION distinguishes the candidate firmware.
 (src/'VERSION').write_bytes(b'RELEASE_VERSION = "NES-MENU076-CF68"\r\n')
def main():
 p=argparse.ArgumentParser();p.add_argument('--mcu-root',type=Path,required=True);p.add_argument('--mcu-evidence',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 assert not a.out.exists() and digest(a.mcu_evidence/'manifest.json')==BASE_MANIFEST
 pins={n[4:]:h for n,h in json.loads((a.mcu_evidence/'manifest.json').read_bytes())['files'].items() if n.startswith('arm/src/')};assert len(pins)==275
 for n,h in pins.items():assert digest(a.mcu_root/n)==h,n
 shutil.copytree(a.mcu_root,a.out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.exe','*.elf','*.stm','*.sof','*.rbf','db','incremental_db','output_files'))
 adapt(a.out/'src')
 (a.out/'preparation076.json').write_text(json.dumps(dict(baseline=BASE_MANIFEST,pinned069=pins,inputs={p.relative_to(a.out).as_posix():digest(p) for p in a.out.rglob('*') if p.is_file()},installable=False),indent=2)+'\n',encoding='utf-8')
 print('PASS076 prepared pinned069=275; compile-only')
if __name__=='__main__':main()
