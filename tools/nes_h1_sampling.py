# SPDX-License-Identifier: MIT
# 044: make the stable address-change predicate explicit per bit.
from pathlib import Path
from nes_h1_qualified import frontend as qualified_frontend,transport,pattern,boundary as old_boundary,source as old_source,session as old_session
ROOT=Path(__file__).resolve().parents[1]
def frontend():
 s=qualified_frontend()
 old='(tracked_read && qualified_read && addr_sync!=read_address)'
 new='(tracked_read && qualified_read && |((addr_sync^read_address)&(addr_previous^read_address)))'
 assert s.count(old)==1
 return s.replace(old,new).replace("8'h43","8'h44").replace('// 043 bundled bus qualification.', '// 044 stable changed-bit qualification.').replace('docs/nes-h1-qualified-contract.md','docs/nes-h1-sampling-contract.md')
def boundary():return old_boundary().replace("command==8'hf1 ?8'h43:","command==8'hf1 ?8'h44:")
def source():return old_source().replace('NES-H1-QUALIFIED-043','NES-H1-SAMPLING-044').replace('nes-h1-last-043.txt','nes-h1-last-044.txt')
def session():return old_session().replace('if(id!=0x43)','if(id!=0x44)')
def materialize(out):
 for name,fn in [('nes_snes_frontend',frontend),('nes_transport',transport),('nes_h1_pattern',pattern),('nes_h1_board_bus',boundary)]:
  (out/(name+'.sv')).write_text(fn(),newline=chr(10))

def main():
 import argparse,json,subprocess,sys
 from nes_h1_spi import sha
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/prepare_nes_h1_firmware.py'),'--out',str(a.out),'--upstream',str(a.upstream)],check=True)
 (a.out/'src/nes_h1_stm32.c').write_text(source(),newline='\n');(a.out/'src/nes_h1_session.c').write_text(session(),newline='\n')
 (a.out/'sampling-preparation.json').write_text(json.dumps({'candidate':'NES-H1-SAMPLING-044','protocol_hex':'44','files':{n:sha(a.out/'src'/n) for n in ('nes_h1_stm32.c','nes_h1_session.c')}},indent=2))
if __name__=='__main__':main()
