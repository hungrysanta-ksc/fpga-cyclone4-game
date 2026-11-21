"""Validate packed row and palette runs once before expanding their byte lanes."""
import argparse
from pathlib import Path

from check_nes_strip869 import digest
from nes_raw506 import once


def prepare(base, patch, wire=False, shared=False, ack=False):
    assert digest(base / 'obj-nes-100/firmware.stm') == '55ab84f51452876ce214f8c4db92d767eeb381259c3bf5f090ae133bd2a4cd84'
    name = 'nes_native165.c'
    if wire:
        # The packet reader validated the full eight-byte record. Use its
        # wire-order bytes directly instead of assembling then shifting a u64.
        original = (base / name).read_text()
        first = original.index('  unsigned left=s->counts[k]-s->at[k];')
        last = original.index(' }else return fail(s,33);', first)
        text = original[:first] + '  return fail(s,33); /* Byte runs are consumed directly at ingress. */\n' + original[last:]
        text = once(text,'   case 1:if((v>>3)>=s->counts[0]/33u)return fail(s,10);s->rows[index]=(uint8_t)v;break;\n','')
        text = once(text,'   case 5:s->palette[index]=(uint8_t)v;break;','   case 1:case 5:return fail(s,33);')
        text = once(text,'  uint64_t value=0;for(unsigned j=0;j<width;j++)value=(value<<8)|p[pos++];',
            '''  if(kind==7 && ((index>>8)==0x19 || (index>>8)==0x1d)){
   unsigned k=(index>>8)&7, count=(index&255)+1, start=s->at[k];
   if(s->state!=NES_NATIVE165_RECEIVING || gen!=s->generation ||
      s->next_kind==7 || start>s->counts[k])return fail(s,33);
   unsigned left=s->counts[k]-start;
   if(count!=(left>8?8:left))return fail(s,33);
   while(width>count){if(p[pos++])return fail(s,33);width--;}
   while(s->next_kind<6 && s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;
   if(k!=s->next_kind)return fail(s,9);
   unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
   uint8_t *dst=k==1?s->rows:s->palette;
   while(count--){
    unsigned byte=p[pos++];
    if(byte>=limit)return fail(s,k==1?10:9);
    dst[s->at[k]++]=(uint8_t)byte;
    s->records++;
   }
   nes_trace166_record(s,kind,gen,index,0);
   continue;
  }
  uint64_t value=0;for(unsigned j=0;j<width;j++)value=(value<<8)|p[pos++];''')
    elif shared:
        text=(base/name).read_text()
        first=text.index('static unsigned need(')
        last=text.index('/* Validate capacity',first)
        text=text[:first]+'''static void require_tile(struct nes_native165 *s,unsigned t,unsigned kind){
 unsigned shift=(t&3)*2;
 uint8_t *slot=s->required+(t>>2);
 if(!(*slot&(3u<<shift)))s->missing++;
 *slot|=kind<<shift;
}
'''+text[last:]
        text=once(text,'uint32_t pending=(uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);',
                  'uint32_t pending; memcpy(&pending,b,sizeof(pending));')
        # Keep the existing per-lane state, ordering, and value checks. The
        # bytes already sit in big-endian order inside the checked D1 payload.
        text=once(text,'static bool record(struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t v){',
                  'static bool record(struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t v,const uint8_t *end){')
        text=once(text,'(v>>(8*(n-1-i)))&255','(end-n)[i]')
        text=once(text,'record(s,kind,gen,index,value))return false;', 'record(s,kind,gen,index,value,p+pos))return false;')
    elif ack:
        name='nes_native_runtime165.c'
        text=once((base/name).read_text(),
                  'reason==2 && r->state==NES_NATIVE165_COMPLETE ? 84u*96u : 84u*128u',
                  'reason==2 && r->state==NES_NATIVE165_COMPLETE ? 0 : 84u*128u')
    else:
        text = once((base/name).read_text(),
            '  for(unsigned i=0;i<n;i++)if(!logical_record(s,k,gen,start+i,(v>>(8*(n-1-i)))&255))return false;',
            '''  while(s->next_kind<6 && s->at[s->next_kind]==s->counts[s->next_kind])s->next_kind++;
  if(s->next_kind!=k)return fail(s,9);
  unsigned limit=k==1?(s->counts[0]/33u)*8u:64u;
  uint8_t *dst=k==1?s->rows:s->palette;
  for(unsigned i=0;i<n;i++){
   unsigned byte=(uint8_t)(v>>(8*(n-1-i)));
   if(byte>=limit)return fail(s,k==1?10:9);
   dst[s->at[k]++]=(uint8_t)byte;
   s->records++;
  }''')
    patch.mkdir(parents=True)
    (patch/name).write_text(text,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path)
    p.add_argument('patch',type=Path)
    policy=p.add_mutually_exclusive_group()
    policy.add_argument('--wire',action='store_true')
    policy.add_argument('--ack',action='store_true')
    policy.add_argument('--shared',action='store_true')
    prepare(**vars(p.parse_args()))
