# SPDX-License-Identifier: MIT
"""Actual queued SPI + unchanged SNES bus, then C replay. Not CPU/game/FIT proof."""
from pathlib import Path
import argparse,json,os,re,shutil,subprocess,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['out','questa-bin','gcc','arm-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 baseline=ROOT.parent/'probes/nes-checkstate181/evidence/map01'
 inputs={}
 for n in ['nes_domain_reset124.sv','nes_sink_bridge165.sv','nes_sink_bus165.sv','sink-program.hex']:
  b=(baseline/n).read_bytes();inputs[n]=sha(baseline/n)
  if n=='nes_sink_bridge165.sv':
   assert b.count(b'nes_sink_spi165 endpoint')==1;b=b.replace(b'nes_sink_spi165 endpoint',b'nes_sink_queue184 endpoint')
  (a.out/n).write_bytes(b)
 sources=['src/nes/diagnostic/nes_sink_queue184.sv','src/nes/firmware/nes_sink_window184.c','src/nes/firmware/nes_sink_window184.h','tests/nes-functional/sink_window184_tb.sv','tests/nes-functional/sink_window184_host.c','tools/test_nes_window184.py']
 for n in sources:shutil.copyfile(ROOT/n,a.out/Path(n).name)
 env=os.environ.copy();env['PATH']=str(a.gcc.parent)+os.pathsep+env.get('PATH','')
 def run(cmd,name,folder=a.out):
  with (folder/(name+'.log')).open('wb') as f:
   r=subprocess.run(list(map(str,cmd)),cwd=folder,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW)
  text=(folder/(name+'.log')).read_text(errors='replace')
  assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',text),text[-4500:]
  return text
 run([a.questa_bin/'vlib.exe','work'],'vlib')
 run([a.questa_bin/'vlog.exe','-sv','nes_domain_reset124.sv','nes_sink_queue184.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv','sink_window184_tb.sv'],'vlog')
 run([a.gcc,'-std=c11','-O2','-Wall','-Wextra','-Werror','sink_window184_host.c','nes_sink_window184.c','-o','host.exe'],'gcc')
 cases=[]
 for tag,phase,wrap in [('normal',0,0),('phase',3.5,0),('wrap',0,1)]:
  d=a.out/tag;d.mkdir()
  s=run([a.questa_bin/'vsim.exe','-c','work.sink_window184_tb',f'-gPHASE={phase}',f'-gWRAP={wrap}','-do','onerror {quit -code 1}; run -all; quit -f'],tag)
  m=re.search(r'PASS WINDOW184 calls=(\d+) wirebytes=(\d+) checks=(\d+) packets=33',s);assert m,s[-4500:]
  shutil.copyfile(a.out/'transactions.txt',d/'transactions.txt')
  h=run([a.out/'host.exe',d/'transactions.txt',wrap],tag+'-host')
  assert 'PASS WINDOW184 C' in h
  cases.append(dict(name=tag,calls=int(m[1]),wire_bytes=int(m[2]),checks=int(m[3]),host=h.strip(),trace_sha256=sha(d/'transactions.txt')))
 run([a.arm_bin/'arm-none-eabi-gcc.exe','-std=c11','-mcpu=cortex-m4','-mthumb','-Os','-Wall','-Wextra','-Werror','-fstack-usage','-c','nes_sink_window184.c','-o','window.o'],'arm')
 size=run([a.arm_bin/'arm-none-eabi-size.exe','window.o'],'arm-size')
 result=dict(passed=True,cases=cases,inputs=inputs,public_sources={n:sha(ROOT/n) for n in sources},stack=(a.out/'window.su').read_text(),arm_size=size,scope=__doc__,new_firmware=False,new_fit=False,new_package=False)
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf8');print(json.dumps(result))
if __name__=='__main__':main()
