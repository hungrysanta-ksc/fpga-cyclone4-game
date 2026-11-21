"""Exercise the selected ARM link and replay corruption, STOP and cold restart on its packet stream."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from check_nes_longrun692 import run as timer
from check_nes_menu533 import check as menu
from check_nes_raw864 import guards
from check_nes_supply485_arm import ARM
from check_nes_tail859_layout import check as layout
from prepare_nes_trial802 import PROBES


def compact_rows(arm,out,cc):
    source=(arm/'nes_native_sink165.c').read_text()
    begin=source.index('unsigned packed=2048;const uint8_t *raw=')
    end=source.index('bool same=same635',begin)
    # Reuse the exact production gather. Independently decode the expected
    # order from the output byte index, including both bytes of each tile.
    harness='''
#include "nes_native_video165.h"
#include <string.h>
#include <assert.h>
static struct nes_native_video165 plan;
int main(void) {
 struct nes_native_video165 *p=&plan;
 for(unsigned count=0;count<=7;count++) {
  for(unsigned i=0;i<2048;i++)p->patch.chr[i]=(uint8_t)(i*83+(i>>4)*19+(i>>8));
  uint8_t original[2048];memcpy(original,p->patch.chr,sizeof original);
  p->patch_count=count;
  GATHER
  assert(!memcmp(original,p->patch.chr,sizeof original));
  if(count==1 || count==2) {
   assert(packed==192*count);
   for(unsigned i=0;i<packed;i++) {
    unsigned plane=i/(64*count),row=(i/64)%count,tile=(i/2)%32;
    assert(raw[i]==original[64*tile+16*plane+2*row+(i%2)]);
   }
  } else {assert(raw==p->patch.chr && packed==2048);}
 }
 return 0;
}
'''.replace('GATHER',source[begin:end])
    test=out/'gather.c'
    test.write_text(harness)
    exe=out/'gather.exe'
    subprocess.run([cc,'-std=c11','-O2','-I',arm,test,'-o',exe],check=True)
    subprocess.run([exe],check=True)


def coverage_words(arm,out,cc):
    source=(arm/'nes_native_sink165.c').read_text()
    begin=source.index('for(unsigned i=0;i<sizeof r->used;i+=4)')
    end=source.index('if(s->state!=NES_SINK165_BUILD)',begin)
    harness='''
#include "nes_resident211.h"
#include <assert.h>
#include <string.h>
static struct nes_resident211 resident;
static int verify(const struct nes_resident211 *r) {
 CHECK
 return 1;
}
int main(void) {
 for(unsigned bank=0;bank<2;bank++)for(unsigned bit=0;bit<144*8;bit++){
  struct nes_resident211 *r=&resident;
  memset(r,0,sizeof(*r));r->target=bank;
  unsigned i=bit/8;
  uint8_t b=1u<<(bit%8);
  r->used[i]=b;r->resident[1-bank][i]=b;
  assert(!verify(r));
  r->dirty[i]=b;assert(verify(r));
  r->dirty[i]=0;r->resident[bank][i]=b;assert(verify(r));
 }
 return 0;
}
'''.replace('CHECK',source[begin:end].replace('return fail(s,5);','return 0;'))
    test=out/'coverage.c'
    test.write_text(harness)
    exe=out/'coverage.exe'
    subprocess.run([cc,'-std=c11','-O2','-I',arm,test,'-o',exe],check=True)
    subprocess.run([exe],check=True)


def linked_coverage(arm):
    # IDLE after the preflight returns false without setting FAULT. A missing
    # bit faults earlier. No PPU or SPI callback is needed to distinguish them.
    m=ARM(arm,'normal')
    r,s=m.resident,m.s
    rk,sk='nes_resident211','nes_native_sink165'
    def addr(field):return r+m.layout[rk][field]
    steps=[]
    for bank in (0,1):
        for key,value,n in [('open',1,1),('prepared',1,1),('fault',0,1),('target',bank,1),
                            ('serial',bank+1,4),('generation',907,2),('displayed',0,1)]:
            m.put(r,rk,key,value,n)
        for key,value,n in [('serial',bank+1,4),('generation',907,2),('displayed',0,1)]:
            m.put(s,sk,key,value,n)
        used=bytes((i*53+11)&255 for i in range(144))
        mask=bytes(v&0xa5 for v in used)
        dirty=bytes(v&0x5a for v in used)
        m.u.mem_write(addr('used'),used)
        m.u.mem_write(addr('resident')+(1-bank)*144,bytes([255])*144)
        m.u.mem_write(addr('resident')+bank*144,mask)
        for ix in [None,*range(0,144,4)]:
            data=bytearray(dirty)
            if ix is not None:
                # Remove one bit that exists only in dirty in this word.
                j=next(k for k in range(ix,ix+4) if data[k])
                data[j]&=data[j]-1
            m.u.mem_write(addr('dirty'),bytes(data))
            m.put(s,sk,'state',0,1)
            m.put(s,sk,'error',0,1)
            start=m.instructions
            assert m.call('nes_sink212_seal',[s,0,r])==0
            assert m.get(s,sk,'error')==(0 if ix is None else 5)
            if ix is None:steps.append(m.instructions-start)
    return dict(valid_preflight_to_IDLE_instructions=steps,wrong_bank_rejections=72)


def empty_map(arm):
    m=ARM(arm,'normal')
    m.setup()
    fields=m.layout['nes_native_sink165']
    results={}
    for cursor in (0,23,32,55,64,128):
        for early in range(4):
            for pair in (False,True):
                m.put(m.s,'nes_native_sink165','map_next',cursor,1)
                m.put(m.s,'nes_native_sink165','map_pair683',pair,1)
                expected=bytearray(m.u.mem_read(m.s,fields['size']))
                expected[fields['map_pair683']]=0
                count=len(m.endpoint.calls)
                start=m.instructions
                # The uint64_t mask occupies r2:r3, with early on the stack.
                assert m.call('map527',[m.s,m.video,0,0,early])==1
                assert m.u.mem_read(m.s,len(expected))==expected and len(m.endpoint.calls)==count
                if early==0 and not pair:
                    results[cursor]=m.instructions-start
    return dict(cases=48,instructions_by_cursor=results)


def empty_offer(arm):
    from check_nes_game478 import UC_HOOK_CODE,UC_ARM_REG_LR,UC_ARM_REG_PC,UC_ARM_REG_R0,UC_ARM_REG_R1
    m=ARM(arm,'normal')
    m.setup()
    m.put(m.s,'nes_native_sink165','plan',m.p,4)
    m.put(m.resident,'nes_resident211','target',0,1)
    m.u.mem_write(m.resident+m.layout['nes_resident211']['map_stale'],bytes(16))
    lookups=[]
    def not_ready(u,pc,size,_):
        lookups.append(pc)
        u.mem_write(u.reg_read(UC_ARM_REG_R1),b'\0')
        u.reg_write(UC_ARM_REG_R0,1)
        u.reg_write(UC_ARM_REG_PC,u.reg_read(UC_ARM_REG_LR))
    call=m.syms['nes_plan527_map_credit']
    m.u.hook_add(UC_HOOK_CODE,not_ready,begin=call,end=call)
    for pending,mask,stop in [(False,0,False),(True,0,False),(False,1,False),(False,0,True)]:
        m.put(m.video,'nes_native_video165','map_dirty',mask,8)
        m.put(m.s,'nes_native_sink165','map_next',0,1)
        m.put(m.s,'nes_native_sink165','map_pair683',1,1)
        m.put(m.p,'nes_plan200','bulk_pending',pending,1)
        m.endpoint.mode='STOP_after_bulk' if stop else 'normal'
        m.endpoint.bulk=1
        before=len(lookups)
        ok=m.call('nes_sink527_early',[m.s,m.video,m.resident,0])
        assert bool(ok)==(not stop)
        assert len(lookups)-before==int(pending or mask!=0),(pending,mask,stop,len(lookups)-before)
        if not pending and not mask:
            assert m.get(m.s,'nes_native_sink165','map_pair683')==0
            assert m.get(m.s,'nes_native_sink165','map_next')==0
        if stop:assert m.get(m.p,'nes_plan200','error')==2 and m.get(m.s,'nes_native_sink165','error')==5
    return dict(no_work_checked=True,pending_bulk_keeps_credit=True,nonempty_offer_keeps_credit=True,STOP_latched=True)


def check(temp,variant):
    build=PROBES/'nes-opening865'/variant
    arm=build/'src'
    out=build/'checks'
    out.mkdir(exist_ok=True)
    cc=Path('C:/altera_lite/25.1std/questa_fse/gcc-7.4.0-mingw64vc16/bin/gcc.exe')
    if variant in ('coverage','empty','cursor','span'):
        coverage_words(arm,out,cc)
    compact_rows(arm,out,cc)
    layout(arm,out/'layout',cc)
    subprocess.run([sys.executable,str(Path(__file__).with_name('check_nes_transfer512_recovery.py')),
                    '--arm',str(arm),'--trial','855','--fault','none','--out',str(out/'base')],check=True)
    guards(temp,temp/f'nes-tile821-demo-jointmirror-p1-865{variant}-on',out/'receiver.json')
    proof=dict(gather_patch_counts=list(range(8)),timer=timer(arm),menu=menu(arm,'855'))
    if variant in ('coverage','empty','cursor','span'):
        proof['coverage_bank_bit_cases']=2*144*8
        proof['linked_coverage']={name:linked_coverage(src) for name,src in
                                  [('855',PROBES/'nes-trial855/link/src'),(variant,arm)]}
    if variant in ('empty','cursor','skip','suffix'):
        proof['empty_map']={name:empty_map(src) for name,src in
                            [('855',PROBES/'nes-trial855/link/src'),(variant,arm)]}
    if variant=='offer':
        proof['empty_offer']=empty_offer(arm)
    for name in ('layout/result','base/result','receiver'):
        proof[name]=json.loads((out/(name+'.json')).read_bytes())
    assert proof['timer']['passed'] and proof['menu']['rows']['normal']['released']
    assert proof['base/result']['base_restored'] and proof['base/result']['safe_return']
    assert proof['receiver']['stop']==dict(commits=1,status=228) and proof['receiver']['restart']==dict(commits=2,status=1)
    (out/'checked.json').write_text(json.dumps(proof,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('temp',type=Path)
    p.add_argument('variant')
    check(**vars(p.parse_args()))
