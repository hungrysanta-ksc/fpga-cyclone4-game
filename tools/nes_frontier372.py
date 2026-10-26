# SPDX-License-Identifier: MIT
"""370 protocol/RTL: byte masks and bounded overlap-safe shift copies."""
from nes_delta231 import once

def apply(d,wide=False):
 p=d/'nes_decode280.c';s=p.read_text()
 s=once(s,'for(unsigned i=0;i<64;i++)base[at+i]=base[at+i+2];',
  '{'+''.join(f'base[at+{j}]=base[at+{j+2}];' for j in range(64))+'}')
 s=once(s,'for(unsigned i=66;i>2;i--)base[at+i-1]=base[at+i-3];',
  '{'+''.join(f'base[at+{j}]=base[at+{j-2}];' for j in range(65,1,-1))+'}')
 s=once(s,'for(unsigned i=0;i<len;i++)changes+=(p[1+i/8]>>(i%8))&1;', '''for(unsigned k=0;k<mb;k++){
     unsigned bits=p[1+k];bits-=((bits>>1)&85);
     bits=(bits&51)+((bits>>2)&51);changes+=(bits+(bits>>4))&15;
    }''')
 start=s.index('    for(unsigned i=0;i<len;i++)if(p[1+i/8]&(1<<(i%8))){')
 end=s.index('    if(s->phase==1)s->expanded+=changes;',start)
 s=s[:start]+'''    for(unsigned k=0;k<mb;k++){
     unsigned bits=p[1+k],different=0;
     if(s->phase==1)while(bits){
      unsigned i=8*k+(unsigned)__builtin_ctz(bits);bits&=bits-1;
      base[at+i]=p[j++];
     }else while(bits){
      unsigned i=8*k+(unsigned)__builtin_ctz(bits);bits&=bits-1;
      uint8_t value=p[j++];
      if(s->phase==2&&value>=64)return reject();
      different|=base[at+i]!=value;base[at+i]=value;
     }
     if(s->phase==2&&different)source_groups352|=UINT32_C(1)<<(((index-68)*8+k)%32);
    }
'''+s[end:]
 s=once(s,'for(unsigned j=0;j<256;j++)target_tags367[j]=0;',
  'for(unsigned j=0;j<256;j+=8){'+''.join(f'target_tags367[j+{j}]=0;' for j in range(8))+'}')
 begin=s.index('  for(unsigned i=0;i<r->bg_slots;i++){',s.index('unsigned source_hint367'))
 end=s.index('\n }\n uint16_t tags[7]',begin)
 s=s[:begin]+'''  for(unsigned k=0;k<(r->bg_slots+7u)/8u;k++){
   unsigned bits=r->resident[target][k];
   while(bits){
    unsigned i=k*8+(unsigned)__builtin_ctz(bits);bits&=bits-1;
    if(i>=r->bg_slots)break;
    unsigned tag=r->bg[i];if(tag<8192)target_tags367[tag>>5]|=UINT32_C(1)<<(tag&31);
   }
  }'''+s[end:]
 if wide:
  s=once(s,'for(unsigned g=0;g<32&&n<5;g++)','for(unsigned g=0;g<32&&n<7;g++)')
  s=once(s,'  for(unsigned i=0;i<33&&n<5;i++){','  unsigned checked[2]={8192,8192};\n  for(unsigned i=0;i<33&&n<7;i++){')
  s=once(s,'   if(word&32768)return 0;','''   if(word&32768)return 0;
   if(tag==checked[0]||tag==checked[1])continue;
   checked[1]=checked[0];checked[0]=tag;''')
  s=once(s,'n=add_tag367(tags,n,tag,5);break; /* One causal frontier tag per changed group. */','n=add_tag367(tags,n,tag,7); /* All verified columns,one-call local reuse only. */')
  s=once(s,'if(n&&n<3)for(unsigned i=r->bg_slots;i&&n<3;)', 'if(n&&n<7)for(unsigned i=r->bg_slots;i&&n<7;)')
  s=once(s,'n=add_tag367(tags,n,tag,3);','n=add_tag367(tags,n,tag,7);')
 p.write_text(s,newline='\n')
