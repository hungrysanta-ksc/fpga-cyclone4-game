# SPDX-License-Identifier: MIT
"""Compare the same packet/tile/receipt schedule with shared vs separate RAM."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_mux258 import sources
from nes_delta231 import ROOT,BASE,sha


def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--out',type=Path,required=True);p.add_argument('--questa-bin',type=Path)
 p.add_argument('--guards',action='store_true');p.add_argument('--guard-cases',type=int,nargs='+')
 p.add_argument('--map-test',type=Path);p.add_argument('--shared',type=int,choices=[0,1],default=1)
 a=p.parse_args();d=a.out.resolve();assert d.as_posix().isascii() and not d.exists();d.mkdir(parents=True)
 pins={};src=sources()
 for n,s in src.items():(d/n).write_text(s,encoding='utf-8',newline='\n')
 def copy(f):pins[f.relative_to(BASE).as_posix()]=sha(f);shutil.copyfile(f,d/f.name)
 for n in ['nes_bulk_aperture188','nes_domain_reset124']:
  folder=ROOT/'src/nes/rtl' if n=='nes_bulk_aperture188' else BASE/'probes/nes-source240/board01'
  copy(folder/(n+'.sv'));src[n+'.sv']=''
 copy(BASE/'probes/nes-source240/board01/nes_native_mailbox206.sv');src['nes_native_mailbox206.sv']=''
 copy(BASE/'probes/nes-source240/board01/nes_tile_bulk206.sv')
 for n in ['nes_mux258.py','probe_nes_mux258.py']:copy(ROOT/'tools'/n)
 copy(ROOT/'tests/nes-functional/mux258_tb.sv')
 hashes={n:sha(d/n) for n in src}
 def run(exe,args,cwd,label,timeout=180):
  with (cwd/(label+'.log')).open('wb') as f:q=subprocess.run([str(exe),*args],cwd=cwd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
  log=(cwd/(label+'.log')).read_text(errors='replace')
  assert q.returncode==0 and not re.search(r'\*\* (Error|Fatal):',log),log[-6000:]
  return log
 if a.map_test:
  test=json.loads((a.map_test/'result.json').read_text());assert test['passed'] and test['rtl_hashes']==hashes
  (d/'mux.qpf').write_text('PROJECT_REVISION = "mux"\n',newline='\n')
  (d/'mux.qsf').write_text('\n'.join(['set_global_assignment -name FAMILY "Cyclone IV E"','set_global_assignment -name DEVICE EP4CE15F17C8','set_global_assignment -name TOP_LEVEL_ENTITY nes_mux258','set_global_assignment -name NUM_PARALLEL_PROCESSORS 2','set_global_assignment -name PROJECT_OUTPUT_DIRECTORY output_files',f'set_parameter -name SHARED {a.shared}',*[f'set_global_assignment -name SYSTEMVERILOG_FILE {n}' for n in src]])+'\n',newline='\n')
  run('C:/altera_lite/25.1std/quartus/bin64/quartus_map.exe',['mux'],d,'map',600)
  summary=(d/'output_files/mux.map.summary').read_text();result=dict(passed=True,summary=summary,shared=a.shared,fit=False,STA=False,test_hash=sha(a.map_test/'result.json'));print(summary)
 else:
  assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
  run(a.questa_bin/'vlib.exe',['work'],d,'vlib');run(a.questa_bin/'vlog.exe',['-sv',*src,'mux258_tb.sv'],d,'vlog')
  cases=[]
  for shared in [0,1]:
   for guard in [0]+(a.guard_cases or list(range(1,17)) if a.guards else []):
    gd=d/f'shared{shared}-guard{guard:02}';gd.mkdir()
    run(a.questa_bin/'vmap.exe',['-c'],gd,'vmap_init');run(a.questa_bin/'vmap.exe',['work',str(d/'work')],gd,'vmap')
    log=run(a.questa_bin/'vsim.exe',['-c','work.mux258_tb',f'-gSHARED={shared}',f'-gGUARD={guard}','-do','onerror {quit -code 1};run -all;quit -f'],gd,'vsim')
    assert 'PASS MUX258' in log
    case=dict(shared=shared,guard=guard)
    if not guard:
     m=re.search(r'ticks=(\d+) bytes=(\d+) receipts=(\d+) ordinary=(\d+)',log);assert m
     case.update(zip(['ticks','bytes','receipts','ordinary'],map(int,m.groups())))
     m=re.search(r'mapwait=(\d+) ordinaryhold=(\d+) ackcheck=(\d+)',log);assert m
     case.update(zip(['map_wait_tile','ordinary_hold','ack_check'],map(int,m.groups())))
    cases.append(case);print(json.dumps(case),flush=True)
  assert (d/'shared0-guard00/events.csv').read_bytes()==(d/'shared1-guard00/events.csv').read_bytes()
  result=dict(passed=True,cases=cases,events_identical=True,actual_SNES=False,receipt_service='fixed8 NES-cycle test endpoint; actual core is separate coupled test',physical=False)
 result.update(rtl_hashes=hashes,input_hashes=pins,scope=__doc__)
 (d/'result.json').write_text(json.dumps(result,indent=2)+'\n',newline='\n')


if __name__=='__main__':main()
