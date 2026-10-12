# SPDX-License-Identifier: MIT
"""Replay pinned concurrent C/SNES packets through the real SPI and SNES RTL buses."""
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
ROOT=Path(__file__).resolve().parents[1]
RTL=['nes_domain_reset124.sv','nes_sink_spi165.sv','nes_sink_bus165.sv','nes_sink_bridge165.sv']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for n in ['evidence','out','questa-bin','gcc','arm-bin']:p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();assert os.environ.get('SALT_LICENSE_SERVER')=='18000@localhost'
 a.out.mkdir(parents=True,exist_ok=False)
 manifest=json.loads((a.evidence/'evidence-manifest.json').read_bytes());inputs={}
 def pinned(n):
  f=a.evidence/n;assert sha(f)==manifest[n],n;inputs[n]=sha(f);return f.read_bytes()
 packets=[];acks=[]
 for name,count in [('normal',137),('stop',90)]:
  for i in range(1,count+1):
   b=pinned(f'sink01/{name}/req-{i:04}.bin');ack=pinned(f'sink01/{name}/ack-{i:04}.bin')
   assert 16<=len(b)<=256 and len(ack)==12
   packets.append(b);acks.append(ack)
 (a.out/'sink-program.hex').write_bytes(pinned('sink01/client/sink-program.hex'))
 (a.out/'packets.hex').write_text(''.join(f'{v:02x}\n' for b in packets for v in b+bytes(256-len(b))))
 (a.out/'acks.hex').write_text(''.join(f'{v:02x}\n' for b in acks for v in b))
 (a.out/'lengths.hex').write_text(''.join(f'{len(b):03x}\n' for b in packets))
 (a.out/'vectors.txt').write_text(''.join(str(len(b))+' '+b.hex(' ')+' '+c.hex(' ')+'\n' for b,c in zip(packets,acks)))
 sources=['src/nes/diagnostic/'+n for n in RTL]+['tests/nes-functional/sink_bridge165_tb.sv','tests/nes-functional/sink_spi165_host.c','src/nes/firmware/nes_sink_spi165.c','src/nes/firmware/nes_sink_spi165.h','tools/test_nes_sink_bridge165.py']
 for n in sources:shutil.copy2(ROOT/n,a.out/Path(n).name)
 def run(exe,args,label):
  with (a.out/(label+'.log')).open('wb') as f:r=subprocess.run([str(exe),*map(str,args)],cwd=a.out,stdout=f,stderr=subprocess.STDOUT,timeout=240)
  s=(a.out/(label+'.log')).read_text(errors='replace');assert r.returncode==0 and not re.search(r'\*\* (Error|Fatal):',s),s[-5000:];return s
 def q(exe,args,label):return run(a.questa_bin/(exe+'.exe'),args,label)
 q('vlib',['work'],'vlib');q('vlog',['-sv',*RTL,'sink_bridge165_tb.sv'],'vlog')
 fw=ROOT/'src/nes/firmware'
 run(a.gcc,['-std=c11','-Wall','-Wextra','-Werror','-O2','-I',fw,'sink_spi165_host.c','nes_sink_spi165.c','-o','host.exe'],'gcc')
 cases=[]
 for phase in [0,3.5]:
  tag='phase'+str(phase);s=q('vsim',['-c','work.sink_bridge165_tb',f'-gPHASE={phase}','-do','onerror {quit -code 1}; run -all; quit -f'],tag)
  m=re.search(r'PASS SINKBRIDGE165 packets=(\d+) bytechecks=(\d+) wirebytes=(\d+)',s);assert m,s[-5000:]
  shutil.copy2(a.out/'transactions.txt',a.out/(tag+'.transactions.txt'))
  c=run(a.out/'host.exe',['transactions.txt','vectors.txt'],tag+'-host')
  assert 'negatives=17' in c
  cases.append(dict(phase_ns=phase,packets=int(m[1]),byte_checks=int(m[2]),wire_bytes=int(m[3]),c_result=c.strip(),trace_sha256=sha(a.out/'transactions.txt')))
 arm=a.arm_bin/'arm-none-eabi-gcc.exe'
 flags=['-mcpu=cortex-m4','-mthumb','-Os','-std=c11','-Wall','-Wextra','-Werror','-fstack-usage','-ffunction-sections','-I',fw]
 run(arm,[*flags,'-c','nes_sink_spi165.c','-o','sink.o'],'arm')
 (a.out/'layout.c').write_text('#include "nes_sink_spi165.h"\nchar context_size[sizeof(struct nes_sink_spi165)];\n')
 run(arm,[*flags,'-c','layout.c','-o','layout.o'],'arm-layout')
 size=run(a.arm_bin/'arm-none-eabi-size.exe',['sink.o','layout.o'],'arm-size')
 result=dict(passed=True,cases=cases,arm_size=size.strip(),stack=(a.out/'sink.su').read_text(),inputs=inputs,public_sources={n:sha(ROOT/n) for n in sources},scope='SPI/SNES RTL transaction replay + actual C adapter, not concurrent CPU model or physical board. Parent integration/full-link/fit/timing pending.')
 (a.out/'result.json').write_text(json.dumps(result,indent=2)+'\n');print('PASS sink SPI/SNES bridge + C adapter')
if __name__=='__main__':main()
