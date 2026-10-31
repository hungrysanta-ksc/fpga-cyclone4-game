# SPDX-License-Identifier: MIT
"""Share E8 transfer/header/CRC validation between plan progress and retirement."""
import argparse,json
from pathlib import Path
from nes_raw506 import once,sha
def prepare(a):
    a.out.mkdir(parents=True,exist_ok=False);(a.out/'patch').mkdir()
    n='nes_plan_service200.c';src=a.base/n;s=src.read_text()
    helper='''static bool read509(struct nes_plan200 *p,uint8_t rx[20],uint8_t phase){
 uint8_t tx[20]={0xe8};
 /* The caller already ran its phase-specific state/STOP guard. */
 if(!p->transfer(p->ctx,tx,rx,20))return fail(p,3);
 if(rx[1]!=0xd7||rx[2]!=4)return status215(p,phase,NES_PLAN215_HEADER,rx);
 if(phase<=NES_PLAN215_FINISH&&rx[18])return status215(p,phase,NES_PLAN215_RESERVED,rx);
 if(crc8(rx+1,18)!=rx[19])return status215(p,phase,NES_PLAN215_CRC,rx);
 return true;
}
'''
    s=once(s,'static bool valid(',helper+'static bool valid(')
    s=once(s,''' uint8_t tx[20]={0xe8},rx[20];if(!valid(p))return false;
 if(!p->transfer(p->ctx,tx,rx,20))return fail(p,3);
 if(rx[1]!=0xd7||rx[2]!=4)return status215(p,phase,NES_PLAN215_HEADER,rx);
 if(rx[18])return status215(p,phase,NES_PLAN215_RESERVED,rx);
 if(crc8(rx+1,18)!=rx[19])return status215(p,phase,NES_PLAN215_CRC,rx);''',''' uint8_t rx[20];if(!valid(p))return false;
 if(!read509(p,rx,phase))return false;''')
    s=once(s,'uint8_t tx[20]={0xe8},rx[20];bool sent=false;','uint8_t rx[20];bool sent=false;')
    s=once(s,'''  if(!p->transfer(p->ctx,tx,rx,20))return fail(p,3);
  uint8_t phase=sent?NES_PLAN215_REARM:NES_PLAN215_RETIRE;
  if(rx[1]!=0xd7||rx[2]!=4)return status215(p,phase,NES_PLAN215_HEADER,rx);
  if(crc8(rx+1,18)!=rx[19])return status215(p,phase,NES_PLAN215_CRC,rx);''','''  uint8_t phase=sent?NES_PLAN215_REARM:NES_PLAN215_RETIRE;
  if(!read509(p,rx,phase))return false;''')
    dst=a.out/'patch'/n;dst.write_text(s,encoding='utf8',newline='\n')
    r=dict(base_SHA256=sha(src),patch_SHA256=sha(dst),scope=__doc__,FPGA_changed=False,SNES_changed=False)
    (a.out/'prepare.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
if __name__=='__main__':
    p=argparse.ArgumentParser()
    for n in ['base','out']:p.add_argument('--'+n,type=Path,required=True)
    prepare(p.parse_args())
