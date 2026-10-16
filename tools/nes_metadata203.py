# SPDX-License-Identifier: MIT
"""Paired 2031 metadata ingress, without a second CHR pixel copy.

The receiver derives a complete sorted tag/kind set from checked geometry.
This authorizes plans, not source bytes: board201/192 must still enforce the
exported immutable CHR-ROM epoch. Never deploy against the old1813 exporter.
"""
from pathlib import Path
import argparse,json
from nes_runtime202 import ROOT,BASE,prepare as runtime,sha
from nes_clip178 import replace

def prepare(out):
 out=Path(out);r=runtime(out);pins=r['source_pins']
 f=out/'nes_native165.h';s=f.read_text()
 s=replace(s,'uint8_t kind,data[16];','uint8_t kind;')
 s=s.replace('Required CHR bitmap becomes raw pixels ONLY after CHR_END validation.',
             'Required tag/kind bitmap becomes raw ONLY after META_END validation.')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_native165.c';s=f.read_text().replace('0x1813','0x2031')
 s=replace(s,'s->bytes||s->lane||s->missing)return fail(s,29);','s->bytes||s->lane||s->ntiles||s->bytes)return fail(s,29);')
 s=replace(s,'  s->next_kind=7;s->last_tile=0;return true;', '''  /* Geometry is complete, including raw-slot validation. Build exactly the
   * required tags before reusing the bitmap; no byte-payload claim is made. */
  if(s->missing>512)return fail(s,34);
  for(unsigned t=0;t<8192;t++){
   unsigned k=need(s,t);if(!k)continue;
   if(s->ntiles>=512)return fail(s,34);
   s->tiles[s->ntiles].tag=(uint16_t)t;
   s->tiles[s->ntiles++].kind=(uint8_t)k;
  }
  if(s->ntiles!=s->missing)return fail(s,34);
  s->missing=0;s->next_kind=7;s->last_tile=0;return true;''')
 start=s.index(' }else{\n  unsigned lane=');end=s.index('\n s->records++;return true;',start)
 s=s[:start]+''' }else return fail(s,35); /*2031 forbids pre-META_END CHR payload. */'''+s[end:]
 s=s.replace('/*181 Candidate: materialize alongside the paired header as nes_native165.c.\n * Old1741 and new1811 records are intentionally incompatible. */',
 '''/*2031 paired metadata-only ingress. Geometry proves required addresses and
 * usages; immutable source lifetime is separately enforced by board201/192. */''')
 s=s.replace('before every need is satisfied.','before every geometry requirement has been enumerated.')
 s=s.replace('/*1813 Compressed records','/*2031 Compressed records')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_plan191.c';s=f.read_text()
 s=replace(s,'static const uint8_t *tile(', 'static const struct nes_native165_tile *tile(')
 s=replace(s,'return s->tiles[i].data;','return &s->tiles[i];')
 f.write_text(s,encoding='utf8',newline='\n')
 f=out/'nes_native_runtime165.c';s=f.read_text().replace('Old checked CHR ingress is intentionally retained until board format changes.',
 'Paired2031 ingress derives tag/kind metadata; no duplicate CHR payload.')
 f.write_text(s,encoding='utf8',newline='\n')
 # The obsolete converter is not linked into RUN, but the full tree still
 # compiles it. Keep only an explicit unavailable API; never synthesize pixels
 # from uninitialized/nonexistent tile data. The191 planner is the sole path.
 f=out/'nes_native_video165.c';s=f.read_text();start=s.index('bool nes_native_video185_build(')
 f.write_text('''/* SPDX-License-Identifier: MIT */
#include "nes_native_video165.h"
bool nes_native_video185_build(const struct nes_native165 *s,const uint16_t lut[64],struct nes_native_video165 *p,bool inherit,nes_native_video165_stage_fn fn,void *ctx){
 (void)s;(void)lut;(void)inherit;(void)fn;(void)ctx;
 if(p){p->valid=false;p->error=16;}return false;
}
bool nes_native_video165_build(const struct nes_native165 *s,const uint16_t lut[64],struct nes_native_video165 *p,nes_native_video165_stage_fn fn,void *ctx){
 return nes_native_video185_build(s,lut,p,false,fn,ctx);
}
''',encoding='utf8',newline='\n')
 src=BASE/'probes/nes-window184-coupled/evidence/route02/nes_native_export181.sv'
 s=src.read_text();pins[src.relative_to(BASE).as_posix()]=sha(src)
 s=s[s.index('// SPDX-License-Identifier: MIT'):]
 start=s.index('//181 New1811');end=s.index('module ',start)
 s=s[:start]+'//2031 metadata/raw only; source bytes belong to the exported201 lease.\n'+s[end:]
 s=s.replace('nes_native_export181','nes_native_export203').replace("16'h1813","16'h2031")
 start=s.index(' output wire fill_start,');end=s.index(' output reg tx_valid',start);s=s[:start]+s[end:]
 s=s.replace(',FSTART=5,FDATA=6','').replace('CHR_END','META_END')
 s=s.replace('reg [3:0] fill_detail;reg [2:0] patches;','reg [2:0] patches;')
 s=s.replace('assign query_generation=generation;assign fill_start=state==FSTART&&live;\n assign byte_ready=state==FDATA&&live&&tx_ready&&byte_generation==generation;','assign query_generation=generation;')
 s='\n'.join(l for l in s.splitlines() if 'FDATA:if(byte_valid' not in l)+'\n'
 s=s.replace("56'd0,fill_detail,error","60'd0,error").replace("fill_detail<=reason==4?fill_error:4'd0;",'').replace('fill_detail<=0;','')
 s=s.replace('state<=FSTART','state<=META_END')
 start=s.index('    FSTART:');end=s.index('    META_END:',start);s=s[:start]+s[end:]
 s=s.replace('!fill_busy&&(!frame_owned||frame_generation!=generation)','(!frame_owned||frame_generation!=generation)')
 assert 'fill_' not in s and 'byte_' not in s
 (out/'nes_native_export203.sv').write_text(s,encoding='utf8',newline='\n')
 pins['repository-nes-milestone/tools/nes_metadata203.py']=sha(Path(__file__))
 r.update(source_pins=pins,generated={p.name:sha(p) for p in out.iterdir() if p.is_file() and p.suffix in ('.c','.h','.inc','.sv')},
          old_chr_ingress_retained=False,wire_version='2031',source_epoch_board_integration=False)
 (out/'preparation203.json').write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');return r

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);a=p.parse_args();print(json.dumps(prepare(a.out)))
