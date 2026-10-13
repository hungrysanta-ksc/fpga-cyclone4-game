# SPDX-License-Identifier: MIT
"""Check full linked runtime, retained fail-stop and explicit stack contributors."""
from pathlib import Path
import argparse,json,re,struct,subprocess
from nes_game147 import ROOT,sha

def main():
 p=argparse.ArgumentParser()
 for n in ['arm','arm-bin','out']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out.mkdir(parents=True,exist_ok=False)
 src=a.arm/'src';obj=src/'obj-nes-100';elf=obj/'sd2snes.elf';fw=obj/'firmware.stm'
 prep=json.loads((a.arm/'preparation-runtime165.json').read_bytes())
 for n,h in prep['copied'].items():assert sha(a.arm/n)==prep['changed'].get(n,h),n
 for n,h in prep['added'].items():assert sha(a.arm/n)==h,n
 def tool(name,args,label):
  raw=subprocess.check_output([str(a.arm_bin/('arm-none-eabi-'+name+'.exe')),*args,str(elf)])
  (a.out/(label+'.txt')).write_bytes(raw);return raw.decode(errors='replace').replace('\r\n','\n')
 symbols=tool('nm',['-S'],'symbols');dis=tool('objdump',['-d'],'disassembly')
 symbol={m[4]:(int(m[1],16),int(m[2],16),m[3]) for m in re.finditer(r'^([\da-f]+) ([\da-f]+) (\w) (\S+)$',symbols,re.M)}
 blocks={m[1]:m[2] for m in re.finditer(r'^[\da-f]+ <([^>]+)>:\n(.*?)(?=^[\da-f]+ <|\Z)',dis,re.M|re.S)}
 for n in ['nes_runtime165_step','nes_native165_bulk','nes_native165_poll','nes_native165_prepare','nes_native_video165_build','nes_sink165_seal','nes_sink_spi165_exchange','nes_display_enter146','nes_display_leave146','nes_rom_verified_start','nes_menu_diagnostic_run','nes_menu_sd_probe','NMI_Handler','stop108']:
  assert n in symbol and n in blocks,n
 probe=blocks['nes_menu_sd_probe'];assert '<nes_runtime165_step>' in probe
 assert probe.index('<nes_display_enter146>')<probe.index('<nes_runtime165_step>')<probe.index('<nes_display_leave146>')
 assert '<nes_runtime165_log_buffer>' in blocks['save_report']
 assert '<nes_cf86_check094>' in blocks['nes_native165_bulk'] and 'strb' in blocks['nes_native165_bulk']
 assert '<stop108>' in blocks['NMI_Handler']
 stop=blocks['stop108'];assert 'cpsid' in stop and not re.search(r'\bblx?(?:\.w)?\s',stop)
 assert len(re.findall(r'\bstr(?:\.w)?\s',stop))==15
 assert len(re.findall(r'\bdsb\s',stop))==3 and len(re.findall(r'\bisb\s',stop))==2
 assert struct.unpack_from('<I',fw.read_bytes(),0x208)[0]==(symbol['NMI_Handler'][0]|1)
 for token in [b'NES-GAME165-DEV',b'NES GAME 165.nh1',b'nes-progress-165.txt',b'nes-game-last-165.txt',b'board_expected_hex=74',b'native_frames=']:
  assert token in fw.read_bytes(),token
 for token in [b'NES GAME 164.nh1',b'NES VERIFY 094 80.nh1']:assert token not in fw.read_bytes(),token
 assert 'rx[1]!=0xe6||rx[7]!=2' in (src/'nes_run136.inc').read_text()
 assert '0x6b' not in (src/'nes_rom_verify.c').read_text()
 cfg=(obj/'autoconf.h').read_text()
 for n,v in [('SNES_RESET_REG','GPIOA'),('SNES_RESET_BIT','0'),('FPGA_PROGBREG','GPIOA'),('FPGA_PROGBBIT','(1)'),('FPGA_SSREG','GPIOA'),('FPGA_SSBIT','(4)')]:
  assert re.search(r'^#define\s+'+n+r'\s+'+re.escape(v)+r'\s*$',cfg,re.M),n
 stacks={};usage={}
 for f in obj.rglob('*.su'):
  usage[f.relative_to(obj).as_posix()]=sha(f)
  for line in f.read_text().splitlines():
   loc,n,kind=line.split('\t');name=loc.rsplit(':',1)[-1]
   stacks[name]=max(stacks.get(name,0),int(n))
 assert stacks['save_report']==768 and symbol['native_work165'][1]==15888
 assert symbol['native_receiver165'][1]==18064
 sections=tool('size',['-A'],'sections')
 heap=int(re.search(r'^([\da-f]+) \w __heap_start$',symbols,re.M)[1],16)
 top=int(re.search(r'^([\da-f]+) \w __stack$',symbols,re.M)[1],16)
 ram=heap-0x20000070
 assert top==0x20010000 and top-heap==65424-ram
 # Include the orphan .ahbram section and any alignment, not just data+bss.
 assert ram>=sum(int(re.search(r'^'+re.escape(n)+r'\s+(\d+)',sections,re.M)[1]) for n in ['.data','.ahbram','.bss'])
 # Explicit nested foreground chain. NOT a whole-program/ISR upper bound.
 chain=['main','nes_menu_diagnostic_run','nes_menu_sd_probe','nes_runtime165_step','nes_native_video165_build','nes_sink165_pattern','packet','nes_sink_spi165_exchange','transfer','guard','native_service165','observe136','nes_game149_transfer','nes149_wait']
 subtotal=sum(stacks[n] for n in chain)
 assert ram<65424 and subtotal<65424-ram
 result=dict(passed=True,firmware_bytes=fw.stat().st_size,firmware_sha256=sha(fw),elf_sha256=sha(elf),ram_static_bytes=ram,ram_capacity=65424,ram_after_static=65424-ram,receiver_bytes=18064,video_or_log_bytes=15888,runtime_bytes=symbol['native_runtime165'][1],save_report_stack=stacks['save_report'],foreground_chain=[dict(function=n,stack=stacks[n]) for n in chain],foreground_subtotal=subtotal,stack_usage_files=usage,whole_program_stack_approved=False,interrupt_nesting_approved=False,hardware_package=False,scope='Actual complete ARM link and fail-stop/call-site checks. Subtotal is an explicit foreground path only; IRQ/library/other menu paths and integration remain to review before SD.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:v for k,v in result.items() if k not in ['stack_usage_files','foreground_chain']}))
if __name__=='__main__':main()
