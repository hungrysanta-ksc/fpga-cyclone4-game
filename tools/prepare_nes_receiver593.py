"""Build a fresh 593 trial tree from the pinned 591 ARM source and full link."""
import argparse
import json
import shutil
from pathlib import Path
from nes_raw506 import sha

ROOT = Path(__file__).resolve().parents[1]
PACKET = """
bool nes_native165_packet(struct nes_native165 *s,uint16_t token,const uint8_t *p,unsigned n) {
 if (!s || s->state == NES_NATIVE165_FAILED) return false;
 if (!p || n < 3 || n > 254) return fail(s,19);
 if ((s->token_valid && token != s->next_token) || p[0] != s->r_phase || p[1] != s->r_ord)
  return fail(s,18);
 p += 2; n -= 2;
 switch (s->r_phase) {
 case 0: if (!summaries591(s,p,n)) return fail(s,44); break;
 case 1: if (!rows591(s,p,n)) return fail(s,49); break;
 case 2: case 3:
  if (!nonmap593(s,p,n)) return fail(s,52);
  nes_trace166.generation=s->generation;
  break;
 case 4:
  if (s->state != NES_NATIVE165_PREPARED || n != 8 || get591(p) != 0xf003 ||
      get591(p+2) != s->generation || get32591(p+4) != s->r_active) return fail(s,51);
  s->r_commit=true;
  break;
 default: return fail(s,54);
 }
 s->r_token=token; ++s->r_ord; s->next_token=token+1; s->token_valid=true;
 return true;
}
"""

def prepare(base, out):
    evidence = json.loads((ROOT/'analysis/roles591-verification.json').read_text())
    assert sha(base/'src/obj-nes-100/sd2snes.elf') == evidence['linked_cost']['591']['ELF_sha256']
    for name, digest in evidence['patch']['patched'].items():
        assert sha(base/'src'/name) == digest
    source = (base/'src/nes_native165.c').read_text()
    decode = (ROOT/'tools/nes_decode593.inc').read_text()
    transport = (ROOT/'tools/nes_transport593.inc').read_text()
    # Keep only the established BEGIN, summary/row envelopes and raster recurrence.
    a = source.index('static const unsigned widths')
    source = source[:a] + source[source.index('/* Same unreflected',a):]
    a = source.index('static void canonical591')
    source = source[:a] + source[source.index('static uint64_t raster_next471',a):]
    a = source.index('static bool record(')
    source = source[:a] + source[source.index('static unsigned get591',a):]
    # The packet owner poisons the transaction once, including a short BEGIN.
    begin = source.index('static bool begin591')
    stop = source.index('bool nes_native165_packet',begin)
    region = source[begin:stop]
    import re
    region = re.sub(r'return fail\(s,\d+\);','return false;',region)
    region = region.replace('  s->r_seen|=1u<<row;', '  ++s->at[0];s->r_seen|=1u<<row;')
    region = region.replace('(unsigned)__builtin_popcount(s->r_request)','s->at[0]')
    a = region.index(' s->counts[0]=(uint16_t)count;')
    b = region.index(' s->generation=',a)
    region = region[:a] + ' memcpy(s->counts,p+18,sizeof(s->counts));\n' + region[b:]
    region = region.replace('(count==1056?0xffffffff:(1u<<(count/33))-1)','(UINT32_MAX >> (32-count/33))')
    source = source[:begin] + region + source[stop:]
    a = source.index('static unsigned get591')
    b = source.index('static uint32_t digest591',a)
    # Typed wire fields may be unaligned. These loads follow M4 LE layout.
    source = source[:a] + """
static uint16_t get591(const uint8_t *p){uint16_t v; memcpy(&v,p,sizeof(v)); return v;}
static uint32_t get32591(const uint8_t *p){uint32_t v; memcpy(&v,p,sizeof(v)); return v;}
""" + source[b:]
    a = source.index('static bool begin591')
    source = source[:a] + decode + '\n' + source[a:]
    a = source.index('  for(unsigned i=0;i<33;i++){', source.index('static bool rows591'))
    b = source.index('  ++s->at[0];',a)
    source = source[:a] + '  memcpy(s->maps+at,p+6,66);\n' + source[b:]
    a = source.index('  if(crc16((const uint8_t *)s->maps')
    b = source.index('static void frame(',a)
    source = source[:a] + '  return check_map593(s);\n }\n return true;\n}\n' + PACKET + source[b:]
    a = source.index('static bool request591')
    source = source[:a] + transport + '\n' + source[source.index('void nes_native165_consumed',a):]
    out.mkdir(parents=True,exist_ok=False)
    for name in ('src','utils','verilog'):
        shutil.copytree(base/name,out/name,ignore=shutil.ignore_patterns('obj-nes-100','.dep-nes-100'))
    (out/'src/nes_native165.c').write_bytes(source.encode())
    (out/'NOT-FOR-INSTALL.txt').write_text('ARM receiver experiment with modeled input endpoint.\n')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('base','out'):
        parser.add_argument('--'+name,type=Path,required=True)
    args = parser.parse_args()
    prepare(args.base,args.out)
