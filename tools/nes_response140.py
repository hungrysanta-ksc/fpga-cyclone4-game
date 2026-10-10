# SPDX-License-Identifier: MIT
"""139 derivative: publish RUN completion at pin release; keep all read phases."""
from pathlib import Path
import argparse,json,shutil,subprocess,re
from nes_spi_boot import ROOT,sha
from nes_menu098 import once

def fit_delta(o):
 p=o/'nes_rom_spi.sv';s=p.read_text();assert s.count("8'h5b")==2;p.write_text(s.replace("8'h5b","8'h5c"))
 p=o/'nes_run_observer134.sv';p.write_text(p.read_text().replace("8'hd6","8'hd7"))
 p=o/'nes_rom_physical.sv';s=p.read_text()
 s=once(s,'HOLD:state<=RELEASE;', '''HOLD:begin
     //140 Data was sampled on the previous memory edge. CE/OE are released
     // on this edge. Publish RUN completion now; keep RELEASE and IDLE intact.
     // The source still observes ACK through its original two-stage chain.
     state<=RELEASE;
     if(!owner_check)ack_toggle<=request_sync[1];
    end''')
 s=once(s,'if(owner_check)check_response<=1;else ack_toggle<=request_sync[1];','if(owner_check)check_response<=1;')
 p.write_text(s,encoding='utf-8',newline='\n')

def prepare(base,out,kind):
 assert not out.exists();e=base/'nes-fault139/evidence'
 m=json.loads((ROOT/'analysis/fault139-verification.json').read_bytes())
 assert sha(e/'manifest.json')==m['manifest_sha256']
 pins=json.loads((e/'manifest.json').read_bytes())['files']
 prefix={'fit':'fit02/','arm':'arm03/','host':'host05/'}[kind];copied={}
 for n,h in pins.items():
  if not n.startswith(prefix):continue
  rel=n[len(prefix):];p=Path(rel)
  if kind=='fit' and (rel.startswith(('db/','incremental_db/','output_files/')) or p.suffix not in ['.sv','.v','.vhd','.hex','.sdc','.qsf','.qpf']):continue
  if kind=='arm' and (any(x.startswith(('obj-','.dep-')) for x in p.parts) or p.suffix in ['.exe','.elf','.stm','.lst','.map','.log','.txt'] or p.name in ['.ARG_VERSION','executed-builder.ps1']):continue
  if kind=='host' and p.suffix not in ['.c','.h','.inc','.nes','.packed','.raw','.bin']:continue
  assert sha(e/n)==h,n;d=out/rel;d.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(e/n,d);copied[rel]=h
 if kind=='fit':fit_delta(out)
 else:
  # Identifier/version-only MCU delta. Whole numeric tokens preserve CRC values.
  s=out/'src' if kind=='arm' else out
  version_files=['nes_menu_diagnostic.c','nes_checkpoint112.c','nes_h1_stm32.c','nes_run136.inc','nes_cf86_session094.c','nes_cf86_session094.h']
  id_files=['nes_h1_stm32.c','nes_rom_verify.c','nes_run136.inc']
  model_files=['card.c','config097_card.inc','host109.c','platform.c'] if kind=='host' else []
  for name in set(version_files+id_files+model_files):
   p=s/name
   t=p.read_text(encoding='utf-8');new=t.replace('139','140')
   if name in id_files+model_files:
    new=re.sub(r'\b0x5b\b','0x5c',new);new=re.sub(r'\b0xd6\b','0xd7',new)
   if name=='platform.c':
    new=re.sub(r'\b0x5a\b','0x5b',new);new=re.sub(r'\b0xd5\b','0xd6',new)
   new=new.replace('board_expected_hex=5b','board_expected_hex=5c')
   if new!=t:p.write_text(new,encoding='utf-8',newline='\n')
  assert (s/'nes_run136.inc').read_text()==(ROOT/'src/nes/firmware/nes_response140.inc').read_text()
  if kind=='arm':(s/'VERSION').write_text('RELEASE_VERSION = "NES-SCREEN140"\n')
 (out/'preparation140.json').write_text(json.dumps(dict(copied=copied,changed={n:sha(out/n) for n,h in copied.items() if sha(out/n)!=h}),indent=2)+'\n',encoding='utf-8')

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for n in ['baseline','out']:p.add_argument('--'+n,type=Path,required=True)
 p.add_argument('--kind',choices=['arm','fit','host'],required=True);p.add_argument('--quartus-bin',type=Path)
 a=p.parse_args();prepare(a.baseline,a.out,a.kind)
 if a.quartus_bin:
  for phase in ['map','fit','sta']:
   with (a.out/(phase+'.log')).open('wb') as f:r=subprocess.run([str(a.quartus_bin/f'quartus_{phase}.exe'),'board'],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=900)
   print(phase,r.returncode,flush=True);assert r.returncode==0
