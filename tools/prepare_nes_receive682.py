"""One checked input-credit path; useful READ/POP replaces an empty polling pause."""
import argparse,json,shutil
from pathlib import Path
from nes_raw506 import once,sha


def prepare(base,out,progress,credit=False,batch=False,read=False):
    proof=json.loads(Path('analysis/late681-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/firmware.stm')==proof['zero_ARM']['firmware']
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log','*.json'))
    p=out/'src/nes_native_runtime165.c';s=p.read_text()
    begin=s.index('static bool wait634(');end=s.index('static bool finish_bg549(',begin)
    body='''static bool wait634(void *ctx,bool (*check)(void *),unsigned reason,bool progress){
 struct nes_native_runtime165 *s=ctx;
 struct nes_native165 *r=s->receiver;
 if(reason==3 || reason==4){
  if(r->state==NES_NATIVE165_COMMITTED)s->prefetch_left=7;
  if(reason==3)reason=2;
 }
 if(reason==4 || (s->prefetch_left && reason==2 && !progress)){
  if(!check(ctx))return false;
  nes_native165_consumed(r);
  if(s->prefetch_left && r->state!=NES_NATIVE165_COMPLETE){
   uint16_t before=r->next_token;
   if(!nes_native165_poll(r,transfer,s))return fail(s,NES_RUNTIME165_RECEIVE);
   /* Only a CRC-checked READ and confirmed POP spend a geometry credit.
    * Empty STATUS and failed/partial IO cannot consume the seven-block cap. */
   if(r->next_token!=before){--s->prefetch_left;@PROGRESS@}
  }
  if(reason==4)return check(ctx);
 }
 /* The caller checks output credit/final identity again before each input
  * transaction. Input progress never acknowledges display or permits COMMIT. */
 return nes_cost474_pause(ctx,check,reason,progress);
}
'''.replace('@PROGRESS@','progress=true;' if progress else '')
    if credit:
        assert progress
        body=body.replace(' if(reason==3 || reason==4){', ' /* A checked FINISH owns no receiver pixels or ROM reader. Only an\n  * output wait with no credit progress may borrow the shared SPI. */\n bool input_wait=reason<=1 && s->plan.finished && !progress;\n if(input_wait || reason==3 || reason==4){').replace('s->prefetch_left && reason==2 && !progress', 's->prefetch_left && (input_wait || (reason==2 && !progress))')
    if batch:
        assert credit and progress
        body=body.replace('  if(s->prefetch_left && r->state!=NES_NATIVE165_COMPLETE){','  while(s->prefetch_left && r->state!=NES_NATIVE165_COMPLETE){')
        body=body.replace('   if(r->next_token!=before){--s->prefetch_left;progress=true;}', '   if(r->next_token==before)break;\n   --s->prefetch_left;progress=true;\n   /* Only sealed output may defer its next E0 until this bounded input\n    * batch ends. Every READ/POP retains CRC, identity and STOP checks. */\n   if(reason!=2)break;\n   if(!check(ctx))return false;')
        body=body.replace('The caller checks output credit/final identity again before each input\n  * transaction.', 'The caller checks output credit/final identity before/after each bounded\n  * input batch.')
    p.write_text(s[:begin]+body+s[end:],newline='\n')
    if read:
        assert batch
        q=out/'src/nes_native165.c';v=q.read_text()
        v=once(v,'uint8_t tx[259]={0},rx[259];frame(tx,0xd0,0,0);','uint8_t tx[259],rx[259];')
        v=once(v,'else if(!fn(ctx,tx,rx,8))return fail(s,21);','else {frame(tx,0xd0,0,0);if(!fn(ctx,tx,rx,8))return fail(s,21);}')
        q.write_text(v,newline='\n')
    (out/'recipe682.json').write_text(json.dumps(dict(base=proof['zero_ARM']['firmware'],useful_input_progress=progress,finished_plan_credit=credit,sealed_input_batch=batch,lazy_read_header=read,source=sha(p)),indent=2)+'\n',newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--base',type=Path,required=True);p.add_argument('--out',type=Path,required=True);p.add_argument('--progress',action='store_true');p.add_argument('--credit',action='store_true');p.add_argument('--batch',action='store_true');p.add_argument('--read',action='store_true');a=p.parse_args()
    prepare(a.base,a.out,a.progress,a.credit,a.batch,a.read)
