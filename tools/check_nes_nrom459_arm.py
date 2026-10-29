# SPDX-License-Identifier: MIT
"""Execute actual 418 ELF functions, byte-matched in STM, in Cortex-M emulator."""
from pathlib import Path
import argparse,hashlib,json,struct,sys,time,zlib
from nes_delta231 import BASE,ROOT,sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
obj=BASE/'probes/nes-nrom418/arm01/src/obj-nes-100';elf=obj/'sd2snes.elf';fw=obj/'firmware.stm';rom=BASE/'probes/nes-nrom428/fixture01/nrom16.nes';raw=rom.read_bytes();assert sha(fw)=='596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c';assert sha(rom)=='61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c'
u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000);symbols={};flash=fw.read_bytes();matches={}
with elf.open('rb') as f:
 e=ELFFile(f);segments=[x for x in e.iter_segments() if x['p_type']=='PT_LOAD'];
 for seg in segments:
  if seg['p_filesz']:u.mem_write(seg['p_vaddr'],seg.data())
 for sym in e.get_section_by_name('.symtab').iter_symbols():
  if sym.name in ('nes_nrom406_header','nes_nrom406_layout','load_crc','nes_rom_spi_frame'):
   address=sym['st_value']&~1;size=sym['st_size'];seg=next(x for x in segments if x['p_vaddr']<=address and address+size<=x['p_vaddr']+x['p_filesz']);blob=seg.data()[address-seg['p_vaddr']:address-seg['p_vaddr']+size];at=flash.find(blob);assert at>=0 and flash.find(blob,at+1)<0;symbols[sym.name]=address;matches[sym.name]={'elf_address':address,'size':size,'stm_offset':at,'code_sha256':hashlib.sha256(blob).hexdigest()}
assert len(symbols)==4
sentinel=0x0807fff0
u.hook_add(UC_HOOK_CODE,lambda uc,address,size,user:uc.emu_stop() if address==sentinel else None,begin=sentinel,end=sentinel)
def call(n,*args):
 for reg,v in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),args):u.reg_write(reg,v)
 u.reg_write(UC_ARM_REG_SP,0x2001f000);u.reg_write(UC_ARM_REG_LR,sentinel|1);u.reg_write(UC_ARM_REG_XPSR,0x01000000);u.emu_start(symbols[n]|1,sentinel+2,count=2000000);assert u.reg_read(UC_ARM_REG_PC)==sentinel;return u.reg_read(UC_ARM_REG_R0)
hdr=0x20001000;profile=0x20001100;from_file=0x20001200;file_at=0x20001204
u.mem_write(hdr,raw[:16]);assert call('nes_nrom406_header',hdr,len(raw),profile)==1;assert bytes(u.mem_read(profile,9))==struct.pack('<II',16384,len(raw))+b'\0'
invalid=[]
for label,mutate,size in [('magic',lambda h:h.__setitem__(0,0),len(raw)),('mapper',lambda h:h.__setitem__(6,0x10),len(raw)),('nes2',lambda h:h.__setitem__(7,8),len(raw)),('trainer',lambda h:h.__setitem__(6,4),len(raw)),('chr_ram',lambda h:h.__setitem__(5,0),len(raw)),('prg_count',lambda h:h.__setitem__(4,3),len(raw)),('short_file',lambda h:None,len(raw)-1),('reserved',lambda h:h.__setitem__(8,1),len(raw))]:
 h=bytearray(raw[:16]);mutate(h);u.mem_write(hdr,bytes(h));assert call('nes_nrom406_header',hdr,size,profile)==0,label;invalid.append(label)
u.mem_write(hdr,raw[:16]);assert call('nes_nrom406_header',hdr,len(raw),profile)==1
start=time.monotonic();source_count=zero_count=0;digest=hashlib.sha256()
for at in range(0x60000):
 assert call('nes_nrom406_layout',profile,at,from_file,file_at)==1,at
 src=u.mem_read(from_file,1)[0];loc=int.from_bytes(u.mem_read(file_at,4),'little');expect=16+at if at<16384 else 16400+at-0x40000 if 0x40000<=at<0x42000 else None
 assert src==(expect is not None) and loc==(expect if expect is not None else 0),(at,src,loc,expect)
 if src:source_count+=1;digest.update(raw[loc:loc+1])
 else:zero_count+=1;digest.update(b'\0')
assert call('nes_nrom406_layout',profile,0x60000,from_file,file_at)==0
independent=bytearray(0x60000);independent[:0x4000]=raw[16:0x4010];independent[0x40000:0x42000]=raw[0x4010:0x6010];assert hashlib.sha256(independent).hexdigest()==digest.hexdigest()
# Actual linked loader CRC over the iNES file, checked against independent zlib.
buf=0x20002000;u.mem_write(buf,raw);crc=call('load_crc',0xffffffff,buf,len(raw))^0xffffffff;assert crc==zlib.crc32(raw)
# Actual SPI framing against independently generated CRC8 over all command types.
frame=0x20010000;frame_cases=0
for op in (0x60,0x61,0x62,0x63,0x64,0x66,0x67,0x68,0x69,0x6a):
 for off in (0,1,0x3ffff,0x60000):
  for data in (0,0x5a,0xff):
   call('nes_rom_spi_frame',frame,op,off,data);actual=bytes(u.mem_read(frame,8));prefix=bytes([op,(off>>16)&255,(off>>8)&255,off&255,data,data^255]);c=0
   for byte in prefix:
    c^=byte
    for _ in range(8):c=((c<<1)^7 if c&0x80 else c<<1)&255
   assert actual==prefix+bytes([c,0xa5]),(op,off,data,actual.hex());frame_cases+=1
r={'passed':True,'elf_sha256':sha(elf),'firmware_sha256':sha(fw),'rom_sha256':sha(rom),'linked_code_matches_stm':matches,'header_rejections':invalid,'ines_crc32':f'{crc:08x}','spi_frame_cases':frame_cases,'physical_offsets':0x60000,'rom_bytes':source_count,'zero_bytes':zero_count,'expanded_sha256':digest.hexdigest(),'wall_seconds':round(time.monotonic()-start,3),'scope':'actual linked ARM machine code in Unicorn with independently checked mapping, no peripheral/IRQ/full loader/physical timing'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
