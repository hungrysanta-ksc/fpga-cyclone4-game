"""Stage 736 changes the issue order of independently addressed sections on 727."""
from argparse import ArgumentParser
from pathlib import Path
from types import SimpleNamespace
from prepare_nes_tail729 import run as share_span
from shutil import copytree, ignore_patterns

from nes_raw506 import once, sha


def prepare(base, out, prefix_only, shared=True, cursor=True):
    assert sha(base/'src/obj-nes-100/firmware.stm') in {
        '523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655',
        '3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386',
    }
    copytree(base, out, ignore=ignore_patterns('obj-*','.dep-*','*.log'))
    path = out/'src/nes_native_sink165.c'
    if shared:
        patch=out/'span-recipe'
        share_span(SimpleNamespace(base=base/'src',out=patch,owned=False,cheap_oam=True))
        s=(patch/path.name).read_text()
    else:
        s=path.read_text()
    # Use the verified 733 zero source for short padding. Retain the original
    # packet boundaries, including the independent raw prefix after offset 1121.
    s = once(s, 'if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;',
             'if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}')
    s = once(s,'if(n)memcpy(b+16,data,n)','if(n && data)memcpy(b+16,data,n)')
    s = once(s,'zero[240]','zero[2]')
    s = once(s,'offset,zero,n)','offset,NULL,n)')
    if cursor:
        s=once(s,''' for(unsigned g=s->map_next&127;g<64;){
  if(!((mask>>g)&1)){g++;pair=false;continue;}
  unsigned first=g++,count=1;while(g<64&&count<3&&((mask>>g)&1)){g++;count++;}''',
               ''' unsigned g=s->map_next&127;
 mask=g<64?mask>>g:0;
 while(mask){
  if(!(mask&1)){g++;mask>>=1;pair=false;continue;}
  unsigned first=g++,count=1;mask>>=1;
  while(count<3 && (mask&1)){g++;count++;mask>>=1;}''')
    begin = s.index('bool nes_sink212_seal(')
    map_start = s.index(' if(!map527(s,p,r->map_upload',begin)
    pack = s.index('  /* Canonical raw CHR',map_start)
    color = s.index(' bool same=same635',pack)
    scroll = s.index(' if(!span(s,5,0,p->hdma',color)
    raw = s.index('  /* Read the enclosing object',scroll)
    end = s.index(' uint8_t descriptor[168]',raw)
    maps = s[map_start:pack]
    ordinary = s[color:scroll].replace(' bool same=same635(s,p);\n','')
    prefix = s[scroll:raw]
    suffix = s[pack:color]+' if(p->patch_count){\n  unsigned offset=1121;\n'+s[raw:end]
    suffix = once(suffix,'size[5]=(uint16_t)(offset+249);','*size=(uint16_t)(offset+249);')
    helpers = '''
/* Keep all checked transactions inside the normal queue. A contiguous
 * outstanding map span is issued in one call, with its original idle grant. */
static bool map736(struct nes_native_sink165 *s,struct nes_native_video165 *p,struct nes_resident211 *r){
'''+maps+''' return true;
}
static bool colors736(struct nes_native_sink165 *s,struct nes_native_video165 *p,struct nes_resident211 *r,bool same){
'''+ordinary+''' return true;
}
static bool prefix736(struct nes_native_sink165 *s,struct nes_native_video165 *p){
'''+prefix+''' }
 return true;
}
static bool tables736(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint16_t *size){
'''+suffix+''' return true;
}
'''
    schedule = ''' bool same=same635(s,p);
 uint64_t remaining=s->map_next<64?r->map_upload>>s->map_next:0;
 /* A separated map tail retains its two idle DMA opportunities. Check the
  * immutable OBJ dirty bits; resident slots can also belong to old frames. */
 bool early=false;
 if(p->patch_count && s->plan && s->plan->bank_history==2 && same && remaining &&
    !(remaining & (remaining+(remaining & -remaining)))){
  for(unsigned i=128;i<144;i++)if(r->dirty[i]){early=true;break;}
 }
 if(early){
  if(!prefix736(s,p))return false;
  MAP_TABLE_ORDER
  if(!colors736(s,p,r,same))return false;
 }else{
  if(!map736(s,p,r) || !colors736(s,p,r,same) || !prefix736(s,p) || !tables736(s,p,&size[5]))return false;
 }
'''
    order = ('if(!map736(s,p,r) || !tables736(s,p,&size[5]))return false;' if prefix_only else
             'if(!tables736(s,p,&size[5]) || !map736(s,p,r))return false;')
    s = s[:begin]+helpers+s[begin:map_start]+schedule.replace('MAP_TABLE_ORDER',order)+s[end:]
    path.write_text(s,encoding='utf8',newline='\n')


if __name__=='__main__':
    parser=ArgumentParser()
    parser.add_argument('base',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--prefix-only',action='store_true')
    parser.add_argument('--original-span',action='store_true')
    parser.add_argument('--original-cursor',action='store_true')
    a=parser.parse_args()
    prepare(a.base,a.out,a.prefix_only,not a.original_span,not a.original_cursor)
