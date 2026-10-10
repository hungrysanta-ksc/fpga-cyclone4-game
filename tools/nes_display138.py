# SPDX-License-Identifier: MIT
"""Display-only delta on the physically tested136 MCU and selected137 FPGA."""
from pathlib import Path
import argparse,json,shutil,zlib,re,subprocess
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def fixture(base):
 e=base/'nes-screen137/evidence';m=json.loads((ROOT/'analysis/screen137-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 data=[]
 for n in ['prg.hex','chr.hex']:
  p=e/'fit03'/n;assert sha(p)==pins['fit03/'+n]
  data.append(bytes(int(x,16) for x in p.read_text().split()))
 assert list(map(len,data))==[65536,16384]
 return b'NES\x1a'+bytes([4,2,0x40,0])+bytes(8)+b''.join(data)

def adapt(src,base):
 def edit(n,old,new):
  p=src/n;p.write_text(once(p.read_text(encoding='utf8'),old,new),encoding='utf8',newline='\n')
 for n in ['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc']:
  p=src/n;s=p.read_text(encoding='utf8')
  s=s.replace('NES RUN 136.nh1','NES SCREEN 138.nh1').replace('NES-RUN-136','NES-SCREEN-138').replace('NES136','NES138')
  s=s.replace('nes-progress-136','nes-progress-138').replace('nes-run-last-136','nes-screen-last-138').replace('run136.nes','screen138.nes').replace('fpga_n136.bi3','fpga_n138.bi3')
  s=s.replace('board_expected_hex=59','board_expected_hex=5a')
  p.write_text(s,encoding='utf8',newline='\n')
 for n in ['nes_h1_stm32.c','nes_rom_verify.c']:
  p=src/n;s=p.read_text();assert '0x59' in s,n
  p.write_text(s.replace('0x59','0x5a'),encoding='utf8',newline='\n')
 edit('nes_h1_stm32.c','header[6]!=0 || header[7]!=0','header[6]!=0x40 || header[7]!=0')
 edit('nes_h1_stm32.c','expected_crc=0x8e37aafdu;',f'expected_crc=0x{zlib.crc32(fixture(base)):08x}u;')
 edit('nes_run136.inc','0xd4','0xd5');edit('nes_run136.inc','candidate->board_id=0x59','candidate->board_id=0x5a')
 edit('nes_run136.inc','"RUN_NEXT"','"DISPLAY_NEXT"')
 edit('nes_run136.inc','for(unsigned i=0;i<16;i++) {','if(!nes_display_enter138())return false;\n for(unsigned i=0;i<200;i++) {')
 edit('nes_run136.inc','wait_us(0,1000);','for(unsigned ms=0;ms<50;ms++){\n   wait_us(0,1000);\n   if(!nes_cf86_check094())return false;\n  }')
 edit('nes_run136.inc','uint8_t stop_tx[8],stop_rx[8];','if(!nes_display_leave138())return false;\n uint8_t stop_tx[8],stop_rx[8];')
 edit('nes_run136.inc','"RUN_STOPPED"','"DISPLAY_STOPPED"')
 edit('nes_run136.inc','Sixteen bounded observations; nominal waits16ms','Two hundred bounded observations; nominal waits10000ms')
 edit('nes_run136.inc','Actual116 delay/guard checks remain active.','Actual116 delay/guard checks remain active; ownership is checked every1ms.')
 edit('nes_run136.inc','strictly checks the59','strictly checks the5A')
 shutil.copy2(ROOT/'src/nes/firmware/nes_display_session138.c',src/'nes_cf86_session094.c')
 with (src/'nes_cf86_session094.h').open('a',encoding='utf8') as f:f.write('\nbool nes_display_enter138(void);\nbool nes_display_leave138(void);\n')

def prepare(base,out,kind):
 assert not out.exists();e=base/('nes-run136/evidence' if kind=='arm' else 'nes-screen137/evidence')
 meta=ROOT/'analysis'/('run136-verification.json' if kind=='arm' else 'screen137-verification.json')
 assert sha(e/'manifest.json')==json.loads(meta.read_bytes())['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files'];prefix='arm03/' if kind=='arm' else 'fit03/';copied={}
 for n,h in pins.items():
  if not n.startswith(prefix):continue
  rel=n[len(prefix):]
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in Path(rel).parts) or Path(rel).suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or Path(rel).name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='fit' and (rel.startswith(('db/','incremental_db/','output_files/')) or Path(rel).suffix not in ['.sv','.v','.vhd','.hex','.qsf','.qpf','.sdc']):continue
  assert sha(e/n)==h,n
  d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 if kind=='arm':
  adapt(out/'src',base);(out/'src/VERSION').write_text('RELEASE_VERSION = "NES-SCREEN138"\n',encoding='utf8')
 else:
  for name,old,new,count in [('nes_rom_spi.sv',"8'h59","8'h5a",2),('nes_run_observer134.sv',"8'hd4","8'hd5",1)]:
   p=out/name;s=p.read_text();assert s.count(old)==count;p.write_text(s.replace(old,new),encoding='utf8',newline='\n')
 changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}
 (out/'preparation138.json').write_text(json.dumps(dict(kind=kind,copied=copied,changed=changed),indent=2)+'\n',encoding='utf8')
 (out/'screen138.nes').write_bytes(fixture(base))
 return changed

def main():
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['arm','fit'],required=True);p.add_argument('--quartus-bin',type=Path)
 a=p.parse_args();print(prepare(a.baseline,a.out,a.kind),flush=True)
 if a.quartus_bin:
  for phase in ['map','fit','sta']:
   with (a.out/(phase+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/f'quartus_{phase}.exe'),'board'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=900)
   print(phase,r.returncode,flush=True);assert r.returncode==0
if __name__=='__main__':main()
