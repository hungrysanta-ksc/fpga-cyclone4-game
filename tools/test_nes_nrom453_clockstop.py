# SPDX-License-Identifier: MIT
"""Actual full-board modeled PLL clock-loss and sticky-reset test."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from nes_delta231 import ROOT,sha
from nes_functional import VHDL
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
for q in a.board.rglob('*'):
 if any(n in ('db','incremental_db','output_files','simulation','work') for n in q.relative_to(a.board).parts):continue
 if q.is_file() and q.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
  dest=d/q.relative_to(a.board);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dest)
for n in ('run133_pll_model.sv','rom_boot_model.sv'):shutil.copyfile(ROOT/'tests/nes-functional'/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom453/clockstop_tb.sv',d/'clockstop_tb.sv');raw=a.rom.read_bytes();assert len(raw)==24592 and raw[:6]==b'NES\x1a\x01\x01';(d/'fixture-prg.hex').write_text(''.join(f'{x:02x}\n' for x in raw[16:16400]));(d/'fixture-chr.hex').write_text(''.join(f'{x:02x}\n' for x in raw[16400:]))
bin=Path('C:/altera_standard/25.1std/questa_fse/win64');names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(d/'board.qsf').read_text());rtl=[n for n in names if n not in VHDL and n!='nes_clock_pll123.v'];
if 'nes_native_ciram165.sv' not in rtl:rtl.append('nes_native_ciram165.sv')
def run(name,cmd,timeout=120):
 with (d/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,cmd)),cwd=d,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
 s=(d/(name+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:];return s
run('vlib',[bin/'vlib.exe','work'])
for i,n in enumerate(VHDL):run('vcom-'+str(i),[bin/'vcom.exe','-2008',n])
run('vlog',[bin/'vlog.exe','-sv','-mfcu',*rtl,'run133_pll_model.sv','rom_boot_model.sv','clockstop_tb.sv'])
for mode in (0,1):
 s=run('mode'+str(mode),[bin/'vsim.exe','-L','altera_mf_ver','-c','work.nrom453_tb',f'+MODE={mode}','-do','onerror {quit -code 1};run -all;quit -f'],300);assert f'PASS NROM453 clock-stop mode={mode}' in s and 'Errors: 0' in s
r={'passed':True,'rom_sha256':sha(a.rom),'rtl_sha256':sha(d/'nes_live_joint.sv'),'testbench_sha256':sha(d/'clockstop_tb.sv'),'scope':'full board RTL, modeled PLL and PSRAM, seeded verified state; separate NES/reference and memory clock stops; not physical timing or CDC MTBF'};(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
