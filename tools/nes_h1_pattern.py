# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for name in ('out','questa-bin','pattern'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();r=Path(__file__).resolve().parents[1];out=a.out.resolve()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER','')),'Use FLOAT wrapper'
 assert str(out).isascii() and not out.exists();out.mkdir()
 files=['src/nes/'+n+'.sv' for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern']]
 files+=['tests/nes-functional/h1_pattern_tb.sv']
 for name in files:shutil.copyfile(r/name,out/Path(name).name)
 shutil.copyfile(a.pattern,out/'h1-pattern.hex')
 m={'candidate':'NES-H1-PATTERN-033','sources':{n:sha(r/n) for n in files},'driver_sha256':sha(__file__),'pattern_sha256':sha(a.pattern),'phases':{},'runs':{}}
 def save():(out/'result.json').write_text(json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (out/(label+'.log')).open('wb') as log:
   cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=120)
  m['phases'][label]=cp.returncode;save();assert cp.returncode==0,label
 run('vlib',['work'],'vlib');run('vlog',['-sv',*[Path(n).name for n in files]],'compile')
 pattern=bytes(int(x,16) for x in (out/'h1-pattern.hex').read_text().split())
 for label,q,h,phase in [('q46_h12',23.280423,5.952381,1.1),('q20_h10',10,5,2.3),('q46_h20',23.280423,10,4.7)]:
  run('vsim',['-c','h1_pattern_tb',f'+QHALF={q}',f'+HHALF={h}',f'+HPHASE={phase}',f'+TRACE={label}.txt','-do','onerror {quit -code 1}; run -all; quit -f'],label)
  text=(out/(label+'.log')).read_text(errors='replace')
  assert 'PASS NES H1 PATTERN checks=5 readbytes=14336' in text and not re.search(r'\*\* (?:Fatal|Error):',text),label
  actual=bytes(map(int,(out/(label+'.txt')).read_text().split()))
  assert actual==pattern*2+pattern[:2048]
  (out/(label+'.bin')).write_bytes(actual)
  m['runs'][label]={'checks':5,'bytes':len(actual),'exact':True,'queue_period_ns':q*2,'host_period_ns':h*2,'phase_ns':phase,'sha256':sha(out/(label+'.bin'))};save()
 m['passed']=True;save();print(json.dumps(m['runs'],indent=2))
if __name__=='__main__':main()
