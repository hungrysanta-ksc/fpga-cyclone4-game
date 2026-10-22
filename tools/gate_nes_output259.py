# SPDX-License-Identifier: MIT
"""Regression of258 ownership guards and a source-bound Lite-only MAP."""
import argparse,json,os,re,shutil,subprocess
from pathlib import Path
from nes_output259 import sources
from nes_delta231 import BASE,ROOT,sha

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path);p.add_argument('--map-test',type=Path);p.add_argument('--shared',type=int,choices=[0,1],default=1)
 a=p.parse_args();d=a.out.resolve();assert not d.exists() and d.as_posix().isascii();d.mkdir(parents=True)
 src=sources()
 for n,s in src.items():(d/n).write_text(s,newline='\n')
 for n in ['nes_domain_reset124.sv','nes_native_mailbox206.sv','nes_bulk_aperture188.sv']:
  shutil.copyfile(BASE/'probes/nes-mux258/test07'/n,d/n);src[n]=''
 hashes={n:sha(d/n) for n in src}
 def run(exe,args,where,label,timeout=180):
  with (where/(label+'.log')).open('wb') as f:r=subprocess.run([str(exe),*args],cwd=where,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
  s=(where/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-4000:];return s
 if a.map_test:
  r=json.loads((a.map_test/'result.json').read_text());assert r['passed'] and r['rtl_hashes']==hashes
  (d/'output.qpf').write_text('PROJECT_REVISION = "output"\n')
  (d/'output.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_output259','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',f'set_parameter -name SHARED {a.shared}',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in src]])+'\n')
  run('C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe',['output'],d,'map',600)
  result=dict(passed=True,shared=a.shared,summary=(d/'output_files/output.map.summary').read_text(),test_sha256=sha(a.map_test/'result.json'),FIT=False,STA=False);print(result['summary'])
 else:
  assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
  tb=(ROOT/'tests/nes-functional/mux258_tb.sv').read_text().replace('mux258_tb','mux259_tb').replace('nes_mux258','nes_output259').replace('op==9','op==12').replace('send_packet(9,','send_packet(12,')
  (d/'mux259_tb.sv').write_text(tb,newline='\n')
  run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'mux259_tb.sv'],d,'vlog')
  cases=[]
  for shared in [0,1]:
   for guard in range(17):
    gd=d/f'shared{shared}-guard{guard:02}';gd.mkdir()
    run(a.questa_bin/'vmap.exe',['-c'],gd,'vmap0');run(a.questa_bin/'vmap.exe',['work',str(d/'work')],gd,'vmap')
    s=run(a.questa_bin/'vsim.exe',['-c','work.mux259_tb',f'-gSHARED={shared}',f'-gGUARD={guard}','-do','onerror {quit -code 1};run -all;quit -f'],gd,'vsim');assert 'PASS MUX258' in s
    cases.append([shared,guard]);print('PASS259',shared,guard,flush=True)
  assert (d/'shared0-guard00/events.csv').read_bytes()==(d/'shared1-guard00/events.csv').read_bytes()
  result=dict(passed=True,cases=cases,scope='258 normal+16 ownership guards on259, typed opcode12 and ordinary sections preserved')
 result['rtl_hashes']=hashes;(d/'result.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
