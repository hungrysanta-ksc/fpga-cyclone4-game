"""Build and replay earlier same-frame map reuse and first OBJ plan supply on 946."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_credit946 import ROM, base, once, sha, work as credit_work

BASE = credit_work('objguard')
MODES = ('word', 'row', 'prefix', 'combined', 'half', 'half_prefix', 'partial', 'table', 'seal', 'pressure', 'wire', 'pressure_seal', 'fit')


def work(mode):
    return BASE.parent.parent/'nes-deadline947'/mode


def pack_report(src):
    """Reuse four empty dictionary slots in post-session report strings."""
    import ast
    import re
    from collections import Counter
    from prepare_nes_report594 import literal
    paths=[src/name for name in ('nes_budget210.c','nes_cost471.c','nes_menu_diagnostic.c','nes_cost471.h')]
    sources=[p.read_text() for p in paths]
    declaration=re.search(r'static const char words\[\] = (".*?");',sources[0])
    decode=lambda t:ast.literal_eval(t).encode('latin1')
    words=decode(declaration[1]).split(b'\0')[:-1]
    sources[0]=sources[0].replace(declaration[0],'/* dictionary947 */')
    pattern=r'"(?:[^"\\]|\\.)*"'
    tokens={t:decode(t) for source in sources for t in re.findall(pattern,source)
            if re.search(r'\\[23][0-7][0-7]',t)}
    def expand(value):
        return b''.join(bytes((b,)) if b<128 else words[b-128] for b in value)
    original={t:expand(v) for t,v in tokens.items()}
    for index in (7,13,20,23):
        assert not words[index] and all(128+index not in v for v in tokens.values())
        grams=Counter(v[i:i+n] for v in tokens.values() for n in range(2,13) for i in range(len(v)-n+1))
        likely=[k for k,count in grams.items() if count*(len(k)-1)>len(expand(k))]
        if not likely:
            break
        def gain(k):
            return sum(v.count(k) for v in tokens.values())*(len(k)-1)-len(expand(k))
        best=max(likely,key=lambda k:(gain(k),k))
        if gain(best)<=0:
            break
        words[index]=expand(best)
        tokens={t:v.replace(best,bytes((128+index,))) for t,v in tokens.items()}
    assert all(expand(v)==original[t] for t,v in tokens.items())
    for p,source in zip(paths,sources):
        code=re.sub(pattern,lambda m:literal(tokens[m[0]]) if m[0] in tokens else m[0],source)
        code=code.replace('/* dictionary947 */','static const char words[] = '+literal(b'\0'.join(words)+b'\0')+';')
        p.write_text(code,newline='\n')


def prepare(mode):
    assert sha(BASE/'link/src/obj-nes-100/firmware.stm')=='2cf4fa201bf44a6d43c17e9abdfae26afe16419db44ccc45f7a0e21a27602827'
    link=work(mode)/'link'
    shutil.copytree(BASE/'link',link)
    if mode=='fit':
        pack_report(link/'src')
    if mode in ('table','seal','pressure_seal','fit'):
        path=link/'src/nes_native_runtime165.c'
        code=path.read_text()
        if mode=='table':
            # The planner has handed off the receiver. Borrow just one SPI
            # transaction group while waiting on the immutable table head.
            # A new input still cannot COMMIT until the last display ACK and EA.
            code=once(code,'reason==1 && progress && r->state==NES_NATIVE165_IDLE && s->prefetch_left==7 &&',
                      'reason==1 && s->prefetch_left && (!progress || r->state==NES_NATIVE165_IDLE) &&')
        else:
            # Once SEAL is queued and the first block actually retired, continue
            # the existing bounded input loop without an intervening E0.
            code=once(code,'   bool first=(r->state==NES_NATIVE165_IDLE);','')
            code=once(code,'if(reason!=2 || first)break;', 'if(reason!=2)break;')
        path.write_text(code,newline='\n')
    if mode in ('word','row','combined','half','half_prefix','partial','pressure','wire','pressure_seal','fit'):
        path=link/'src/nes_planner211.c'
        code=path.read_text()
        first=code.index('   for(unsigned x=0;x<33;x++){',code.index('  if(reuse!=g){'))
        end=code.index('   reusable474|=',first)
        # Map inputs match all 66 bytes, including both subpalette bits.
        # Only palette epoch changes bit 12. Source and destination rows differ.
        if mode in ('word','half','half_prefix','partial','pressure','wire','pressure_seal','fit'):
            loop=code[first:end]
            a=loop.index('    unsigned cell=')
            b=loop.index('    c=(new_column',a)
            loop=loop[:a]+'    word^=(unsigned)(bank[g]^bank[reuse])<<12;\n'+loop[b:]
        else:
            loop='''   for(unsigned x=0;x<33;){
    unsigned col=(old_column+x)&63, dst=(new_column+x)&63;
    unsigned n=32-(col&31);
    if(n>32-(dst&31))n=32-(dst&31);
    if(n>33-x)n=33-x;
    unsigned src=((col/32)*1024+reuse*32+(col&31))*2;
    unsigned at=((dst/32)*1024+g*32+(dst&31))*2;
    if(bank[g]==bank[reuse]){
     if(memcmp(p->map+at,p->map+src,n*2)){
      memcpy(p->map+at,p->map+src,n*2);
      p->map_dirty|=UINT64_C(1)<<(at/64);
     }
    }else for(unsigned i=0;i<n;i++){
     unsigned word=p->map[src+i*2]|((unsigned)p->map[src+i*2+1]<<8);
     map_word185(p,at+i*2,word^0x1000);
    }
    x+=n;
   }
'''
        code=code[:first]+loop+code[end:]
        if mode in ('half','half_prefix'):
            a=code.index(' if(p->map[at]')
            b=code.index('\n}',a)
            code=code[:a]+''' uint16_t current, value=(uint16_t)word;
 memcpy(&current,p->map+at,sizeof current);
 if(current!=value){
  memcpy(p->map+at,&value,sizeof value);
  p->map_dirty|=UINT64_C(1)<<(at/64);
 }'''+code[b:]
        path.write_text(code,newline='\n')
    if mode in ('prefix','combined','half_prefix','partial','pressure','wire','pressure_seal','fit'):
        path=link/'src/nes_plan_service200.c'
        code=path.read_text()
        anchor=' if(!append(p,q))return false;\n if(q->kind==0)'
        replacement=''' if(!append(p,q))return false;
 /* Supply the first confirmed compact OBJ with the mandatory zero tile.
  * Both still need a checked E8, SNES consumption and physical release. */
 if(!p->sent && p->bank_history==2 && p->count==2 && q->kind==1)return flush(p);
 if(q->kind==0)'''
        if mode in ('partial','pressure','wire','pressure_seal','fit'):
            # A complete eight-row OBJ stays in the sorted suffix for a larger
            # upload. Only a masked first OBJ can take this early transfer.
            replacement=replacement.replace('q->kind==1)return flush','q->kind==1 && q->mask!=255)return flush')
        if mode in ('pressure','wire','pressure_seal','fit'):
            h=link/'src/nes_plan_service200.h'
            h.write_text(once(h.read_text(),'bool tile_service;','bool tile_service; uint8_t pressure;'),newline='\n')
            code=once(code,'  if(!poll(p,&flags,NES_PLAN215_FINISH))return false;',
                      '  if(!poll(p,&flags,NES_PLAN215_FINISH))return false;\n  if(!flags && i>=3)p->pressure|=1;')
            code=once(code,'   p->sent=0;p->finished=false;',
                      '   p->pressure<<=1;p->sent=0;p->finished=false;')
            replacement=replacement.replace('!p->sent && p->bank_history==2','!p->sent && (p->pressure&2) && p->bank_history==2')
        path.write_text(once(code,anchor,replacement),newline='\n')

    if mode=='wire':
        path=link/'src/nes_plan_service200.c'
        code=path.read_text()
        start='static bool append(struct nes_plan200 *p,const struct nes_plan191 *q){'
        code=once(code,start+'\n uint8_t encoded[32];unsigned n=nes_plan199_encode(q,encoded);',
                  'static bool append_wire(struct nes_plan200 *p,const uint8_t *encoded,unsigned n){')
        code=once(code,'p->buffer[4+at-8+3]>q->slot','p->buffer[4+at-8+3]>encoded[3]')
        code=once(code,' if(!append(p,q))return false;',
                  ' uint8_t encoded[32];unsigned n=nes_plan199_encode(q,encoded);\n if(!append_wire(p,encoded,n))return false;')
        a=code.index(' struct nes_plan191 end={0};')
        b=code.index(' p->ending=true;',a)
        code=code[:a]+''' /* END has no caller fields. Insert its canonical three-byte record
  * through the same capacity/credit/framing path as a validated tile. */
 const uint8_t end[]={0x83,(uint8_t)p->generation,(uint8_t)(p->generation>>8)};
 if(!append_wire(p,end,sizeof end))return false;
'''+code[b:]
        path.write_text(code,newline='\n')


def check_obj_recovery(temp,mode):
    import analyze_nes_obj923 as validation
    import check_nes_chain935 as edge
    import nes_obj923
    arm=work(mode)
    tag='947'+mode
    packets=temp/f'nes-tile821-obj-jointmirror-p1-{tag}-warm-pair'/'packets.jsonl'
    heads=[bytes.fromhex(json.loads(line)[2]) for line in packets.read_text().splitlines()]
    sizes=[int.from_bytes(h[14:16],'little') for h in heads
           if h[:2]==bytes((7,1)) and int.from_bytes(h[8:10],'little')==909]
    assert sizes[0]==32 and sizes[-1]>=288
    lengths=(sizes[0],sizes[-1])
    with patch.object(nes_obj923,'client',lambda _:ROM):
        nes_obj923.obj_stops(temp,'first',tag=tag,destination=arm/'final-stops.json',
                            lengths=lengths,output_prefix='obj947-stop')
    with patch.object(validation,'client',lambda _:ROM):
        result=validation.recovery('final',arm,trial=arm,stop_lengths=lengths)
    with patch.object(edge,'output',lambda _:ROM):
        result['edge']={f'{phase}-{case}':edge.run(temp,'bounded',phase,case,tag=tag)
                        for phase in (1,2) for case in ('head','stop')}
    (arm/'safety947.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','guards'))
    parser.add_argument('mode',choices=MODES)
    parser.add_argument('temp',type=Path)
    parser.add_argument('phase',type=int,nargs='?',choices=(1,2))
    parser.add_argument('cache',nargs='?',choices=('warm','cold'))
    a=parser.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='guards':
        from check_nes_supply905_arm import run as proof
        from nes_order938 import empty_next_offer
        import nes_obj923
        import nes_return920
        arm=work(a.mode)
        proof(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',arm,925,
              short_header=True,order=empty_next_offer,marker_values=(4,8,16,24))
        with patch.object(nes_return920,'client',lambda _:ROM),patch.object(nes_obj923,'client',lambda _:ROM):
            nes_return920.guards(a.temp,'first',tag='947'+a.mode,destination=arm/'final-guards.json')
        check_obj_recovery(a.temp,a.mode)
    else:
        with patch.object(base.prev.chain,'output',lambda _:ROM):
            base.prev.chain.replay(a.temp,'final',a.phase,a.cache,'bounded',work_arm=work(a.mode),tag='947'+a.mode)
