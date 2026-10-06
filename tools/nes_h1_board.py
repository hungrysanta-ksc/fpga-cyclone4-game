# SPDX-License-Identifier: MIT
from pathlib import Path
import argparse,hashlib,json,os,re,shutil,subprocess
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser()
 for name in ('out','questa-bin','build'):p.add_argument('--'+name,type=Path,required=True)
 a=p.parse_args();r=Path(__file__).resolve().parents[1];out=a.out.resolve()
 assert re.fullmatch(r'18000@(?:localhost|127\.0\.0\.1)',os.environ.get('SALT_LICENSE_SERVER','')),'Use FLOAT wrapper'
 assert str(out).isascii() and not out.exists();out.mkdir()
 files=['src/nes/'+n+'.sv' for n in ['nes_packet_queue_ram','nes_packet_cdc_ram','nes_host_stage','nes_snes_frontend','nes_transport','nes_h1_pattern_producer','nes_h1_pattern','nes_h1_board_bus']]
 files+=['tests/nes-functional/h1_board_tb.sv']
 for name in files:shutil.copyfile(r/name,out/Path(name).name)
 for name in ['h1-pattern.hex','h1-program.hex','program-full.hex']:shutil.copyfile(a.build/name,out/name)
 m={'candidate':'NES-H1-BOARD-034','sources':{n:sha(r/n) for n in files},'inputs':{n:sha(out/n) for n in ['h1-pattern.hex','h1-program.hex','program-full.hex']},'driver_sha256':sha(__file__),'phases':{},'scope':'Actual84MHz boundary RTL, injected clock/PLL lock; no analogPLL model or physical board execution'}
 def save():(out/'result.json').write_text(json.dumps(m,indent=2)+'\n')
 def run(tool,args,label):
  with (out/(label+'.log')).open('wb') as log:
   cp=subprocess.run([str(a.questa_bin/(tool+'.exe')),*args],cwd=out,stdout=log,stderr=subprocess.STDOUT,timeout=180)
  m['phases'][label]=cp.returncode;save();assert cp.returncode==0,label
 run('vlib',['work'],'vlib');run('vlog',['-sv',*[Path(n).name for n in files]],'compile')
 run('vsim',['-c','h1_board_tb','-do','onerror {quit -code 1}; run -all; quit -f'],'board')
 text=(out/'board.log').read_text(errors='replace')
 assert 'PASS NES H1 BOARD checks=6 rombytes=65536 payloadbytes=8192' in text and not re.search(r'\*\* (?:Fatal|Error):',text),'board.log'
 rows=[list(map(int,s.split())) for s in (out/'board-bytes.tsv').read_text().splitlines()]
 rom=bytes(int(s,16) for s in (out/'program-full.hex').read_text().split())
 patterns=bytes(int(s,16) for s in (out/'h1-pattern.hex').read_text().split())
 assert bytes(v for kind,addr,v in rows if kind==1)==rom
 assert bytes(v for kind,addr,v in rows if kind==2)==patterns+patterns[:2048]
 m.update(passed=True,checks=6,rombytes=65536,payloadbytes=8192);save();print(json.dumps(m['phases']))
if __name__=='__main__':main()
