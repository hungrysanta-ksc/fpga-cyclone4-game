# SPDX-License-Identifier: MIT
"""Materialize142 from pinned141; retain the working ROM service and menu recovery."""
from pathlib import Path
import argparse,json,re,shutil
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def put(p,s):p.write_text(s,encoding='utf-8',newline='\n')

def prepare(base,out,kind):
 assert not out.exists();e=base/'nes-screen141/evidence'
 meta=json.loads((ROOT/'analysis/screen141-verification.json').read_bytes())
 assert sha(e/'manifest.json')==meta['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];copied={}
 prefix=kind+'/'
 for n,h in pins.items():
  if not n.startswith(prefix):continue
  rel=n[len(prefix):];p=Path(rel)
  if kind=='fit' and (rel.startswith(('db/','incremental_db/','output_files/','client/')) or p.suffix not in ['.sv','.v','.vhd','.hex','.sdc','.qsf','.qpf']):continue
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='host' and p.suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  assert sha(e/n)==h,n
  d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 if kind=='fit':
  from build_nes_screen142 import build
  # The consumer uses only16KiB CHR; this is the same diagnostic atlas as137.
  chr_data=bytes(int(x,16) for x in (out/'chr.hex').read_text().split())
  rom=build(chr_data[:16384],out/'client');shutil.copy2(rom,out/'screen-program.hex')
  p=out/'nes_rom_spi.sv';put(p,p.read_text().replace("8'h5d","8'h5e"))
  p=out/'nes_run_observer134.sv';put(p,p.read_text().replace("8'hd8","8'hd9"))
  shutil.copy2(ROOT/'src/nes/diagnostic/nes_screen_status142.sv',out/'nes_screen_status142.sv')
  p=out/'nes_live_joint.sv';s=p.read_text();s=once(s,'output wire out_host_clk,','output wire out_host_locked,output wire out_host_clk,');s=once(s,'assign out_host_clk=', 'assign out_host_locked=locked;\nassign out_host_clk=');put(p,s)
  p=out/'fxpak_nes_screen137_top.sv';s=p.read_text();s=once(s,'wire host_clk,run_enable;', 'wire host_clk,run_enable,host_locked;\n wire status_reset,status_selected,status_miso,status_receive,consumer_oe,consumer_dir;')
  s=once(s,'.out_host_clk(host_clk),','.out_host_locked(host_locked),.out_host_clk(host_clk),')
  s=once(s,'assign SPI_MISO=boot_selected&&!observer_selected?boot_miso:\n                 observer_selected&&!boot_selected?observer_miso:1\'bz;', '''assign SPI_MISO=boot_selected&&!observer_selected&&!status_selected?boot_miso:
                 observer_selected&&!boot_selected&&!status_selected?observer_miso:
                 status_selected&&!boot_selected&&!observer_selected?status_miso:1'bz;
 nes_domain_reset124 status_release(.clk(host_clk),.raw_reset(power_reset||!host_locked),.reset(status_reset));
 nes_screen_status142 screen_status(.clk(host_clk),.reset(status_reset),.active(run_enable&&!core_reset),
  .address(SNES_ADDR_IN),.read_n(SNES_READ_IN),.write_n(SNES_WRITE_IN),.romsel_n(SNES_ROMSEL_IN),.data_in(SNES_DATA),
  .SPI_SS(SPI_SS),.SPI_SCK(SPI_SCK),.SPI_MOSI(SPI_MOSI),
  .receive_write(status_receive),.selected(status_selected),.miso(status_miso));''')
  s=once(s,'.oe_n(SNES_DATABUS_OE),.dir(SNES_DATABUS_DIR));', '''.oe_n(consumer_oe),.dir(consumer_dir));
 assign SNES_DATABUS_DIR=consumer_dir;
 assign SNES_DATABUS_OE=consumer_oe&&!status_receive;''');put(p,s)
  p=out/'board.qsf';put(p,p.read_text()+'\nset_global_assignment -name SYSTEMVERILOG_FILE nes_screen_status142.sv\n')
 else:
  root=out/'src' if kind=='arm' else out
  names=['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc','nes_cf86_session094.c','nes_cf86_session094.h','nes_rom_verify.c']
  if kind=='host':names+=['card.c','config097_card.inc','host109.c','platform.c']
  for n in names:
   p=root/n;s=p.read_text(encoding='utf-8');pieces=re.split(r'(\b0x[0-9a-fA-F]+)',s)
   s=''.join(x if i%2 else x.replace('141','142') for i,x in enumerate(pieces))
   if n in ['nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc','platform.c']:
    s=re.sub(r'\b0x5d\b','0x5e',s);s=re.sub(r'\b0xd8\b','0xd9',s)
   s=s.replace('board_expected_hex=5d','board_expected_hex=5e');put(p,s)
  p=root/'nes_run136.h';s=once(p.read_text(),'uint8_t first_error,stop_error,context_valid;', 'uint8_t first_error,stop_error,context_valid;\n uint8_t screen_valid,screen_stage,screen_error,screen_flags;uint16_t screen_frames;');put(p,s)
  p=root/'nes_run136.inc';s=p.read_text();s=once(s,'static bool identify136', '''static bool screen142(const struct nes_rom_spi_io *io){
 uint8_t tx[8]={0x73,0,0,0,0,0,0,0},rx[8]={0};
 if(!nes_rom_spi_transfer(io,tx,rx))return false;
 if(rx[1]!=0xd9||rx[7]!=1||(rx[4]&0xf8u))return false;
 nes_run136.screen_valid=1;nes_run136.screen_stage=rx[2];nes_run136.screen_error=rx[3];
 nes_run136.screen_flags=rx[4];nes_run136.screen_frames=((uint16_t)rx[5]<<8)|rx[6];
 return true;
}
static bool identify136''')
  # Snapshot after STOP while ownership and SPI are valid, before reconfiguration.
  s=once(s,'nes_run136.error=nes_run136.first_error?', 'if(!screen142(io))return nes_cf86_fail094();\n nes_run136.error=nes_run136.first_error?');put(p,s)
  p=root/'nes_menu_diagnostic.c';s=p.read_text().replace('char text[896]','char text[1152]')
  s=once(s,'fault_context_lo=%08lx\\n",', 'fault_context_lo=%08lx\\nscreen_status_valid=%u\\nscreen_stage=%u\\nscreen_error=%u\\nscreen_flags=%u\\nscreen_frames=%u\\n",')
  s=once(s,'(unsigned long)nes_run136.context_lo);','(unsigned long)nes_run136.context_lo,nes_run136.screen_valid,nes_run136.screen_stage,nes_run136.screen_error,nes_run136.screen_flags,nes_run136.screen_frames);');put(p,s)
  if kind=='arm':put(root/'VERSION','RELEASE_VERSION = "NES-SCREEN142"\n')
  else:
   p=root/'platform.c';s=p.read_text();s=once(s,'if(tx[0]==0x71||tx[0]==0x72){assert(bits==64);return;}', 'if(tx[0]==0x71||tx[0]==0x72||tx[0]==0x73){assert(bits==64);return;}')
   s=once(s,'if(tx[0]==0x71||tx[0]==0x72){\n', '''if(tx[0]==0x73){
    assert(reset_held&&stop_count);reply[1]=0xd9;reply[2]=6;reply[3]=0;reply[4]=7;reply[5]=0;reply[6]=3;reply[7]=1;
   }else if(tx[0]==0x71||tx[0]==0x72){
''');put(p,s)
 put(out/'preparation142.json',json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}),indent=2)+'\n')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['fit','arm','host'],required=True)
 a=p.parse_args();prepare(a.baseline,a.out,a.kind)
