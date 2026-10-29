# SPDX-License-Identifier: MIT
"""Execute linked old/new M4 packet decoders on actual RTL blocks."""
import argparse,hashlib,json,sys,struct
from pathlib import Path
from nes_delta231 import BASE,sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('--new-arm',required=True,type=Path);p.add_argument('--new-blocks',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
def execute(src,blocks):
 elf=src/'obj-nes-100/sd2snes.elf';fw=src/'obj-nes-100/firmware.stm';flash=fw.read_bytes();u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000)
 with elf.open('rb') as f:
  e=ELFFile(f);segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_filesz']]
  syms={x.name:(x['st_value']&~1,x['st_size']) for x in e.get_section_by_name('.symtab').iter_symbols() if x['st_info']['type']=='STT_FUNC'}
  offsets=[]
  for cu in e.get_dwarf_info().iter_CUs():
   for z in cu.iter_DIEs():
    if z.tag=='DW_TAG_structure_type' and z.attributes.get('DW_AT_name') and z.attributes['DW_AT_name'].value==b'nes_native165':
     for c in z.iter_children():
      if c.attributes.get('DW_AT_name') and c.attributes['DW_AT_name'].value==b'token_valid':offsets.append(c.attributes['DW_AT_data_member_location'].value[1])
  assert offsets and len(set(offsets))==1
 for b,v in segments:u.mem_write(b,v)
 for n in ['nes_native165_reset','nes_native165_packet','nes_native165_prepare']:
  at,size=syms[n];b,v=next((b,v) for b,v in segments if b<=at and at+size<=b+len(v));assert flash[at-0x0800c000:at-0x0800c000+size]==v[at-b:at-b+size]
 state=0x20010000;buf=0x20015000;end=0x0807fff0;callback=0x0807ffe0;count=0;calls=0
 def crc8(bs):
  c=0
  for v in bs:
   c^=v
   for _ in range(8):c=((c<<1)^7 if c&128 else c<<1)&255
  return c
 def hook(uc,at,size,user):
  nonlocal count,calls
  if at==end:uc.emu_stop();return
  if at==callback:
   rx=bytearray(8);rx[1]=0xd6;rx[2]=2;rx[7]=crc8(rx[1:7]);uc.mem_write(uc.reg_read(UC_ARM_REG_R2),bytes(rx));calls+=1;uc.reg_write(UC_ARM_REG_R0,1);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR));return
  count+=1
 u.hook_add(UC_HOOK_CODE,hook)
 def call(n,args):
  for reg,v in zip([UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3],args):u.reg_write(reg,v)
  u.reg_write(UC_ARM_REG_SP,0x2001f000);u.reg_write(UC_ARM_REG_LR,end|1);u.reg_write(UC_ARM_REG_XPSR,0x01000000);u.emu_start(syms[n][0]|1,end+2,count=20000000);assert u.reg_read(UC_ARM_REG_PC)==end;return u.reg_read(UC_ARM_REG_R0)
 call('nes_native165_reset',[state]);packet_instructions=0
 for line in blocks.read_text().splitlines():
  tok,n,h=line.split();data=bytes.fromhex(h)
  # COMMIT is a whole control block. Prepare through the actual callback ABI first.
  if data[:2]==b'\xe0\x03':assert call('nes_native165_prepare',[state,1,callback|1,0])==1
  u.mem_write(buf,data);before=count;assert call('nes_native165_packet',[state,int(tok),buf,len(data)])==1
  packet_instructions+=count-before
 return {'firmware_sha256':sha(fw),'packet_instructions':packet_instructions,'total_instructions':count,'prepare_callbacks':calls,'canonical_prefix':bytes(u.mem_read(state,offsets[0]))}
old=execute(BASE/'probes/nes-nrom418/arm01/src',BASE/'probes/nes-nrom429/core01/nrom429-blocks.txt');new=execute(a.new_arm,a.new_blocks)
assert old['canonical_prefix']==new['canonical_prefix'] and old['prepare_callbacks']==new['prepare_callbacks']==3
h=hashlib.sha256(new['canonical_prefix']).hexdigest();old.pop('canonical_prefix');new.pop('canonical_prefix')
r={'passed':True,'old':old,'new':new,'canonical_prefix_sha256':h,'instruction_delta':new['packet_instructions']-old['packet_instructions'],'scope':'actual linked M4 packet and prepare code, exact canonical state excluding transport token; counts are instructions not hardware cycles/fullRUN/IRQ/SPI/VBlank time'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
