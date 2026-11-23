"""Borrow checked output waits for source input after planner ownership ends."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

import nes_supply948 as prior
from nes_credit946 import ROM, base, once, sha

SOURCE=prior.work('half_page')
HELD={'held_base':'half_page','held_credit':'credit','held_large':'large','held_pair':'pair','held_diff':'diff','held_stage':'stage','held_history':'history','held_idle':'idle','held_report':'report'}
MODES=('large','accepted','credit','drain','finish','head','pair','diff','stage','history','idle','report',*HELD)


def work(mode):
    if mode=='held_base':
        return SOURCE
    mode=HELD.get(mode,mode)
    return SOURCE.parent.parent/'nes-input949'/mode


def prepare(mode):
    if mode in HELD:
        raise ValueError('reuse the linked control or experimental binary')
    expected=json.loads((Path(__file__).resolve().parents[1]/'analysis/supply948-results.json').read_bytes())
    assert sha(SOURCE/'link/src/obj-nes-100/firmware.stm')==expected['cases']['warm1']['half_page']['sha256']
    link=work(mode)/'link'
    shutil.copytree(SOURCE/'link',link)
    if mode in ('accepted','large'):
        f=link/'src/nes_plan_service200.c'
        s=f.read_text()
        a='bool follows_oam=(!p->bank_history || p->window->last[1]==4);'
        s=once(s,a,'bool follows_oam=(!p->bank_history || p->window->last[1]==4 || (p->pressure&2));')
        if mode=='accepted':
            s=once(s,'&& d[1] && d[3] && !p->window->wait','&& d[1] && (d[3] || (p->pressure&2)) && !p->window->wait')
    elif mode=='head':
        f=link/'src/nes_plan_service200.c'
        s=f.read_text()
        # At END, sample the next physical bank while the previous queue ACK
        # is in flight. The old target is still checked before any new E1.
        s=once(s,'if(p->bank_history==2 && !complete485(p))',
               'if(p->bank_history==2 && !(p->ending && p->bulk[1]) && !complete485(p))')
        s=once(s,'if(phase==NES_PLAN215_FINISH&&!complete485(p))',
               'if(phase==NES_PLAN215_FINISH && !(p->ending && rx[7]) && !complete485(p))')
        pivot='   if(!complete485(p))return false;\n  }else if(mode!=NES_FINAL553'
        s=once(s,pivot,'   if(mode==NES_FINAL553 && p->bulk[1])continue;\n'+pivot)
    elif mode=='drain':
        f=link/'src/nes_plan_service200.c'
        s=once(f.read_text(),'for(unsigned i=0;i<12;i++)',
               'for(unsigned i=0;i<((p->pressure&2)?1u:12u);i++)')
    elif mode=='finish':
        f=link/'src/nes_plan_service200.c'
        s=once(f.read_text(),'p->finished=true;return true;',
               """p->finished=true;
    if((p->pressure&2) && p->bulk[1] && p->window && p->window->wait &&
       !p->window->wait(p->ctx,p->window->guard,4,false))return fail(p,2);
    return true;""")
    else:
        f=link/'src/nes_native_runtime165.c'
        s=f.read_text()
        at=' bool input_wait=reason<=1 && s->plan.finished && !progress;'
        s=once(s,at,''' /* While the SNES owns a confirmed OBJ, retire at most one input
  * block before rechecking queue credit. COMMIT still follows final ACK/EA. */
 if(reason==1 && !progress && s->plan.ending && (s->plan.pressure&2) &&
    s->transport.last[0]==7 && s->transport.last[1]==1)reason=4;
'''+at)
    if mode=='pair':
        s=once(s,'if(reason==1 && !progress', 'bool pair=(reason==1);\n if(reason==1 && !progress')
        s=once(s,'if(reason!=2)break;', '''if(reason!=2){
    if(reason!=4 || !pair || !r->ready183)break;
    pair=false;
   }''')
    if mode=='diff':
        f.write_text(s,newline='\n')
        f=link/'src/nes_native_sink165.c'
        s=f.read_text()
        s=once(s,'*map,int same)', '*map,int same,uint32_t diff)')
        s=once(s,'    uint32_t diff=h->keep ? compare869(h,map) : UINT32_MAX;\n','')
        marker=' if(!packet(s,3,0,0,descriptor,sizeof descriptor))return false;\n unsigned bank=r->target;'
        s=once(s,marker,''' const mapword869 *right=(const mapword869 *)(p->map+2048);
 bool map_same=!((uint32_t)(p->map_dirty>>32)&0x7fffff);
 uint32_t prior_diff=maps869.keep && !map_same ? compare869(&maps869,right) : UINT32_MAX;
'''+marker)
        s=once(s,'''remember869(&maps869,(const mapword869 *)(p->map+2048),
             !((uint32_t)(p->map_dirty>>32)&0x7fffff))''',
               'remember869(&maps869,right,map_same,prior_diff)')
    if mode=='idle':
        marker='reason==2 && (r->state==NES_NATIVE165_COMPLETE || r->state==NES_NATIVE165_IDLE) ? 0 :'
        s=once(s,marker,'''reason==2 && r->state==NES_NATIVE165_COMPLETE ? 8u*8u*32u :
      reason==2 && r->state==NES_NATIVE165_IDLE ? 0 :''')
    if mode in ('stage','history','idle','report'):
        f.write_text(s,newline='\n')
        f=link/'src/nes_native_sink165.c'
        s=f.read_text()
        begin=s.index('static void __attribute__((noinline)) commit635')
        end=s.index('bool nes_sink212_seal',begin)
        assert 's->ack635[bank]=s->serial;' in s[begin:end]
        s=s[:begin]+s[end:]
        pivot=' if(reuse && !send635(s,p,r->target))return false;'
        s=once(s,pivot,pivot+'''
 /* Old identity no longer owns the buffer. Publish only after final ACK. */
 if(!same){
  s->ack635[0]=s->ack635[1]=0;
  memcpy(s->palette635,p->cgram,512);
  memcpy(s->tail635,p->oam+112,432);
 }''')
        s=once(s,'commit635(s,p,bank,same);','s->ack635[bank]=s->serial;')
    if mode=='history':
        # All ordinary heads already own their transmitted bytes. Temporarily
        # invalidate the optional cache; only a checked SEAL may publish it.
        start=s.index('static void remember869')
        end=s.index('static unsigned right_packet869',start)
        body=s[start:end].replace('static void remember869','static bool prepare_map949')
        body=once(body,'h->differing=0;\n        return;', 'h->differing=0; h->keep=0;\n        return true;')
        body=once(body,'128)) return;', '128)) return false;')
        body=once(body,'h->differing=diff; h->keep=1;', 'h->differing=diff; return true;')
        s=s[:start]+body+s[end:]
        remember='''remember869(&maps869,(const mapword869 *)(p->map+2048),
             !((uint32_t)(p->map_dirty>>32)&0x7fffff));'''
        s=once(s,remember,'maps869.keep=map_ok;')
        pivot=' if(!packet(s,3,0,0,descriptor,sizeof descriptor))return false;\n unsigned bank=r->target;'
        s=once(s,pivot,' bool map_ok='+remember.replace('remember869','prepare_map949')+'\n'+pivot)
    if mode=='report':
        f.write_text(s,newline='\n')
        budget=link/'src/nes_budget210.c'
        cost=once(budget.read_text(),'unsigned char mode900;', 'unsigned char mode900,report_bulk949;')
        cost=once(cost,'if(native_runtime165.plan.bulk_valid)memcpy',
                  'if(native_runtime165.plan.bulk_valid || report_bulk949)memcpy')
        budget.write_text(cost,newline='\n')
        f=link/'src/nes_native_runtime165.c'
        s=f.read_text()
        begin=s.index('  r->ready183 &= s->sink.displayed;')
        end=s.index(' }else if(r->state!=NES_NATIVE165_COMMITTED)',begin)
        code=s[begin:end]
        pivot='bool nes_runtime165_step(struct nes_native_runtime165 *s){'
        s=s[:begin]+'  if(!complete949(s,r))return false;\n'+s[end:]
        s=once(s,pivot,'''extern unsigned char report_bulk949;
static bool complete949(struct nes_native_runtime165 *s,struct nes_native165 *r){
'''+code+' return true;\n}\n'+pivot)
        first=s.index('  nes_budget210_display(nes_trace166.last_display_tick,s->video);')
        last=s.index(' }\n return true;',first)
        # budget_display reads the old video and descriptor. EA clears the valid
        # flag, but leaves its bytes intact until the next planner starts.
        s=s[:first]+'''  report_bulk949=s->plan.bulk_valid;
  bool retired=nes_plan200_retire(&s->plan);
  bool input_ok=true;
  if(retired){
   nes_native165_consumed(r);
   if(r->state==NES_NATIVE165_COMPLETE)input_ok=complete949(s,r);
  }
  nes_budget210_display(nes_trace166.last_display_tick,s->video);
  report_bulk949=0;
  if(!retired)return fail(s,NES_RUNTIME165_DISPLAY);
  if(!input_ok)return false;
'''+s[last:]
    f.write_text(s,newline='\n')


def replay(temp,mode,phase,cache,profile=False):
    from contextlib import ExitStack
    from nes_credit946 import work as credit_work
    from replay_nes_strip869 import dense
    from test_nes_receive649 import admission
    with ExitStack() as stack:
        chain=base.prev.chain
        arm=work(mode)
        rom=ROM
        if mode=='reference935':
            arm,rom=chain.fit_arm(),chain.output('bounded')
        elif mode=='reference946':
            arm=credit_work('objguard')
        stack.enter_context(patch.object(chain,'output',lambda _:rom))
        if mode in HELD or mode.startswith('reference'):
            rt=dense.joint.Runtime
            stack.enter_context(patch.object(rt,'offer_input',admission(rt.offer_input)))
        rows=[]
        if profile:
            from unicorn import UC_HOOK_CODE
            rt=dense.joint.Runtime
            init=rt.__init__
            def attach(cpu,*args):
                init(cpu,*args)
                def hook(u,pc,size,user):
                    if cpu.generation==909 and cpu.input_generation==910:
                        rows.append((round(cpu.clock),user))
                names=('receipt_matches','e0900','nes_native165_consumed','nes_cost471_phase',
                    'nes_resident211_commit','nes_budget210_display','nes_plan200_retire',
                    'nes_native165_prepare','nes_native165_poll','nes_native913_classify',
                    'remember869','page905','nes_cost471_now','nes_budget210_frame','crc_xmodem_block','check','native_service165')
                for name in names:
                    pc=cpu.syms.get(name)
                    if pc:
                        cpu.u.hook_add(UC_HOOK_CODE,hook,name,begin=pc,end=pc)
            stack.enter_context(patch.object(rt,'__init__',attach))
        tag='949'+mode+('audit' if profile else '')
        chain.replay(temp,'final',phase,cache,'bounded',work_arm=arm,tag=tag)
        if profile:
            from analyze_nes_deadline947 import directory
            from analyze_nes_input949 import timing
            folder=directory(temp,phase,tag,cache)
            trace=timing(folder)
            assert trace==timing(directory(temp,phase,'949'+mode,cache))
            path=folder/'handoff949.json'
            path.write_text(json.dumps([(clock,name) for clock,name in rows
                if trace['valid_E0_end']<=clock<=trace['blocks'][-1][3]],indent=2)+'\n')



def guards(temp,mode):
    from check_nes_supply905_arm import run as proof
    from nes_order938 import empty_next_offer
    from nes_deadline947 import check_obj_recovery
    import nes_return920
    arm=work(mode)
    proof(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,
          short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
    with patch.object(nes_return920,'client',lambda _:ROM):
        nes_return920.guards(temp,'first',tag='949'+mode,destination=arm/'final-guards.json')
    check_obj_recovery(temp,mode,work=work,prefix='949')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','guards','profile'))
    p.add_argument('mode',choices=(*MODES,'reference935','reference946'))
    p.add_argument('temp',type=Path)
    p.add_argument('phase',nargs='?',type=int,choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    if a.mode.startswith('reference') and a.action!='replay':
        p.error('fixed references support replay only')
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='guards':
        guards(a.temp,a.mode)
    else:
        if not a.phase or not a.cache:
            p.error('replay requires phase and cache')
        replay(a.temp,a.mode,a.phase,a.cache,a.action=='profile')
