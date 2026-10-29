# SPDX-License-Identifier: MIT
"""Actual 418 ARM verification to 457 board SPI, fail-stop after 16 bytes."""
import argparse,json,os,re,shutil,subprocess,sys
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
from nes_functional import VHDL
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--rom',required=True,type=Path);p.add_argument('--out',required=True,type=Path);p.add_argument('--fault',choices=('source','corrupt'),default='source');a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists() and os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost';d.mkdir(parents=True)
for q in a.board.rglob('*'):
 if any(n in ('db','incremental_db','output_files','simulation','work') for n in q.relative_to(a.board).parts):continue
 if q.is_file() and q.suffix.lower() in ('.sv','.v','.vhd','.vh','.mif','.hex','.qsf','.qpf','.sdc','.qip'):
  dest=d/q.relative_to(a.board);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(q,dest)
for n in ('run133_pll_model.sv','rom_boot_model.sv','join208_rpc.c'):shutil.copyfile(ROOT/'tests/nes-functional'/n,d/n)
shutil.copyfile(ROOT/'tests/nes-nrom461/verify_tb.sv',d/'verify_tb.sv');raw=a.rom.read_bytes();assert sha(a.rom)=='61cc6ae495fb34dd6aa28497db6f584fa308063a79ba9412bde50c0c9419fd2c';(d/'fixture-prg.hex').write_text(''.join(f'{x:02x}\n' for x in raw[16:16400]));(d/'fixture-chr.hex').write_text(''.join(f'{x:02x}\n' for x in raw[16400:]))
questa=Path('C:/altera_standard/25.1std/questa_fse');gcc=questa/'gcc-7.4.0-mingw64vc16/bin/gcc.exe';bin=questa/'win64';env=os.environ.copy();env['PATH']=str(gcc.parent)+os.pathsep+env.get('PATH','')
names=re.findall(r'set_global_assignment -name (?:SYSTEMVERILOG|VERILOG|VHDL)_FILE (\S+)',(d/'board.qsf').read_text());rtl=[n for n in names if n not in VHDL and n!='nes_clock_pll123.v'];
if 'nes_native_ciram165.sv' not in rtl:rtl.append('nes_native_ciram165.sv')
def run(name,cmd):
 with(d/(name+'.log')).open('wb') as f:r=subprocess.run(list(map(str,cmd)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=120,creationflags=subprocess.CREATE_NO_WINDOW)
 assert r.returncode==0,(d/(name+'.log')).read_text(errors='replace')[-4000:]
run('rpc-build',[gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','-shared','join208_rpc.c','-o','join208_rpc.dll']);run('vlib',[bin/'vlib.exe','work'])
for i,n in enumerate(VHDL):run('vcom-'+str(i),[bin/'vcom.exe','-2008',n])
run('vlog',[bin/'vlog.exe','-sv','-mfcu',*rtl,'run133_pll_model.sv','rom_boot_model.sv','verify_tb.sv'])
children=[];logs=[]
try:
 for n,cmd in [('rtl',[bin/'vsim.exe','-L','altera_mf_ver','-c','-sv_lib','join208_rpc','work.nrom461_tb','-do','onerror {quit -code 1};run -all;quit -f']),('arm',[sys.executable,ROOT/'tools/check_nes_nrom461_arm.py','--out',d/'arm-result','--fault',a.fault])]:
  f=(d/(n+'.log')).open('wb');logs.append(f);children.append(subprocess.Popen(list(map(str,cmd)),cwd=d,env=env,stdout=f,stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NO_WINDOW))
 for child in (children[1],children[0]):
  child.wait(timeout=400)
  if child.returncode!=0:break
finally:
 for child in children:
  if child.poll() is None:child.kill();child.wait()
 for f in logs:f.close()
assert all(c.returncode==0 for c in children),[(d/(n+'.log')).read_text(errors='replace')[-4000:] for n in ('rtl','arm')]
rtl_log=(d/'rtl.log').read_text(errors='replace');assert 'PASS NROM461 ARM verify real board CHECK abort STOP' in rtl_log and 'Errors: 0' in rtl_log
r=json.loads((d/'arm-result/result.json').read_text());assert r['passed'];r['board_core_sha256']=sha(d/'nes_live_joint.sv');r['bench_sha256']=sha(d/'verify_tb.sv');(d/'result.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
