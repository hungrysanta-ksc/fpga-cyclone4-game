"""Run the 941 prefix consumer with 940 ARM pacing after section 5."""
import argparse
import ast
import re
from pathlib import Path
import shutil
from unittest.mock import patch

import nes_chain935 as chain
from nes_raw506 import once, sha
from nes_receipt941 import ARM, image

MODES=('section','quiet','empty','half','compact','sectionfit','credit','creditfast','emptyfit','halffit','refresh','quietfit','fullpoll','creditspin','turn','retime','creditfit','short','shortcredit','fastfit','handoff','borrow')
ROM=image('prefix')


def work(mode):
    return ARM.parent.parent/'nes-discovery942'/mode


def compact_report(src):
    menu=src/'nes_menu_diagnostic.c'
    code=menu.read_text()
    # These adjacent post-STOP appends are unconditional and share the buffer.
    fmt=r'"[^"\n]*"'
    pair=re.search(r'n=nes_packed828\(text,4096,n,('+fmt+r'),(nes_trace166[^\n]+?)\);\n \}\n \{\n  n=nes_packed828\(text,4096,n,('+fmt+r'),(native_runtime165[^\n]+?)\);',code)
    assert pair
    a,args_a,b,args_b=pair.groups()
    budget=(src/'nes_budget210.c').read_text()
    words=ast.literal_eval(re.search(r'static const char words\[\] = (".*?");',budget)[1]).split('\0')
    expanded=''.join(words[ord(c)-128] if ord(c)>=128 else c for c in ast.literal_eval(a)+ast.literal_eval(b))
    assert len(expanded)<int(re.search(r'char format\[(\d+)\];',budget)[1])
    menu.write_text(once(code,pair[0],f'n=nes_packed828(text,4096,n,{a} {b},{args_a},{args_b});'),newline='\n')


def before_plan_wait(src, extra):
    path=src/'nes_plan_service200.c'
    code=path.read_text()
    start=code.index('bool nes_plan200_progress(')
    wait='  if(!wait485(p))return false;'
    path.write_text(code[:start]+once(code[start:],wait,extra+'\n'+wait),newline='\n')


def prepare(variant):
    mode={'creditfit':'credit','fastfit':'creditfast','handoff':'creditfast','borrow':'creditfast'}.get(variant,variant)
    source=ARM/'link'
    assert sha(source/'src/obj-nes-100/firmware.stm')=='efaef97babd87abfec81f7f269f8fb315c754ce38dd59e27ac35ae1a3f67b545'
    link=work(variant)/'link'
    shutil.copytree(source,link)
    path=link/'src/nes_native_runtime165.c'
    code=path.read_text()
    last='s->transport.last[1]==1'
    if mode in ('compact','sectionfit','credit','creditfast','emptyfit','halffit','refresh','quietfit','fullpoll','creditspin','turn','retime','short','shortcredit'):
        compact_report(link/'src')
    if variant in ('creditfit','short','shortcredit','fastfit','handoff','borrow'):
        from pack_nes_formats942 import compact
        compact(link/'src')
    if mode=='compact':return
    if mode in ('section','sectionfit','creditfast'):
        # Only sections 1 and 5 satisfy this mask. Every pause keeps its STOP guard.
        code=once(code,last,'(s->transport.last[1] & ~4u)==1')
    elif mode in ('quiet','quietfit'):
        code=once(code,last,'(s->transport.last[1]==1 || (!reason && s->transport.last[1]==5))')
    elif mode in ('fullpoll','creditspin'):
        # Only the full ordinary queue needs E0 on the next enqueue. A
        # terminal empty descriptor costs one full E8 before that credit.
        urgency='!reason && s->transport.last[1]==5 && (uint16_t)(s->transport.sent-s->transport.retired)==4'
        if mode=='creditspin':
            urgency='!reason && s->plan.ending && (uint16_t)(s->transport.sent-s->transport.retired)==4'
        code=once(code,last,'('+last+' || ('+urgency+'))')
    elif mode in ('short','shortcredit'):
        short='!reason && s->transport.last[1]==5 && s->plan.bulk[1] && !s->plan.bulk[3]'
        code=once(code,last,'('+last+' || ('+short+'))')
    elif mode in ('half','halffit'):
        code=once(code,'84u*128u);','(!reason && s->transport.last[1]==5 ? 84u*64u : 84u*128u));')
    if variant in ('handoff','borrow'):
        # Do not delay the first valid final E0 while draining source input.
        # Actual CRC, final identity, STOP and EA-before-COMMIT remain mandatory.
        old='reason==2 && (r->state==NES_NATIVE165_COMPLETE || r->state==NES_NATIVE165_IDLE)'
        condition='reason==2'
        if variant=='borrow':
            condition='reason==2 && (s->prefetch_left || r->state==NES_NATIVE165_COMPLETE || r->state==NES_NATIVE165_IDLE)'
        code=once(code,old,condition)
    path.write_text(code,newline='\n')
    if mode in ('empty','emptyfit'):
        before_plan_wait(link/'src','  if(!flags && p->window && p->window->last[1]==5)continue;')
    if mode=='refresh':
        before_plan_wait(link/'src','''  if(!flags && p->window && p->window->last[1]==5){
   bool room;
   if(!nes_window532_room(p->window,&room))return fail(p,5);
   if(room)continue;
  }''')
    if mode in ('turn','retime'):
        # Always re-read E8 after verified credit. No tile is retired from E8.
        condition='!flags && p->window && (uint16_t)(p->window->sent-p->window->retired)==4'
        if mode=='retime':
            condition+=' && p->window->last[1]==5'
        before_plan_wait(link/'src',f"""  if({condition}){{
   bool room;
   if(!nes_window532_room(p->window,&room))return fail(p,5);
   if(room)continue;
  }}""")
        menu=link/'src/nes_menu_diagnostic.c'
        original=menu.read_text()
        a=original.index(' static const char modes[]=')
        b=original.index(' return 0;\n}',a)
        # Dispatch code immediately precedes its exact NUL-terminated name.
        names=r''' static const char modes[]="\004MMC3\0\001START\0\002BOOT\0\010EARLY\0\020LATE\0\030CONTROL\0";
 if(strncmp(name,"NES ",4))return 0;
 for(const char *b=modes;*b;){
  unsigned mode=(unsigned char)*b++;
  const char *a=name+4;
  while(*b && *a==*b){a++;b++;}
  if(!*b && !strcmp(a," 925.nh1"))return mode;
  while(*b++){}
 }
'''
        menu.write_text(original[:a]+names+original[b:],newline='\n')
    if mode in ('credit','creditfast','shortcredit'):
        # E0 checks the returned count and any final empty-queue identity.
        before_plan_wait(link/'src','''  if(!flags && p->window && p->window->last[1]==5 &&
     (uint16_t)(p->window->sent-p->window->retired)==4){
   bool room;
   if(!nes_window532_room(p->window,&room))return fail(p,5);
  }''')



def replay(temp,mode,phase,cache):
    assert sha(ROM/'sink165.sfc')=='dd66d713015c55a016f78cae5b662488301af12aeb231889454122703abe42c6'
    with patch.object(chain,'output',lambda _:ROM):
        chain.replay(temp,'final',phase,cache,'bounded',work_arm=work(mode),tag='942'+mode)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('prepare','replay','proof'))
    p.add_argument('mode',choices=MODES)
    p.add_argument('temp',type=Path)
    p.add_argument('phase',type=int,nargs='?',choices=(1,2))
    p.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=p.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,a.mode,a.phase,a.cache)
    else:
        from check_nes_supply905_arm import run
        from nes_order938 import empty_next_offer
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),925,
            short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
