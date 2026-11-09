"""Move bounded input ownership from generic SPI completion to SEAL barrier."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out):
    expected='a212093bf4c6ff400df6406f275cca87bd290a90c4ff2c01d2ff9f57d0273cc7'
    assert sha(base/'src/obj-nes-100/firmware.stm')==expected
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    changed={}
    p=out/'src/nes_native_runtime165.c';s=p.read_text()
    s=once(s,' bool seal=opcode==0xe1&&n>=2&&tx[1]==3;\n','')
    s=once(s,' if(ok&&seal&&s->receiver->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;\n','')
    p.write_text(s,newline='\n');changed[p.name]=sha(p)
    p=out/'src/nes_sink_window184.c';s=p.read_text()
    s=once(s,' return send(s,p,n)&&nes_window184_drain(s,ack);',
        ''' /* The completed SEAL transaction owns no further output payload.
  * Borrow input SPI before the first E0, then require the unchanged complete
  * final identity. Failed send/STOP never enter input; input never commits. */
 if(!send(s,p,n))return false;
 if(p[0]==3 && !wait474(s,3,false))return false;
 return nes_window184_drain(s,ack);''')
    p.write_text(s,newline='\n');changed[p.name]=sha(p)
    (out/'recipe686.json').write_text(json.dumps(dict(base=expected,changed=changed,
        boundary='successful SEAL send -> bounded reason3 input -> unchanged E0 full final identity; no generic SPI opcode sniff/rearm'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();prepare(a.base,a.out)
