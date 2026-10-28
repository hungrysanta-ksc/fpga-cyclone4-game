# SPDX-License-Identifier: MIT
"""Run real 227 board/core with NROM424 PSRAM seeded, no physical claim."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_functional import VHDL
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args()
d=a.out.resolve();board=a.board.resolve();assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
raw=a.rom.read_bytes();assert len(raw)==24592 and raw[:6]==b'NES\x1a\x01\x01'
for q in board.rglob('*'):
 if any(n in ('db','incremental_db','output_files','simulation') for n in q.relative_to(board).parts):continue
 if q.is_file() and q.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
  dest=d/q.relative_to(board);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dest)
(d/'fixture-prg.hex').write_text(''.join('%02x\n'%x for x in raw[16:16400]),newline='\n')
(d/'fixture-chr.hex').write_text(''.join('%02x\n'%x for x in raw[16400:]),newline='\n')
for name in ('run133_pll_model.sv','rom_boot_model.sv'):shutil.copyfile(ROOT/'tests/nes-functional'/name,d/name)
shutil.copyfile(ROOT/'tests/nes-nrom426/core_tb.sv',d/'core_tb.sv')
names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(d/'board.qsf').read_text())
exe=Path('C:/altera_standard/25.1std/questa_fse/win64')
def run(name,cmd,timeout=600):
 with(d/(name+'.log')).open('wb') as f:r=subprocess.run([str(exe/(cmd[0]+'.exe')),*cmd[1:]],cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-6000:]
run('vlib',['vlib','work'])
for i,n in enumerate(VHDL):run('vcom-%d'%i,['vcom','-2008',n])
sv=[n for n in names if n not in VHDL and n!='nes_clock_pll123.v']
if 'nes_native_ciram165.sv' not in sv:sv.append('nes_native_ciram165.sv')
run('vlog',['vlog','-sv','-mfcu',*sv,'run133_pll_model.sv','rom_boot_model.sv','core_tb.sv'])
run('simulation',['vsim','-L','altera_mf_ver','-c','work.core_tb','-do','onerror {quit -code 1};run -all;quit -f'],timeout=1800)
log=(d/'simulation.log').read_text(errors='replace');assert 'PASS NROM426 actual seeded NROM core pixel' in log and 'Errors: 0' in log,log[-6000:]
result={'passed':True,'fixture_sha256':sha(a.rom),'cart_sha256':sha(board/'cart_nrom.sv'),'tb_sha256':sha(d/'core_tb.sv'),'scope':'actual 227 board/NES core and NROM mapper, seeded PSRAM/verified loader, manual SNES bus program read and pad writes, core pixels and SPI STOP; not actual loader, 65816 execution, actual controller or hardware'}
(d/'result.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
