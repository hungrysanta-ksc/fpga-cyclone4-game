"""Reuse the validated CHR bitmap and losslessly compact the ROM file-name case table."""
import re
import shutil
from pathlib import Path
from nes_raw506 import once
from nes_blank960 import WORK

ARM=WORK.parent/'nes-mail964'


def ranges(path):
    code=path.read_text(encoding='latin1')
    pattern=r'static const WCHAR tbl_(lower|upper)\[\] = \{([^}]+)\};'
    tables={}
    for name,values in re.findall(pattern,code):
        items=[int(v.strip(),0) for v in values.split(',')]
        assert items[-1]==0 and 0 not in items[:-1]
        tables[name]=items[:-1]
    mapping={}
    for x,y in zip(tables['lower'],tables['upper'],strict=True):
        mapping.setdefault(x,y)
    entries=sorted((x,y) for x,y in mapping.items() if x!=y)
    groups=[]
    i=0
    while i<len(entries):
        x,y=entries[i]
        k=i+1
        step=entries[k][0]-x if k<len(entries) else 1
        while (k<len(entries) and step in (1,2) and entries[k]==(x+(k-i)*step,y+(k-i)*step)):
            k+=1
        groups.append((x,entries[k-1][0],y-x,int(k>i+1 and step==2)))
        i=k
    rebuilt={c:c+d for start,end,d,odd in groups for c in range(start,end+1,1+odd)}
    assert all(mapping.get(c,c)==rebuilt.get(c,c) for c in range(65536))
    start=code.index('static const WCHAR tbl_lower')
    end=code.index('return tbl_lower[i] ? tbl_upper[i] : chr;',start)
    rows=',\n'.join('  {%d,%d,%d,%d}'%g for g in groups)
    replacement='''/* Same FatFS conversion table. A stride-two range preserves the other parity. */
 static const struct { WCHAR first,last; short delta; unsigned char alternate; } ranges[]={
'''+rows+'''
 };
 for(unsigned i=0;i<sizeof ranges/sizeof ranges[0];++i){
   if(chr<ranges[i].first)break;
   if(chr<=ranges[i].last){
     if(!ranges[i].alternate || !((chr-ranges[i].first)&1))return chr+ranges[i].delta;
     break;
   }
 }
 return chr;'''
    path.write_text(code[:start]+replacement+code[end+len('return tbl_lower[i] ? tbl_upper[i] : chr;'):],encoding='latin1',newline='\n')


def prepare():
    link=ARM/'link'
    shutil.copytree(WORK/'link',link)
    src=link/'src'
    ranges(src/'ccsbcs.c')
    header=src/'nes_native165.h'
    header.write_text(once(header.read_text(),'uint8_t obj_check913;',
        'uint8_t obj_check913; uint16_t obj_page_plus_one964;'),newline='\n')
    path=src/'nes_native165.c'
    body=once(path.read_text(),'static bool logical_record(','''/* Called only for an aligned half-word whose eight OBJ kind bits are set. */
static void page964(struct nes_native165 *s,unsigned base){
 unsigned mask=0;
 for(unsigned i=0;i<s->counts[2];++i){
  uint64_t obj=s->objects[i];
  unsigned tag=(unsigned)obj&8191;
  if((tag&~7u)==base && (uint8_t)(obj>>38)==255)mask|=1u<<(tag&7);
 }
 if(mask==255)s->obj_page_plus_one964=base+1;
}
static bool logical_record(''')
    body=once(body,'   while(pending){','''   if(pending && !s->obj_page_plus_one964){
    if((pending&0xaaaau)==0xaaaau)page964(s,t);
    if(!s->obj_page_plus_one964 && (pending&0xaaaa0000u)==0xaaaa0000u)page964(s,t+8);
   }
   while(pending){''')
    path.write_text(body,newline='\n')
    runtime=src/'nes_native_runtime165.c'
    body=once(runtime.read_text(),'static bool planner221(','''extern uint8_t nes_wire_crc807(const uint8_t *,unsigned);
static bool planner221(''')
    runtime.write_text(once(body,' bool ok=nes_native_video211_plan(',''' if(s->plan.bank_history==2 && s->receiver->obj_page_plus_one964){
  unsigned base=s->receiver->obj_page_plus_one964-1;
  uint16_t g=s->receiver->generation;
  uint8_t tx[7]={0xeb,g,g>>8,base,base>>8,0,0xa5},rx[7];
  tx[5]=nes_wire_crc807(tx,5);
  if(!transfer(s,tx,rx,sizeof tx))return false;
 }
 bool ok=nes_native_video211_plan('''),newline='\n')


if __name__=='__main__':
    prepare()
