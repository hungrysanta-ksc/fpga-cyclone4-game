"""Keep the complete 727 map run before issuing section 5 on a checked DMA notice."""
from argparse import ArgumentParser
from pathlib import Path
from shutil import copytree, ignore_patterns

from nes_raw506 import once, sha


def prepare(base, out, pack_early=False, pack_after_map=False):
    assert sha(base/'src/obj-nes-100/firmware.stm') in {
        '523be6b648b23be88e888dd0c119788e164cd42c66306368ed4f77d07fd90655',
        '3196a512124899531abbcb45f545cb01186779326b47c0e811d61209b1f2f386'}
    copytree(base, out, ignore=ignore_patterns('obj-*', '.dep-*', '*.log'))
    path = out/'src/nes_native_sink165.c'
    s = path.read_text()
    # Same short zero padding as 733; preserve the old packet boundaries.
    s = once(s, 'if(op==2 && data && n>=4 && !(n&1)){\n  unsigned i=2;while(i<n && data[i]==data[i&1])i++;',
             'if(op==2 && n>=4 && !(n&1)){\n  unsigned i=n;\n  if(data){i=2;while(i<n && data[i]==data[i&1])i++;}')
    s = once(s, 'if(n)memcpy(b+16,data,n)', 'if(n && data)memcpy(b+16,data,n)')
    s = once(once(s,'zero[240]','zero[2]'),'offset,zero,n)','offset,NULL,n)')
    start = s.index(' if(!span(s,5,0,p->hdma')
    end = s.index('  /* Read the enclosing object',start)
    prefix = s[start:end]
    s = s[:start]+''' if(!prefix_sent && !scroll737(s,p))return false;
 if(p->patch_count){
  unsigned offset=1121;
'''+s[end:]
    helpers = '''
/* At most one consecutive OBJ slot run can follow this DMA notice.
 * Count starts across the byte boundary; all-zero means no pending work. */
static bool one_obj737(const uint8_t *dirty){
 unsigned previous=0;
 bool found=false;
 for(unsigned i=128;i<144;i++){
  unsigned bits=dirty[i];
  unsigned starts=bits & ~((bits<<1)|previous);
  if(starts){
   if(found || (starts&(starts-1)))return false;
   found=true;
  }
  previous=bits>>7;
 }
 return found;
}
static bool scroll737(struct nes_native_sink165 *s,struct nes_native_video165 *p){
'''+prefix+''' }
 return true;
}
'''
    s=once(s,'bool nes_sink212_seal(',helpers+'bool nes_sink212_seal(')
    s=once(s,' if(!map527(s,p,r->map_upload,false))',' bool prefix_sent=false;\n if(!map527(s,p,r->map_upload,false))')
    s=once(s,'    if((w->status_flags&8) || !w->wait)break;', '''    if(w->status_flags&8){
     /* drain verified the latest map identity and returned all queue credit.
      * The notice is only an issue hint; final display still needs SEAL. */
     if(!s->obj_next && p->patch_count && one_obj737(r->dirty)){
      if(!scroll737(s,p))return false;
      prefix_sent=true;
     }
     break;
    }
    if(!w->wait)break;''')
    if pack_early:
        # The 727 packing loop writes only expired BG keys. Run it once
        # while the retained map heads drain if the immutable OBJ run is single.
        begin=s.index('  /* Canonical raw CHR')
        end=s.index(' bool same=same635',begin)
        pack=s[begin:end]
        loop=pack[pack.index('   for(unsigned plane'):pack.index('   raw=out;')]
        helper=('static unsigned __attribute__((noinline)) pack737(struct nes_native_video165 *p){\n'
                ' unsigned packed=0;uint8_t *out=(uint8_t *)p->bg_keys+4096;\n'+loop+' return packed;\n}\n')
        s=s[:begin]+'''  const uint8_t *raw=p->patch.chr;
  if(p->patch_count && p->patch_count<=2){
   if(!packed)packed=pack737(p);
   raw=(uint8_t *)p->bg_keys+4096;
  }else packed=2048;
'''+s[end:]
        s=once(s,'static bool scroll737(',helper+'static bool scroll737(')
        s=once(s,' bool prefix_sent=false;', ' unsigned packed=0;bool prefix_sent=false;')
        s=once(s,'   unsigned left=w->poll_limit;','''   bool single=!s->obj_next && p->patch_count && one_obj737(r->dirty);
   if(single && p->patch_count<=2)packed=pack737(p);
   unsigned left=w->poll_limit;''')
        s=once(s,'     if(!s->obj_next && p->patch_count && one_obj737(r->dirty)){','     if(single){')
    if pack_after_map:
        # Every map E1 has already copied its payload. This is the original
        # bounded CPU-only loop, moved intact; no second packing state or call.
        begin=s.index('  /* Canonical raw CHR')
        end=s.index(' bool same=same635',begin)
        pack=s[begin:end]
        s=s[:begin]+s[end:]
        s=once(s,' /*719 The ACK timestamp',pack+' /*719 The ACK timestamp')
    path.write_text(s,encoding='utf8',newline='\n')


if __name__=='__main__':
    parser=ArgumentParser()
    for name in ('base','out'):
        parser.add_argument(name,type=Path)
    group=parser.add_mutually_exclusive_group()
    group.add_argument('--pack-early', action='store_true')
    group.add_argument('--pack-after-map', action='store_true')
    a=parser.parse_args()
    prepare(a.base,a.out,a.pack_early,a.pack_after_map)
