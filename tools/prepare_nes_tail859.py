"""Repartition the bounded HDMA tail using the existing DATA and repeat ABI."""
import argparse
from prepare_nes_seal858 import ROOT as BASE
from nes_raw506 import once

ROOT = BASE.with_name('nes-tail859')


def prepare(variant):
    source = BASE/'link-c/src/nes_native_sink165.c'
    text = source.read_text()
    start = text.index('  if(!span(s,5,offset,raw,packed))')
    end = text.index('  size[5]=', start)
    table = '  const uint8_t *tables=(const uint8_t *)p+__builtin_offsetof(struct nes_native_video165,patch.mode);\n'
    if variant == 'a':
        prefix = '''  if(!span(s,5,offset,raw,packed))return false;
  offset+=packed;
  if(!packet(s,2,5,offset,tables,9))return false;
'''
    elif variant == 'b':
        prefix = '''  /* Keep the complete legacy CHR stream for the full-width case. */
  if(packed==2048){
   if(!span(s,5,offset,raw,packed))return false;
   if(!packet(s,2,5,offset+packed,tables,9))return false;
  }else{
   /* Compact CHR already occupies expired BG keys. Append nine bytes only
    * after production finishes. Both sends copy synchronously. */
   unsigned suffix=64;
   if(!span(s,5,offset,raw,packed-suffix))return false;
   memcpy((uint8_t *)p->bg_keys+4096+packed,tables,9);
   if(!packet(s,2,5,offset+packed-suffix,raw+packed-suffix,suffix+9))return false;
  }
  offset+=packed;
'''
    else:
        count = 64 if variant in ('c','f') else 192
        prefix = f'''  /* Both the canonical raw array and the compact source precede this
   * expired-key workspace. The last literal can cross the CHR/table boundary. */
  unsigned prefix=packed-{count};
  if(prefix && !span(s,5,offset,raw,prefix))return false;
  uint8_t *joined=(uint8_t *)p->bg_keys+6144;
  memcpy(joined,raw+prefix,{count});
  memcpy(joined+{count},tables,9);
  if(!packet(s,2,5,offset+prefix,joined,{count+9}))return false;
  offset+=packed;
'''
    tail = '''  /* This workspace already holds compact CHR. All its submissions have
   * copied the payload before the first write below. Skip the C padding
   * between patch.enable and patch.size. */
  uint8_t *tail=(uint8_t *)p->bg_keys+4096;
  memcpy(tail,tables+9,234);
  memcpy(tail+234,p->patch.size,6);
  if(!packet(s,2,5,offset+9,tail,240))return false;
'''
    if variant == 'g':
        prefix = '''  /* One contiguous wire image, outside both source regions. Its
   * 441 bytes fit even when all 2,048 canonical CHR bytes are live. */
  unsigned prefix=packed-192;
  if(prefix && !span(s,5,offset,raw,prefix))return false;
  offset+=prefix;
  uint8_t *joined=(uint8_t *)p->bg_keys+6144;
  memcpy(joined,raw+prefix,192);
  memcpy(joined+192,tables,243);
  memcpy(joined+435,p->patch.size,6);
  if(!packet(s,2,5,offset,joined,201))return false;
  if(!packet(s,2,5,offset+201,joined+201,240))return false;
  offset+=192;
'''
        tail = ''
    text = once(text, text[start:end], table+prefix+tail)
    if variant in ('e','f'):
        text = once(text, 'for(unsigned i=0;i<4;i++)b[4+i]=(uint8_t)(s->serial>>(i*8));',
                    'memcpy(b+4,&s->serial,4);')
        text = once(text, 'for(unsigned i=0;i<4;i++){b[4+i]=(uint8_t)(s->serial>>(8*i));b[8+i]=(uint8_t)(r->epoch>>(8*i));}',
                    'memcpy(b+4,&s->serial,4);memcpy(b+8,&r->epoch,4);')
        text = once(text, 'for(unsigned i=0;i<6;i++)put16(descriptor+i*2,size[i]);',
                    'memcpy(descriptor,size,sizeof size);')
    out = ROOT/f'patch-{variant}'
    out.mkdir(exist_ok=True,parents=True)
    (out/source.name).write_text(text)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('variant', choices=list('abcdefg'))
    prepare(p.parse_args().variant)
