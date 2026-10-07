# SPDX-License-Identifier: MIT
"""Check076 compile-only ARM and host evidence; does not install firmware."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,zlib
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source-root',type=Path,required=True);p.add_argument('--tests',type=Path,required=True);p.add_argument('--objdump',type=Path,required=True);a=p.parse_args();src=a.source_root/'src';w=a.tests
 prep=json.loads((a.source_root/'preparation076.json').read_bytes())
 changed=[n for n,h in prep['pinned069'].items() if sha(a.source_root/n)!=h];assert set(changed)=={'src/Makefile','src/memory.c','src/nes_menu_return.c'},changed
 for n,h in json.loads((w/'host-03/result.json').read_bytes())['inputs'].items():assert sha(src/n)==h,n
 for name in ['class-crc','copy-crc']:
  m=json.loads((w/('mutation-'+name)/'result.json').read_bytes());assert m['exit'] and m['mutation']==name
 assert json.loads((w/'host-03/result.json').read_bytes())['checks']==853
 elf=src/'obj-nes-069/sd2snes.elf';fw=src/'obj-nes-069/firmware.stm';data=fw.read_bytes()
 assert data[:4]==b'STM3' and int.from_bytes(data[8:12],'little')==len(data)-512 and int.from_bytes(data[12:16],'little')==zlib.crc32(data[512:]) and b'NES-MENU076-CF68' in data
 calls={}
 for name,targets in {'load_rom':['nes_menu_classify076','nes_menu_approved076','nes_return_copy_menu'],'nes_menu_classify076':['f_lseek','f_read','nes_menu_crc076','nes_return_io_step'],'nes_return_copy_menu':['nes_menu_crc076','sram_writeblock','sram_readblock','nes_return_io_step']}.items():
  raw=subprocess.check_output([str(a.objdump),'-d','--disassemble='+name,str(elf)]);(w/(name+'-076.txt')).write_bytes(raw);text=raw.decode()
  calls[name]=re.findall(r'\bbl(?:\.w)?\s+\w+\s+<([^>]+)>',text)
  for target in targets:assert target in calls[name],(name,target)
 log=(w/'arm-02.log').read_text(encoding='utf-8-sig');assert 'PASS069 manual ELF markers=3' in log and 'PASS069 CF68 compare and READY_before_GPIO' in log
 result=dict(candidate='NES-MENU076-CF68',firmware_bytes=len(data),firmware_sha256=sha(fw),elf_sha256=sha(elf),changed_pinned069=changed,unchanged_pinned069=272,host_checks=853,causal_mutations=2,calls=calls,installable=False,physical=False)
 (w/'check076.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result,indent=2))
if __name__=='__main__':main()
