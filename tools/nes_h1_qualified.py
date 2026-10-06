# SPDX-License-Identifier: MIT
"""043 qualified bundled bus plus a single registered first-error event."""
from pathlib import Path
from nes_h1_edge import transport,pattern,boundary as edge_boundary,source as edge_source,session as edge_session
ROOT=Path(__file__).resolve().parents[1]
def frontend():return (ROOT/'src/nes/nes_snes_frontend_qualified.sv').read_text()
def boundary():return edge_boundary().replace("command==8'hf1 ?8'h41:","command==8'hf1 ?8'h43:")
def source():return edge_source().replace('NES-H1-EDGE-041','NES-H1-QUALIFIED-043').replace('nes-h1-last-041.txt','nes-h1-last-043.txt')
def session():return edge_session().replace('if(id!=0x41)','if(id!=0x43)')
def materialize(out):
 for name,fn in [('nes_snes_frontend',frontend),('nes_transport',transport),('nes_h1_pattern',pattern),('nes_h1_board_bus',boundary)]:
  (out/(name+'.sv')).write_text(fn(),newline='\n')


def main():
 import argparse,json,subprocess,sys
 from nes_h1_spi import sha
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--upstream',type=Path,required=True);a=p.parse_args()
 subprocess.run([sys.executable,'-B','-X','utf8',str(ROOT/'tools/prepare_nes_h1_firmware.py'),'--out',str(a.out),'--upstream',str(a.upstream)],check=True)
 (a.out/'src/nes_h1_stm32.c').write_text(source(),newline='\n');(a.out/'src/nes_h1_session.c').write_text(session(),newline='\n')
 (a.out/'qualified-preparation.json').write_text(json.dumps({'candidate':'NES-H1-QUALIFIED-043','protocol_hex':'43','files':{n:sha(a.out/'src'/n) for n in ('nes_h1_stm32.c','nes_h1_session.c')}},indent=2))
if __name__=='__main__':main()
