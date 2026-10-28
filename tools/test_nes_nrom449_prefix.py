# SPDX-License-Identifier: MIT
"""Actual 227 FatFS loader to full board RTL and full-size functional PSRAM, bounded prefix."""
import argparse,os,re,shutil,subprocess,json
from pathlib import Path
from nes_delta231 import ROOT,BASE,sha
from nes_functional import VHDL
p=argparse.ArgumentParser();p.add_argument('--board',type=Path,required=True);p.add_argument('--rom',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();d=a.out.resolve()
assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
prod=BASE/'probes/nes-repeat227/arm01/src'; build=BASE/'probes/nes-nrom407/build04'; full=BASE/'probes/nes-nrom411/full01'; raw=a.rom.read_bytes();assert len(raw)==24592 and raw[:6]==b'NES\x1a\x01\x01'
for q in a.board.rglob('*'):
 if any(n in ('db','incremental_db','output_files','simulation') for n in q.relative_to(a.board).parts):continue
 if q.is_file() and q.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
  dest=d/q.relative_to(a.board);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dest)
for n in ('run133_pll_model.sv',):shutil.copyfile(ROOT/'tests/nes-functional'/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom448/rom_boot_full_model.sv',d/'rom_boot_full_model.sv');shutil.copyfile(ROOT/'tests/nes-nrom449/prefix_tb.sv',d/'prefix_tb.sv');shutil.copyfile(a.rom,d/'fixture.nes');(d/'fixture-prg.hex').write_text(''.join(f'{v:02x}\n' for v in raw[16:272]))
for n in ('full408.inc','ff.c','ff.h','ffconf.h','diskio.h'):shutil.copyfile(full/n,d/n)
(d/'unicode').mkdir();shutil.copyfile(full/'unicode/ccsbcs.c',d/'unicode/ccsbcs.c')
for h in prod.glob('*.h'):shutil.copyfile(h,d/h.name)
for h in (BASE/'probes/nes-run136/evidence/initial/host04').glob('*.h'):shutil.copyfile(h,d/h.name)
for n in ('ff.h','ffconf.h','diskio.h'):shutil.copyfile(full/n,d/n)
s=(full/'bridge.c').read_text();old="for(uint32_t i=16;i<sizeof(filedata);i++)filedata[i]=(uint8_t)(i^(i>>8)^0xa5);";new='FILE *fixture=fopen("fixture.nes","rb");assert(fixture && fread(filedata,1,sizeof(filedata),fixture)==sizeof(filedata) && fgetc(fixture)==EOF);fclose(fixture);';assert s.count(old)==1;s=s.replace(old,new)
s=s.replace('if(tx[0]==NES_ROM_DATA){sent_data++;', 'if(tx[0]==NES_ROM_DATA && sent_data==TEST_LIMIT)return false;\n if(tx[0]==NES_ROM_DATA){sent_data++;')
old='worker_code=(!safe || !p.sd.verified || !p.sd.load.stop_ok || !p.sd.load.base_restored || sent_data!=TEST_LIMIT || sticky || irq_count!=1 || config_count!=2);';new='worker_code=(safe || p.sd.verified || sent_data!=TEST_LIMIT || !sticky || irq_count!=0);';assert s.count(old)==1;s=s.replace(old,new);(d/'bridge.c').write_text(s)
questa=Path('C:/altera_standard/25.1std/questa_fse');gcc=questa/'gcc-7.4.0-mingw64vc16/bin/gcc.exe';bin=questa/'win64';env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(d/'board.qsf').read_text());rtl=[n for n in names if n not in VHDL and n!='nes_clock_pll123.v'];
if 'nes_native_ciram165.sv' not in rtl:rtl.append('nes_native_ciram165.sv')
def run(name,cmd,timeout=120):
 with (d/(name+'.log')).open('wb') as f:q=subprocess.run(list(map(str,cmd)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 assert q.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-4000:]
run('compile',[gcc,'-shared','-std=c99','-O2','-Wno-unused-function','-DNROM_USE_FATFS','-DTEST_LIMIT=256','-I',d,'-I',build,'-I',prod,d/'ff.c',d/'unicode/ccsbcs.c',build/'nes_rom_verify.c',prod/'nes_rom_spi.c',build/'nes_nrom406.c',ROOT/'tests/nes-nrom408/fat_disk.c',d/'bridge.c','-o',d/'bridge.dll'])
run('vlib',[bin/'vlib.exe','work'])
for i,n in enumerate(VHDL):run('vcom-'+str(i),[bin/'vcom.exe','-2008',n])
run('vlog',[bin/'vlog.exe','-sv','-mfcu',*rtl,'run133_pll_model.sv','rom_boot_full_model.sv','prefix_tb.sv'])
run('simulation',[bin/'vsim.exe','-L','altera_mf_ver','-c','-sv_lib','bridge','work.nrom449_tb','-do','onerror {quit -code 1};run -all;quit -f'],300)
log=(d/'simulation.log').read_text(errors='replace');assert 'PASS NROM449 actual loader full board PSRAM prefix bytes=256' in log and 'Errors: 0' in log
result={'passed':True,'rom_sha256':sha(a.rom),'model_sha256':sha(d/'rom_boot_full_model.sv'),'bridge_sha256':sha(d/'bridge.c'),'scope':'256-byte intentional abort; actual 227 loader and FatFS host C, actual full board RTL, functional full-size PSRAM; no complete load/readback, RUN or hardware'};(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
