# SPDX-License-Identifier: MIT
"""Issue ACK-backed OAM, scroll and padding inside the existing map wait."""
import argparse
from pathlib import Path
from nes_raw506 import once, sha


def prepare(base, out, table_first=False):
    path = base / 'nes_native_sink165.c'
    assert sha(path) == '2606dedef52e6f0af368b07f53a0abf190da692aa54b44c76b2396dce8ab63f4'
    s = path.read_text()
    if table_first:
        # Keep the section receiver's ascending cursor. Move the entire checked
        # section in front of the remaining map span on warm, reusable frames.
        a=s.index('  /* Canonical raw CHR')
        b=s.index(' bool same=same635',a)
        c=s.index(' if(!span(s,5,0,p->hdma',b)
        d=s.index(' uint8_t descriptor[168]',c)
        emit=s[a:b]+s[c:d]
        emit=once(emit,'size[5]=(uint16_t)(offset+249);','*size=(uint16_t)(offset+249);')
        helper=('static bool section777(struct nes_native_sink165 *s,struct nes_native_video165 *p,uint16_t *size){\n'
                +emit+' return true;\n}\n')
        s=s[:a]+s[b:c]+(' if(!early777 && !section777(s,p,&size[5]))return false;\n')+s[d:]
        s=once(s,'bool nes_sink212_seal(',helper+'bool nes_sink212_seal(')
        s=once(s,' if(!map527(s,p,r->map_upload,false))return false;',""" bool same=same635(s,p);
 bool early777=p->patch_count && same && s->displayed && s->ack635[r->target] &&
               s->ack635[1-r->target] && s->plan && s->plan->bank_history==2;
 if(early777 && !section777(s,p,&size[5]))return false;
 if(!map527(s,p,r->map_upload,false))return false;""")
        # Relocate the existing color-history comparison, keeping the check once.
        pos=s.index(' bool same=same635(s,p);',s.index(' /*719 The ACK'))
        s=s[:pos]+s[pos:].replace(' bool same=same635(s,p);','',1)
        out.mkdir(parents=True,exist_ok=False)
        (out/path.name).write_text(s, encoding='utf8', newline='\n')
        return
    a = s.index(' if(!span(s,5,0,p->hdma')
    b = s.index('  /* Read the enclosing object', a)
    prefix = s[a:b]
    s = s[:a] + ''' if(!early777 && !prefix777(s,p))return false;
 if(p->patch_count){
  unsigned offset=1121;
''' + s[b:]
    fn = '''static bool prefix777(struct nes_native_sink165 *s,const struct nes_native_video165 *p){
''' + prefix + ''' }
 return true;
}
'''
    s = once(s, 'bool nes_sink212_seal(', fn + 'bool nes_sink212_seal(')
    s = once(s, ' /*719 The ACK', ' bool early777=false;\n /*719 The ACK')
    s = once(s, '   unsigned left=w->poll_limit;', '''   /* Publish only final data from the prepared frame, using the original
    * checked dispatcher on each packet. Save the map wait deadline above. */
   if(p->patch_count && s->displayed && s->ack635[r->target] &&
      s->ack635[1-r->target] && same635(s,p)){
    if(!send635(s,p,r->target) || !prefix777(s,p))return false;
    early777=true;
   }
   unsigned left=w->poll_limit;''')
    s = once(s, ' bool same=same635(s,p);',' bool same=early777 || same635(s,p);')
    s = once(s, '  if(!send635(s,p,r->target))return false;', '  if(!early777 && !send635(s,p,r->target))return false;')
    out.mkdir(parents=True,exist_ok=False)
    (out/path.name).write_text(s, encoding='utf8', newline='\n')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('base',type=Path)
    parser.add_argument('out',type=Path)
    parser.add_argument('--table-first',action='store_true')
    args=parser.parse_args()
    prepare(args.base,args.out,args.table_first)
