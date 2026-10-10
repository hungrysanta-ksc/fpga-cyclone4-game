# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,json,re,struct,subprocess,shutil
from nes_spi_boot import ROOT,sha
def main():
 p=argparse.ArgumentParser()
 for n in ['arm','host','objdump','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();s=a.arm/'src';o=a.out;o.mkdir(parents=True,exist_ok=False);shutil.copy2(__file__,o/'executed-check.py')
 prep=json.loads((a.arm/'preparation145.json').read_bytes())
 for n,h in prep['copied'].items():
  if n=='executed-builder.ps1':assert sha(a.arm/n)==sha(ROOT/'tools/build_nes_screen145_arm.ps1')
  else:assert sha(a.arm/n)==prep['changed'].get(n,h),n
 for n in ['nes_menu_return.c','nes_menu_diagnostic.c','nes_h1_stm32.c','nes_checkpoint112.c','nes_run136.inc','nes_run136.h','nes_cf86_session094.h','nes_rom_verify.c','nes_rom_spi.c','nes_cf86_session094.c']:
  assert sha(s/n)==sha(a.host/n),n
 handoff=(ROOT/'src/nes/firmware/nes_sd_entry113.inc').read_text(encoding='utf-8')
 assert handoff in (s/'stm32f4xx/sdnative.c').read_text(encoding='utf-8')
 assert handoff in (a.host/'native.inc').read_text(encoding='utf-8')
 actual=(s/'fpga.c').read_text(encoding='utf-8')
 actual=actual[actual.index('struct nes_diag_input '):].strip()
 assert actual==(a.host/'config.inc').read_text(encoding='utf-8').strip()
 cfg=(s/'obj-nes-100/autoconf.h').read_text()
 for n,v in [('SNES_RESET_REG','GPIOA'),('SNES_RESET_BIT','0'),('FPGA_PROGBREG','GPIOA'),('FPGA_PROGBBIT','(1)'),('FPGA_SSREG','GPIOA'),('FPGA_SSBIT','(4)')]:
  assert re.search(r'^#define\s+'+n+r'\s+'+re.escape(v)+r'\s*$',cfg,re.M),n
 elf=s/'obj-nes-100/sd2snes.elf';fw=s/'obj-nes-100/firmware.stm'
 def dump(*args):return subprocess.check_output([str(a.objdump),*args,str(elf)])
 sym=dump('-t');(o/'symbols.txt').write_bytes(sym);table=sym.decode(errors='replace')
 nmi=re.search(r'^([0-9a-f]+)\s+g\s+F\s+\.text\s+[0-9a-f]+ NMI_Handler\s*$',table,re.M);assert nmi
 ptr=struct.unpack_from('<I',fw.read_bytes(),0x208)[0]
 assert ptr==(int(nmi[1],16)|1),(hex(ptr),nmi[1])
 d={}
 for n in ['NMI_Handler','stop108','nes_css_begin108','nes_css_end108','nes_css_fault108','nes_return_failed','nes_diag_leave','nes_menu_sd_probe','nes_checkpoint112','nes_checkpoint_begin112','nes_checkpoint_progress112','nes_diag_sd_handoff113','nes_menu_diagnostic_run','nes_menu_entry_only113','nes_menu_base_only116','nes_diag_fpga_pgm','nes_return_checkpoint_enter112','nes_return_checkpoint_leave112']:
  raw=dump('-d','--disassemble='+n);(o/(n+'.txt')).write_bytes(raw);d[n]=raw.decode(errors='replace');assert '<'+n+'>:' in d[n],n
 assert '<stop108>' in d['NMI_Handler'] and 'bx\tlr' not in d['NMI_Handler']
 stop=d['stop108'];assert 'cpsid' in stop and not re.search(r'\bblx?(?:\.w)?\s',stop)
 assert not re.search(r'\bbx\s+lr|\bpop[^\n]*pc',stop)
 assert len(re.findall(r'\bstr(?:\.w)?\s',stop))==15
 assert len(re.findall(r'\bdsb\s',stop))==3 and len(re.findall(r'\bisb\s',stop))==2
 for token in ['0x40020000','0x40023800','0xe000e100','#131072','#2621440','#8388608']:assert token in stop,token
 assert stop.index('#131072')<re.search(r'\bmovs\s+r2, #16\b',stop).start() # nCONFIG before CS
 assert '<nes_css_fault108>' in d['nes_return_failed']
 leave=d['nes_diag_leave'];assert leave.index('<nes_css_end108>')<leave.index('<nes_diag_observe>') and '<nes_diag_blocked>' in leave
 probe=d['nes_menu_sd_probe'];assert probe.index('<nes_css_begin108>')<probe.index('<f_open>')
 assert probe.index('<nes_diag_sd_handoff113>')<probe.index('<nes_checkpoint_begin112>')<probe.index('<nes_cf86_enter094>')<probe.index('<nes_css_begin108>')<probe.index('<f_open>')
 assert probe.index('<nes_menu_entry_only113>')<probe.index('<f_open>')
 assert probe.index('<nes_menu_base_only116>')<probe.index('<f_open>')
 assert '<nes_checkpoint112>' in d['nes_diag_fpga_pgm']
 run=d['nes_menu_diagnostic_run'];assert run.index('<nes_diag_begin>')<run.index('<nes_menu_sd_probe>')
 assert '<nes_diag_begin>' not in probe
 for token in ['<nes_entry_owner113>','<cmd_fast>','<nes_return_failed>']:
  assert token in d['nes_diag_sd_handoff113'],token
 assert b'NES-SCREEN145' in fw.read_bytes()
 assert b'NES SCREEN 145.nh1' in fw.read_bytes()
 assert b'nes-progress-145.txt' in fw.read_bytes()
 for name in ['f_open','f_lseek','f_write','f_sync','f_close','nes_return_checkpoint_enter112','nes_return_checkpoint_leave112']:
  assert '<'+name+'>' in d['nes_checkpoint112'],name
 assert '<nes_css_end108>' not in probe # leave function owns balanced release
 assert '<nes_rom_verified_start>' in probe
 assert b'nes-screen-last-145.txt' in fw.read_bytes()
 assert b'NES VERIFY 094 80.nh1' not in fw.read_bytes()
 assert b'NES BASE 116.nh1' not in fw.read_bytes()
 assert b'DISPLAY_NEXT' in fw.read_bytes() and b'DISPLAY_STOPPED' in fw.read_bytes()
 assert '<nes_display_enter145>' in probe and '<nes_display_leave145>' in probe
 assert probe.index('<nes_display_enter145>')<probe.index('<nes_display_leave145>')
 result=dict(firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),nmi_address='0x'+nmi[1],vector_word=hex(ptr),stop_stores=15,stop_calls=0,stop_dsb=3,stop_isb=2,host_sources_match=True,strong_nmi=True,arm_execution=False,physical=False,installable=False)
 (o/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
