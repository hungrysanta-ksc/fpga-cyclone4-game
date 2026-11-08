"""Share actual empty-query ownership with the adjacent map sender."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha

def prepare(base,out,clear_failure=False):
    proof=json.loads(Path('analysis/pair687-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/firmware.stm')==proof['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_native_sink165.c';s=p.read_text()
    s=once(s,'pair=pairable && !adjacent && count==3 && !s->plan->bulk_pending;',
        '''/* Only the real checked-empty query lends its next slot. A
   * receipt-only fast path cannot manufacture producer query credit. */
  pair=pairable && count==3 && s->map_pair683;
  s->map_pair683=false;''')
    if clear_failure:
        s=once(s,'if(!packet(s,(early==1||adjacent)?24:2,2,first*64,p->map+first*64,count*64))return false;',
            'if(!packet(s,(early==1||adjacent)?24:2,2,first*64,p->map+first*64,count*64)){s->map_pair683=false;return false;}')
    p.write_text(s,newline='\n')
    p=out/'src/nes_plan_service200.c';s=p.read_text()
    s=once(s,'}else if(mode!=NES_FINAL553)return complete485(p);',
        '''}else if(mode!=NES_FINAL553){
   /* No descriptor was returned. Complete any earlier owned receipt;
    * a failed completion still fails the enclosing map send. This bit
    * is consumed/cleared by map527, never a bank or display ACK. */
   if(mode==NES_MAP553)p->sink->map_pair683=true;
   return complete485(p);
  }''')
    p.write_text(s,newline='\n')
    (out/'recipe688.json').write_text(json.dumps(dict(base=proof['firmware'],clear_failure=clear_failure,
        changed={n:sha(out/'src'/n) for n in ('nes_native_sink165.c','nes_plan_service200.c')},
        rule='Only checked empty E8; bounded adjacent pair; receipt-only path never grants; no persistent RAM added.'),indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--clear-failure',action='store_true')
    a=p.parse_args();prepare(a.base,a.out,a.clear_failure)
