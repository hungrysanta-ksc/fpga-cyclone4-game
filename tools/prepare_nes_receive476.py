# SPDX-License-Identifier: MIT
"""Materialize474 plus an equivalent byte CRC16 and sparse required-tag scan."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prepare(base, out):
    pins = json.loads((REPO/'analysis/nrom474-verification.json').read_text(encoding='utf8'))['ARM_changed_inputs']
    for name, digest in pins.items():
        assert sha(base/name) == digest, ('not selected474 source', name)
    out.mkdir(parents=True, exist_ok=False)
    for name in pins:
        shutil.copyfile(base/name, out/name)
    path = out/'nes_native165.c'
    text = path.read_text(encoding='utf8')
    old_crc = 'static uint16_t crc16(const uint8_t *p,unsigned n){uint16_t c=65535;while(n--){c^=(uint16_t)*p++<<8;for(unsigned i=0;i<8;i++)c=(uint16_t)((c<<1)^((c&0x8000)?0x1021:0));}return c;}'
    new_crc = '''/* Same unreflected CCITT(0x1021), initffff, no table/state/check removal. */
static uint16_t crc16(const uint8_t *p,unsigned n){
 uint16_t c=65535;
 while(n--){unsigned x=(c>>8)^*p++;x^=x>>4;c=(uint16_t)((c<<8)^(x<<12)^(x<<5)^x);}
 return c;
}'''
    old_scan = '''  for(unsigned t=0;t<8192;t++){
   unsigned k=need(s,t);if(!k)continue;
   if(s->ntiles>=512)return fail(s,34);
   s->tiles[s->ntiles].tag=(uint16_t)t;
   s->tiles[s->ntiles++].kind=(uint8_t)k;
  }'''
    new_scan = '''  /* Enumerate the same complete bitmap in increasing tag order. Explicit
   * little-lane assembly avoids alignment, aliasing and host-endian assumptions.
   * ctz is used only for nonzero words; kind2 starts at the odd bit of its pair. */
  for(unsigned t=0;t<8192;t+=16){
   const uint8_t *b=&s->required[t>>2];
   uint32_t pending=(uint32_t)b[0]|((uint32_t)b[1]<<8)|((uint32_t)b[2]<<16)|((uint32_t)b[3]<<24);
   while(pending){
    unsigned shift=(unsigned)__builtin_ctz(pending)&~1u;
    unsigned k=(pending>>shift)&3u;
    if(s->ntiles>=512)return fail(s,34);
    s->tiles[s->ntiles].tag=(uint16_t)(t+(shift>>1));
    s->tiles[s->ntiles++].kind=(uint8_t)k;
    pending&=~(UINT32_C(3)<<shift);
   }
  }'''
    for old, new in [(old_crc, new_crc), (old_scan, new_scan)]:
        assert text.count(old) == 1, '476 replacement boundary changed'
        text = text.replace(old, new)
    path.write_text(text, encoding='utf8', newline='\n')
    manifest = {'baseline':'ARM474-02', 'base':pins,
                'generated':{name:sha(out/name) for name in pins},
                'scope':__doc__, 'unchanged':'wire2232, every logical record guard, missing/count/slot checks, CRC comparison, POP/retire, STOP/finalACK/EA, FPGA471'}
    (out/'preparation.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.base, args.out)
    print(json.dumps({'generated':len(result['generated']), 'changed':[n for n in result['base'] if result['base'][n]!=result['generated'][n]]}))
