"""Give the next ready OBJ a queue slot before a repeated OAM fill."""
import argparse
import shutil
from pathlib import Path
from nes_chain935 import replay
from nes_oam937 import work as previous
from nes_raw506 import once, sha


def work(mode):
    return previous('runs').parent.parent/'nes-order938'/mode


MODES=('after','replace','full','bound','bootpair','linked','fit','balanced')


def prepare(mode):
    if mode not in MODES:
        raise ValueError(mode)
    original=previous('runs')/'link'
    assert sha(original/'src/obj-nes-100/firmware.stm')=='82b30f92b6614886ccff14a83c9381d0bc6c98c68ba4fc4a34a354d2df8113a8'
    link=work(mode)/'link'
    shutil.copytree(original,link)
    weigh_bulk=mode=='balanced'
    compact_report=mode in ('fit','linked','balanced')
    if compact_report:
        mode='bound' if mode=='linked' else 'bootpair'
    src=link/'src/nes_native_sink165.c'
    old='!wait_map880(s->plan->window,12))return fail(s,5);'
    wait='wait_map880(s->plan->window,12)'
    progress='nes_plan200_progress(s->plan,NES_ORDINARY553)'
    long_plan='s->plan->sent>2'
    if mode=='full':
        src.write_text(once(src.read_text(),'op==3?NES_FINAL553:section==2?',
                            '(op==3 || op==8)?NES_FINAL553:section==2?'),newline='\n')
        return
    if mode=='replace':
        test=f'({long_plan} ? {progress} : {wait})'
    else:
        test=f'{wait} && (!({long_plan}) || {progress})'
    if weigh_bulk:
        test='((s->plan->bulk[2]+256u*s->plan->bulk[3])>=expanded ? nes_plan200_progress(s->plan,NES_FINAL553) : ('+test+'))'
    text=once(src.read_text(),old,'!('+test+'))return fail(s,5);')
    if mode in ('bound','bootpair'):
        plan=link/'src/nes_plan_service200.c'
        mark='p->bulk_valid=p->bulk_pending=true;p->bulk_until=p->window->sent;'
        cond='rx[3]==2 && p->ending && p->sent>2 && p->window->wait'
        if mode=='bootpair':
            cond='rx[3]==2 && p->ending && follows_oam && p->window->wait'
        cond+=' && d[1] && d[3]'
        code=once(plan.read_text(),mark,mark+'\n     if('+cond+' && !p->window->wait(p->window->ctx,p->window->guard,4,false))return fail(p,2);')
        if mode=='bootpair':
            anchor='if(!nes_sink195_submit(p->sink,d))'
            history='(!p->bank_history || p->window->last[1]==4)'
            code=once(code,anchor,'bool follows_oam='+history+';\n     '+anchor)
        plan.write_text(code,newline='\n')
    if mode in ('bound','bootpair'):
        menu=link/'src/nes_menu_diagnostic.c'
        code=menu.read_text()
        assert 'geometry_delta[]={0,1,2,26,27,28}' in code and 'return 384+geometry_delta[i];' in code
        begin=code.index(' mode900=selected>=410?')
        end=code.index('pending=true;',begin)
        code=code[:begin]+''' /* Each accepted diagnostic marker loads the same 384 KiB ROM. */
 mode900=selected>=410?(unsigned char)(selected-409):0;
 nes_boot_probe798=mode900?0:(unsigned char)(selected-384);
 geometry=384;'''+code[end:]
        code=once(code,'static bool entry_only113,base_only116;','')
        code=once(code,'return base_only116;','return false;')
        code=once(code,'return entry_only113;','return false;')
        if mode=='bootpair':
            code=once(code,'for(unsigned i=0,off=0;i<sizeof geometry_delta;i++){','const char *b=modes;\n for(unsigned i=0;i<sizeof geometry_delta;i++){')
            code=once(code,'const char *a=name,*b=modes+off;','const char *a=name;')
            code=once(code,'while(*b)b++;\n  off=(unsigned)(b-modes)+1;', 'while(*b++){}')
        if compact_report:
            import ast
            import re
            code=once(code,'static unsigned geometry;','enum { geometry=384 };')
            code=once(code,' geometry=384;pending=true;',' pending=true;')
            pattern=r' n=nes_packed828\(text,4096,n,("[^"]*"),(native_runtime165\.transport[^\n]+?)\);\n n=nes_packed828\(text,4096,n,("[^"]*"),(native_runtime165\.plan[^\n]+?)\);'
            match=re.search(pattern,code)
            assert match
            left,args1,right,args2=match.groups()
            formatter=(link/'src/nes_budget210.c').read_text()
            words=ast.literal_eval(re.search(r'static const char words\[\] = (".*?");',formatter)[1]).split('\0')
            size=sum(len(words[ord(c)-128]) if ord(c)>=128 else 1 for c in ast.literal_eval(left)+ast.literal_eval(right))
            capacity=int(re.search(r'char format\[(\d+)\];',formatter)[1])
            assert size+1<=capacity
            code=once(code,match[0],' n=nes_packed828(text,4096,n,'+left+' '+right+','+args1+','+args2+');')
        menu.write_text(code,newline='\n')
    src.write_text(text,newline='\n')


def empty_next_offer(trace):
    """One-screen boot fixture has no next capture at a terminal OBJ probe."""
    from check_nes_sram897 import D0, crc
    empty=bytearray.fromhex('00d6000000000000')
    empty[-1]=crc(empty[1:-1],8,7,0)
    result=[]
    descriptor=None
    for tx,rx in trace:
        request,reply=bytes.fromhex(tx),bytes.fromhex(rx)
        result.append([tx,rx])
        if request[0]==0xe8:
            descriptor=reply[6:18] if reply[3]==2 and int.from_bytes(reply[4:6],'big')>2 else None
        if request[:3]==bytes((0xe1,7,1)) and descriptor and descriptor[0:2]==bytes((1,1)) and descriptor[3]:
            packet=request[1:]
            assert descriptor[8:12]==packet[16:20] and descriptor[2:4]==packet[14:16]
            result.append([D0.hex(),empty.hex()])
            descriptor=None
    assert len(result)>len(trace)
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','proof','guards'))
    parser.add_argument('mode',choices=MODES)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,nargs='?',choices=(1,2))
    parser.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=parser.parse_args()
    arm=work(a.mode)
    tag='938'+a.mode
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=arm,tag=tag)
    elif a.action=='proof':
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,short_header=True,
            order=empty_next_offer if a.mode in ('bound','bootpair','fit','linked','balanced') else None)
    else:
        from nes_oam937 import guards
        guards(a.temp,tag,arm)
