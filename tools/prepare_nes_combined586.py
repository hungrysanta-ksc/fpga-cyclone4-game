# SPDX-License-Identifier: MIT
"""Bounded section/direct-progress/shared-RX link probe. Never install."""
import argparse,json
from pathlib import Path
from prepare_nes_transport584 import prepare as transport
from nes_raw506 import once
from nes_abi582 import sha

ROOT=Path(__file__).resolve().parents[1]
def prepare(src,out):
    transport(src,out)
    p=out/'nes_native165.h';s=p.read_text()
    s=once(s,' uint8_t state,next_kind,lane,error,patch_count;',
        ' uint32_t epoch586,serial586;uint16_t crc586,length586,base_count586;bool base_valid586,inherit586;\n uint8_t state,next_kind,lane,error,patch_count;')
    s=once(s,'struct nes_ingress584 {','struct nes_ingress584 {uint8_t *buffer586;')
    p.write_text(s,encoding='utf8',newline='\n')
    p=out/'nes_native165.c';s=p.read_text()
    s=once(s,'static const unsigned widths[8]={2,1,7,4,7,1,2,8};\n','')
    s=once(s,'s->state=NES_NATIVE165_FAILED;s->error=', 's->base_valid586=false;s->state=NES_NATIVE165_FAILED;s->error=')
    s=once(s,'bool valid=s->token_valid;nes_native165_reset(s);',
        'bool valid=s->token_valid;memset((uint8_t *)s+offsetof(struct nes_native165,palette),0,sizeof(*s)-offsetof(struct nes_native165,palette));')
    a=s.index('static bool record(');b=s.index('static unsigned le584(',a)
    s=s[:a]+(ROOT/'tools/nes_row583.c').read_text()+'\n'+(ROOT/'tools/nes_section586.inc').read_text()+'\n'+s[b:]
    s=once(s,'n>256||!!(flags&1)','n>254||!!(flags&1)')
    s=once(s,'if(!s||!t||!accept||','if(!s||!fn||!t||!accept||')
    s=once(s,'if(!s||!fn||!t||s->state','if(!s||!fn||!t||!t->buffer586||s->state')
    s=once(s,'uint8_t b[261]={0};b[0]=0xdd;', 'uint8_t *b=t->buffer586;memset(b,0,n+5);b[0]=0xdd;')
    s=once(s,'s->generation!=t->generation)',
        's->generation!=t->generation||s->epoch586!=t->epoch||s->serial586!=t->serial)')
    p.write_text(s,encoding='utf8',newline='\n')
    p=out/'nes_native_runtime165.h';s=p.read_text();s=once(s,' struct nes_ingress584 ingress584;',
        ' uint8_t rx586[259];\n struct nes_ingress584 ingress584;');p.write_text(s,encoding='utf8',newline='\n')
    p=out/'nes_native_runtime165.c';s=p.read_text()
    s=once(s,'n>261','n>259');s=once(s,'unsigned opcode=tx[0],original=n;','unsigned opcode=tx[0];')
    s=once(s,'uint8_t b[261];\n if(carrier){memcpy(b,tx,n);if(n<52){memset(b+n,0,52-n);n=52;}}',
        'uint8_t *b=s->rx586;\n /* E1 TX owns259B, E9 owns248B, EC owns52B. Dummy tail is ignored. */\n if(carrier&&n<52)n=52;')
    s=once(s,'carrier?b:tx,carrier?b:rx','tx,carrier?b:rx')
    s=once(s,'  memcpy(rx,b,original);\n','')
    s=once(s,'s->ingress584.serial=1;', 's->ingress584.serial=1;s->ingress584.buffer586=s->rx586;')
    p.write_text(s,encoding='utf8',newline='\n')
    p=out/'nes_plan_service200.c';s=p.read_text()
    a=s.index('static bool read509(');b=s.index('static bool valid(',a)
    s=s[:a]+'''static bool read509(struct nes_plan200 *p,uint8_t rx[50],uint8_t phase){
 if(!p->window||!p->window->progress584||!p->window->progress584(p->ctx,rx,1))return fail(p,3);
 if(!!(rx[2]&2)!=!!rx[36])return status215(p,phase,NES_PLAN215_DESCRIPTOR,rx);
 return true;
}
static unsigned flags586(const uint8_t *p){return (p[2]&4?1:0)|(p[2]&8?2:0)|(p[2]&64?4:0);}
static unsigned count586(const uint8_t *p){return p[20]|(unsigned)p[21]<<8;}
''' + s[b:]
    # All below are semantic views, not raw SPI replies; snapshot validation is
    # performed by the common runtime before either consumer can inspect them.
    a=s.index('static bool poll(');prefix=s[:a];s=s[a:]
    s=s.replace('uint8_t rx[20]','uint8_t rx[50]')
    s=s.replace('rx[3]','flags586(rx)').replace('(unsigned)rx[4]*256+rx[5]','count586(rx)')
    s=s.replace('rx[6]','rx[36]').replace('rx+6','rx+36')
    s=s.replace('i=7;i<18','i=37;i<48').replace('k=6;k<19','k=36;k<48')
    p.write_text(prefix+s,encoding='utf8',newline='\n')
    manifest=json.loads((out/'manifest.json').read_text())
    manifest.update(stage=586,scope=__doc__,history_implemented=False,
        stop_gate='First linked envelope cost; no history implementation credited if already over cap',
        patched={n:sha(out/n) for n in manifest['patched']},
        tools={n:sha(ROOT/'tools'/n) for n in ('prepare_nes_combined586.py','nes_section586.inc','nes_row583.c','prepare_nes_transport584.py')})
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('src','out'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();prepare(a.src,a.out)
