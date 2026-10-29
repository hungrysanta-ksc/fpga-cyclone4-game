# SPDX-License-Identifier: MIT
"""Execute 418 menu loader preflight with malformed inputs; platform calls modeled."""
import argparse,collections,json,struct,sys
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
sys.path.insert(0,str(BASE/'.tools/arm259-python'))
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_MODE_MCLASS,UC_HOOK_CODE
from unicorn.arm_const import UC_ARM_REG_PC,UC_ARM_REG_SP,UC_ARM_REG_LR,UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3,UC_ARM_REG_XPSR
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser();p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
obj=BASE/'probes/nes-nrom418/arm01/src/obj-nes-100';elf=obj/'sd2snes.elf';fw=obj/'firmware.stm';rom=BASE/'probes/nes-nrom428/fixture01/nrom16.nes';raw=rom.read_bytes();assert sha(fw)=='596a8a73ca2b8a66f946fe612b1f4480ecff258e01b2e9bf32b952e0448cd30c'
names=['nes_menu_sd_probe','nes_diag_sd_handoff113','nes_checkpoint_begin112','nes_checkpoint112','nes_cf86_enter094','nes_css_begin108','nes_menu_entry_only113','nes_menu_base_only116','nes_cf86_check094','nes_cf86_failed094','nes_cf86_finish094','nes_cf86_monitoring094','nes_diag_sd_failed','nes_return_failed','nes_return_fail','nes_menu_diagnostic_pending','nes_diag_leave','nes_diag_progress','nes_diag_fpga_pgm','snes_reset','slow_end','f_open','f_read','f_close','f_lseek','nes_game149_transfer','fpga_test']
with elf.open('rb') as f:
 e=ELFFile(f);segments=[(x['p_vaddr'],x.data()) for x in e.iter_segments() if x['p_type']=='PT_LOAD' and x['p_filesz']];symbols={x.name:x['st_value']&~1 for x in e.get_section_by_name('.symtab').iter_symbols() if x.name in names};sizes={x.name:x['st_size'] for x in e.get_section_by_name('.symtab').iter_symbols() if x.name in names};assert set(symbols)==set(names),set(names)-set(symbols)
 report=[]
 for cu in e.get_dwarf_info().iter_CUs():
  for z in cu.iter_DIEs():
   v=z.attributes.get('DW_AT_name')
   if z.tag=='DW_TAG_structure_type' and v and v.value==b'nes_mcu_load_report':report.append((z.attributes['DW_AT_byte_size'].value,{c.attributes['DW_AT_name'].value.decode():c.attributes['DW_AT_data_member_location'].value for c in z.iter_children() if 'DW_AT_name' in c.attributes and 'DW_AT_data_member_location' in c.attributes}))
 assert report and all(x[0]==20 and x[1]['result']==[35,0] for x in report)
start=symbols['nes_menu_sd_probe'];seg=next((base,data) for base,data in segments if base<=start<base+len(data));blob=seg[1][start-seg[0]:start-seg[0]+sizes['nes_menu_sd_probe']];assert len(blob)==sizes['nes_menu_sd_probe'] and fw.read_bytes()[start-0x0800c000:start-0x0800c000+len(blob)]==blob
true_hooks={'nes_diag_sd_handoff113','nes_checkpoint_begin112','nes_checkpoint112','nes_cf86_enter094','nes_css_begin108','nes_cf86_check094','nes_cf86_finish094'}
false_hooks={'nes_menu_entry_only113','nes_menu_base_only116','nes_cf86_failed094','nes_cf86_monitoring094','nes_diag_sd_failed','nes_return_failed','nes_menu_diagnostic_pending'}
void_hooks={'nes_return_fail','nes_diag_leave','nes_diag_progress','snes_reset','slow_end'}
cases=[]
for label,change,size in [('magic',lambda h:h.__setitem__(0,0),len(raw)),('mapper',lambda h:h.__setitem__(6,0x10),len(raw)),('vertical',lambda h:h.__setitem__(6,1),len(raw)),('trainer',lambda h:h.__setitem__(6,4),len(raw)),('nes2',lambda h:h.__setitem__(7,8),len(raw)),('chr_ram',lambda h:h.__setitem__(5,0),len(raw)),('short',lambda h:None,len(raw)-1),('valid_control',lambda h:None,len(raw))]:
 data=bytearray(raw);change(data);data=bytes(data[:size]);u=Uc(UC_ARCH_ARM,UC_MODE_THUMB|UC_MODE_MCLASS);u.mem_map(0x08000000,0x80000);u.mem_map(0x20000000,0x20000);u.mem_map(0x40000000,0x100000);u.mem_map(0xe000e000,0x2000)
 for address,blob in segments:u.mem_write(address,blob)
 sentinel=0x0807fff0;path=0x20001000;image=0x20001100;out=0x20001200;stack=0x2001e000;u.mem_write(path,b'nrom.nes\0');u.mem_write(image,b'nrom.bi3\0');calls=collections.Counter();pos=[0]
 def finish(uc,value):uc.reg_write(UC_ARM_REG_R0,value);uc.reg_write(UC_ARM_REG_PC,uc.reg_read(UC_ARM_REG_LR))
 def hook(uc,address,n,user):
  if address==sentinel:uc.emu_stop();return
  name=next(k for k,v in symbols.items() if v==address);calls[name]+=1
  if name in true_hooks:finish(uc,1)
  elif name in false_hooks or name in void_hooks:finish(uc,0)
  elif name in ('nes_game149_transfer','fpga_test'):raise AssertionError('invalid header reached FPGA transport')
  elif name=='nes_diag_fpga_pgm':
   if label!='valid_control':raise AssertionError('invalid header configured FPGA')
   uc.emu_stop()
  elif name=='f_open':
   fp=uc.reg_read(UC_ARM_REG_R0);uc.mem_write(fp,b'\0'*16);uc.mem_write(fp+12,struct.pack('<I',len(data)));pos[0]=0;finish(uc,0)
  elif name=='f_read':
   fp=uc.reg_read(UC_ARM_REG_R0);dest=uc.reg_read(UC_ARM_REG_R1);n=uc.reg_read(UC_ARM_REG_R2);got=uc.reg_read(UC_ARM_REG_R3);chunk=data[pos[0]:pos[0]+n];uc.mem_write(dest,chunk);pos[0]+=len(chunk);uc.mem_write(fp+8,struct.pack('<I',pos[0]));uc.mem_write(got,struct.pack('<I',len(chunk)));finish(uc,0)
  elif name=='f_lseek':
   fp=uc.reg_read(UC_ARM_REG_R0);pos[0]=uc.reg_read(UC_ARM_REG_R1);uc.mem_write(fp+8,struct.pack('<I',pos[0]));finish(uc,0)
  elif name=='f_close':finish(uc,0)
  else:raise AssertionError(name)
 for name in true_hooks|false_hooks|void_hooks|{'nes_diag_fpga_pgm','f_open','f_read','f_close','f_lseek','nes_game149_transfer','fpga_test'}:u.hook_add(UC_HOOK_CODE,hook,begin=symbols[name],end=symbols[name])
 u.hook_add(UC_HOOK_CODE,hook,begin=sentinel,end=sentinel)
 for reg,value in zip((UC_ARM_REG_R0,UC_ARM_REG_R1,UC_ARM_REG_R2,UC_ARM_REG_R3),(path,image,0,out)):u.reg_write(reg,value)
 u.reg_write(UC_ARM_REG_SP,stack);u.reg_write(UC_ARM_REG_LR,sentinel|1);u.reg_write(UC_ARM_REG_XPSR,0x01000000);u.emu_start(start|1,sentinel+2,count=5000000)
 if label=='valid_control':
  assert u.reg_read(UC_ARM_REG_PC)==symbols['nes_diag_fpga_pgm'] and calls['nes_diag_fpga_pgm']==1 and pos[0]==0 and calls['f_lseek']==1,(label,calls,pos)
  cases.append({'case':label,'program_reached':True,'read_calls':calls['f_read'],'scope':'deliberately stopped before configuring'});continue
 assert u.reg_read(UC_ARM_REG_PC)==sentinel,label
 safe=u.reg_read(UC_ARM_REG_R0);result=bytes(u.mem_read(out,36));assert safe==1 and result[0]==2 and calls['nes_diag_fpga_pgm']==0 and calls['f_open']==1 and calls['f_close']==1,(label,safe,result.hex(),calls)
 cases.append({'case':label,'safe_return':safe,'load_result':result[0],'read_bytes':pos[0],'program_calls':calls['nes_diag_fpga_pgm'],'calls':dict(calls)})
r={'passed':True,'firmware_sha256':sha(fw),'elf_sha256':sha(elf),'rom_sha256':sha(rom),'cases':cases,'scope':'actual linked ARM menu-loader invalid-header branch with modeled FatFS, platform and hardware calls; no physical FPGA or complete loader'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
