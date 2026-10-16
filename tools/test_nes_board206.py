# SPDX-License-Identifier: MIT
"""206 real direct path and partial tile fixtures, plus loader differential proof.
Generated benches retain old names for comparison. Not gameplay or physical CDC.
"""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess
from nes_board204 import ROOT,BASE,sha,replace
from nes_board206 import MODULES,transform
from test_nes_directloader165 import bench

def main():
 p=argparse.ArgumentParser()
 for n in ('out','questa-bin'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();a.out=a.out.resolve();a.out.mkdir(parents=True,exist_ok=False)
 assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 board=BASE/'probes/nes-board206/source02';pins={};cases={}
 def read(f):pins[f.relative_to(BASE).as_posix()]=sha(f);return f.read_text()
 def run(cmd,cwd,label,timeout=240,negative=False):
  with (cwd/(label+'.log')).open('wb') as log:r=subprocess.run(cmd,cwd=cwd,stdout=log,stderr=subprocess.STDOUT,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
  t=(cwd/(label+'.log')).read_text(errors='replace')
  if negative:assert '** Fatal:' in t and 'PASS STATE165' not in t,t[-3000:]
  else:assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',t),t[-5000:]
  return t
 for label,oldname in [('direct','test_nes_board205.py'),('atomic','test_nes_stream205.py')]:
  s=read(ROOT/'tools'/oldname)
  s=s.replace("BASE/'probes/nes-board205/source01'","BASE/'probes/nes-board206/source02'").replace('preparation205.json','preparation206.json')
  if label=='direct':
   for old,new in MODULES.items():
    if old!=new:s=s.replace(old,new)
   s=s.replace('nes_direct204 dut','nes_direct206 dut')
  else:
   s=replace(s,"ROOT/'src/nes/rtl/nes_tile_bulk193.sv'","BASE/'probes/nes-board206/source02/nes_tile_bulk206.sv'")
   s=replace(s,"BASE/'probes/nes-board204/source01/nes_native_mailbox165.sv'","BASE/'probes/nes-board206/source02/nes_native_mailbox206.sv'")
   s=replace(s,'shutil.copyfile(f,a.out/f.name);names.append(f.name);',"shutil.copyfile(f,a.out/f.name);\n  if f.name=='tile_stream205_tb.sv': (a.out/f.name).write_text(f.read_text().replace('nes_tile_bulk193 bulk','nes_tile_bulk206 bulk'),encoding='utf8',newline='\\n')\n  names.append(f.name);")
  # Make imports explicit; generated runners live outside tools.
  s="import sys\nsys.path.insert(0,"+repr(str(ROOT/'tools'))+")\n"+s
  script=a.out/(label+'.py');script.write_text(s,encoding='utf8',newline='\n')
  run([os.sys.executable,'-B','-X','utf8',str(script),'--out',str(a.out/label),'--questa-bin',str(a.questa_bin)],a.out,label,420)
  cases[label]=json.loads((a.out/label/'result.json').read_bytes())
 # Candidate vs205: all command priorities/states and actual timed writes.
 out=a.out/'loader';out.mkdir()
 old=read(BASE/'probes/nes-board205/source01/nes_rom_loader.sv');new=read(board/'nes_rom_loader.sv')
 assert transform('nes_rom_loader.sv',old)==new
 (out/'candidate.sv').write_text(new,encoding='utf8',newline='\n')
 (out/'reference.sv').write_text(old.replace('module nes_rom_loader #','module nes_rom_loader_reference #'),encoding='utf8',newline='\n')
 s=bench().replace('refdut.state=state;',"refdut.phase=16'b1<<state;")
 for n in ['tools/test_nes_directloader165.py','tools/test_nes_state165.py','tools/test_nes_drain165.py','tests/nes-functional/counter131_diff_tb.sv']:
  read(ROOT/n)
 # Completion update additionally enumerates every19-bit old count and both
 # completion inputs, including unreachable values, with a real advance edge.
 end='  $display("PASS STATE165 states=%0d sequences=%0d",checks,sequences);$finish;'
 ext='''  sequential=0;
  for(integer v=0;v<524288;v++)begin
   @(negedge mem_clk);clear_commands();
   dut.phase=16'b1<<8;refdut.phase=16'b1<<8;
   dut.remaining=1;refdut.remaining=1;dut.terminal=1;refdut.terminal=1;
   dut.fault=0;refdut.fault=0;dut.loaded_bytes=v;refdut.loaded_bytes=v;
   dut.count_complete=v[0];refdut.count_complete=v[0];
   @(posedge mem_clk);#0.01;
   if(dut.loaded_bytes!==refdut.loaded_bytes||dut.count_complete!==refdut.count_complete)$fatal(1,"COUNT206 exhaustive");
  end
  $display("PASS STATE165 states=%0d sequences=%0d exhaustive=524288",checks,sequences);$finish;'''
 s=replace(s,end,ext).replace('#10000000;','#20000000;').replace('#1000000;','#20000000;')
 (out/'bench.sv').write_text(s,encoding='utf8',newline='\n')
 def q(tool,args,label,negative=False):return run([str(a.questa_bin/(tool+'.exe')),*args],out,label,240,negative)
 q('vlib',['work'],'vlib');q('vlog',['-sv','candidate.sv','reference.sv','bench.sv'],'vlog')
 args=['-c','counter131_diff_tb','-do','onerror {quit -code 1}; run -all; quit -f']
 t=q('vsim',args,'equivalence');assert 'PASS STATE165 states=294912 sequences=1056 exhaustive=524288' in t
 wrong=new.replace("loaded_bytes==total-1'b1","loaded_bytes==total")
 (out/'wrong.sv').write_text(wrong,encoding='utf8',newline='\n');q('vlog',['-sv','wrong.sv'],'negative-compile');q('vsim',args,'negative',True)
 cases['loader']=dict(states=294912,sequences=1056,exhaustive=524288,wrong_terminal_rejected=True)
 r=dict(passed=True,cases=cases,source_pins=pins,script_sha256=sha(Path(__file__)),physical=False,scope=__doc__)
 (a.out/'result.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8',newline='\n');print(json.dumps(dict(passed=True,loader=cases['loader'])))
if __name__=='__main__':main()
