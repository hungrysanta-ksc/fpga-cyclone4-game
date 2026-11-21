"""Reuse the verified terminal plan snapshot across the SEAL display barrier."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base, out, mode):
    expected=('e8ed86b1c6cfc1e2c4784ff6987bafe28a0bd9ddee1034c0998bbc557b8ee66d'
              if mode=='overlap' else '033f7f93bafde2ed3c88f425dd2052c59c2723676ee09f4bf33877d9a81db1ea')
    assert digest(base/'obj-nes-100/firmware.stm')==expected
    out.mkdir(parents=True)
    name='nes_plan_service200.c'
    src=(base/name).read_text()
    src=once(src,'if(flags&2){p->finished=true;return true;}',
             '''if(flags&2){
   /* Only the CRC-checked empty descriptor, exact count and ended state
    * may arm EA. poll() completed any outstanding bulk receipt. */
   if(flags!=2)return fail(p,4);
   p->finished=true;return true;
  }''')
    if mode=='overlap':
        # Preserve the older table order and the live status check unless END
        # and its POP have returned within the previous output's lifetime.
        before='  if(!read509(p,rx,phase))return false;'
        start=src.index(before,src.index('bool nes_plan200_retire'))
        stop=src.index('   uint8_t cmd[7]',start)
        checked=src[start:stop]
        src=src[:start]+'''  unsigned accepted=0;
  if(sent || !next_complete){
'''+checked.replace('unsigned accepted=','accepted=').replace('  if(!sent){','  if(!sent) {')+'''   }
  }
  if(!sent){
'''+src[stop:]
        src=once(src,'nes_plan200_retire(struct nes_plan200 *p)','nes_plan200_retire(struct nes_plan200 *p,bool next_complete)')
        (out/name).write_text(src,newline='\n')
        for name,old,new in (
            ('nes_plan_service200.h','nes_plan200_retire(struct nes_plan200 *)','nes_plan200_retire(struct nes_plan200 *,bool)'),
            ('nes_native_runtime165.c','nes_plan200_retire(&s->plan)','nes_plan200_retire(&s->plan,r->state==NES_NATIVE165_COMPLETE)')):
            (out/name).write_text(once((base/name).read_text(),old,new),newline='\n')
        return
    begin=src.index(' uint8_t rx[20];bool sent=false;',src.index('bool nes_plan200_retire('))
    cmd=src.index('   uint8_t cmd[7]',begin)
    end=src.index('   sent=true;',cmd)
    send=src[cmd:end]
    rearm=src.index('   p->sent=0;',end)
    status=src[src.index('  if(!read509',begin):src.index('  if(!sent){',begin)]
    status=status.replace('phase','NES_PLAN215_REARM')
    src=src[:begin]+''' /* Only this owner can send another plan or EA. The FPGA rechecks
  * live state, generation, count, empty producer and CRC at EA itself.
  * Do not enter the next receiver decision until a checked E8 rearm. */
'''+send+''' uint8_t rx[20];
 for(unsigned i=0;i<p->poll_limit;i++){
  if(!p->guard(p->ctx))return fail(p,2);
'''+status+'''  if(rx[3]==1&&accepted==0){
'''+src[rearm:].replace('status215(p,phase,','status215(p,NES_PLAN215_REARM,')
    (out/name).write_text(src,newline='\n')
    if mode=='ready':
        name='nes_native_runtime165.c'
        src=once((base/name).read_text(),' return nes_cost474_pause(ctx,check,reason,progress);',
                 ''' /* END and its confirmed POP close the input side of this wait.
  * A pending SEAL can now poll E0 without another idle backoff. */
 if(reason==2 && r->state==NES_NATIVE165_COMPLETE)return check(ctx);
 return nes_cost474_pause(ctx,check,reason,progress);''')
        (out/name).write_text(src,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('out',type=Path)
    p.add_argument('mode',choices=('finish','ready','overlap'))
    prepare(**vars(p.parse_args()))
