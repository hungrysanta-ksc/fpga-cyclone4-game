"""Materialize two matched planner variants from the pinned 604 project."""
import argparse
from pathlib import Path
import shutil

from check_nes_wire600 import ROOT, pin, read
from nes_raw506 import once


def prepare(base,out,variant,baseline):
    digest = {'558':'98fe5eeb2d9bfdd7b4be66bc50994b91a88229113dd8f9d4ba5aa3f7ed33f1d9',
              '577':read(ROOT/'analysis/whole580-manifest.json')['artifacts']['firmware'],
              '604':read(ROOT/'analysis/rows604-verification.json')['rows']['firmware_SHA256']}[baseline]
    pin(base/'src/obj-nes-100/firmware.stm',digest)
    shutil.copytree(base,out,ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    src=out/'src'
    f=src/'nes_planner211.c';s=f.read_text()
    old='  unsigned cell=s->maps[(s->rows[first[g]]>>3)*33+x];if(cell>>15)return fail(p,6);'
    if variant in ('slots','recent'):
        # Cache only the last two validated slots in the current group. Palette
        # attributes and dirty tracking still use the original map write.
        s=once(s,'  for(unsigned x=0;x<33;x++){\n'+old,'''  unsigned prior_slot[2];
  for(unsigned x=0;x<33;x++){
  unsigned idx=(s->rows[first[g]]>>3)*33+x,cell=s->maps[idx];if(cell>>15)return fail(p,6);
  unsigned slot;
  if(x>=2 && !exceptional && ((cell^s->maps[idx-2])&8191)==0){
   slot=prior_slot[x&1];
  }else{''')
        s=once(s,'  unsigned slot=nes_resident211_slot(resident,p,key,&q);\n  if(slot>=1024)return fail(p,7);',
               '  slot=nes_resident211_slot(resident,p,key,&q);\n  if(slot>=1024)return fail(p,7);\n  prior_slot[x&1]=slot;\n  }')
        if variant=='recent':
            s=once(s,'unsigned prior_slot[2];','unsigned previous_slot=0,older_slot=0;')
            s=once(s,'slot=prior_slot[x&1];','slot=older_slot;')
            s=once(s,'  prior_slot[x&1]=slot;\n  }','  }\n  older_slot=previous_slot;previous_slot=slot;')
        f.write_bytes(s.encode())
        return
    prefix=variant=='prefix'
    marker='(s->pair607[idx>>3]&(1u<<(idx&7))) && ' if prefix else ''
    s=once(s,old,'''  unsigned idx=(s->rows[first[g]]>>3)*33+x,cell=s->maps[idx];if(cell>>15)return fail(p,6);
  unsigned column=(column225(s->raster[first[g]])+x)&63u;
  unsigned at=((column/32)*1024+g*32+column%32)*2;
  /* Both ordinary cells use the same immutable physical tile. The earlier
   * destination was written in this group; its slot is marked used until SEAL. */
  if(x>=2 && !exceptional && '''+marker+'''((cell^s->maps[idx-2])&8191)==0){
   unsigned c=(column+62)&63u,prior=((c/32)*1024+g*32+c%32)*2;
   unsigned slot=p->map[prior]|((p->map[prior+1]&3u)<<8);
   map_word185(p,at,slot|((bank[g]*4+(cell>>13))<<10)|0x2000);continue;
  }''')
    s=once(s,'  if(slot>=1024)return fail(p,7);\n  unsigned column=(column225(s->raster[first[g]])+x)&63u;\n  unsigned at=((column/32)*1024+g*32+column%32)*2;',
           '  if(slot>=1024)return fail(p,7);')
    f.write_bytes(s.encode())
    if prefix:
        f=src/'nes_native165.h'
        f.write_bytes(once(f.read_text(),' uint16_t maps[1056];',' uint8_t pair607[132];\n uint16_t maps[1056];').encode())
        f=src/'nes_native165.c'
        f.write_bytes(once(f.read_text(),'case 0:s->maps[index]=(uint16_t)v;',
            '''case 0:s->maps[index]=(uint16_t)v;
    if(index>=2 && (((unsigned)v^s->maps[index-2])&8191)==0)
     s->pair607[index>>3]|=1u<<(index&7);
    ''').encode())


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('base',type=Path);p.add_argument('out',type=Path)
    p.add_argument('variant',choices=('direct','prefix','slots','recent'))
    p.add_argument('--baseline',choices=('604','558','577'),default='604')
    a=p.parse_args();prepare(a.base,a.out,a.variant,a.baseline)
