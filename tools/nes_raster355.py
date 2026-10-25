# SPDX-License-Identifier: MIT
"""Compact raster storage with checked native64 fallback for generic callers."""
from nes_delta231 import once
from nes_compact354 import native as previous

def native(d):
 previous(d)
 p=d/'nes_native165.h';s=p.read_text()
 s=once(s,'uint64_t objects[128],raster[224];uint32_t exceptions[128];','uint64_t objects[128];union {uint64_t raster[224];uint16_t raster355[896];};uint32_t exceptions[128];')
 s=once(s,'uint8_t status183[8];bool ready183;','uint8_t status183[8];bool ready183;bool compact355;uint8_t mask355;')
 helpers='''/* The flag is zero after generic reset/packet reception. Compact admission
 * writes the same bounded storage; every consumer retains native64 checks. */
static inline __attribute__((always_inline)) unsigned raw355(const struct nes_native165 *s,unsigned y){return s->compact355?(s->raster355[y]>>10)&1:(unsigned)(s->raster[y]>>49)&1;}
static inline __attribute__((always_inline)) unsigned slot355(const struct nes_native165 *s,unsigned y){return s->compact355?(s->raster355[y]>>11)&7:(unsigned)(s->raster[y]>>50)&7;}
static inline __attribute__((always_inline)) unsigned epoch355(const struct nes_native165 *s,unsigned y){return s->compact355?(s->raster355[y]>>9)&1:(unsigned)(s->raster[y]>>44)&31;}
static inline __attribute__((always_inline)) unsigned mask355(const struct nes_native165 *s,unsigned y){return s->compact355?s->mask355:(unsigned)(s->raster[y]>>36)&255;}
static inline __attribute__((always_inline)) unsigned column355(const struct nes_native165 *s,unsigned y){return s->compact355?s->raster355[y]&63:(unsigned)(s->raster[y]&31)|((unsigned)(s->raster[y]>>5)&32);}
static inline __attribute__((always_inline)) unsigned fine355(const struct nes_native165 *s,unsigned y){return s->compact355?(s->raster355[y]>>6)&7:(unsigned)(s->raster[y]>>30)&7;}
static inline __attribute__((always_inline)) bool badraw355(const struct nes_native165 *s,unsigned y){return s->compact355?(s->raster355[y]&0xc3ff)!=0:(s->raster[y]>>53)!=0||(s->raster[y]&((UINT64_C(1)<<49)-1))!=0;}
static inline __attribute__((always_inline)) bool badnormal355(const struct nes_native165 *s,unsigned y){return s->compact355?(s->raster355[y]&0xf800)!=0:(s->raster[y]>>49)!=0;}
'''
 s=once(s,'enum {NES_NATIVE165_IDLE',helpers+'\nenum {NES_NATIVE165_IDLE');p.write_text(s,newline='\n')
 p=d/'nes_input286.inc';s=p.read_text()
 s=once(s,' unsigned raw=0,palettes=s->counts[5]/32,mask=p[4320];',' s->compact355=true;s->mask355=p[4320];\n unsigned raw=0,palettes=s->counts[5]/32,mask=p[4320];')
 s=once(s,'s->raster[y]=(UINT64_C(1)<<49)|((uint64_t)raw++<<50);','s->raster355[y]=(uint16_t)v;raw++;')
 s=once(s,'s->raster[y]=(v&31)|((uint64_t)(v&32)<<5)|((uint64_t)((v>>6)&7)<<30)|((uint64_t)mask<<36)|((uint64_t)((v>>9)&1)<<44);','s->raster355[y]=(uint16_t)v;')
 s=once(s,'(input285.raster[y]>>49)&1','raw355(&input285,y)');s=once(s,'((input285.raster[n]>>49)&1)','raw355(&input285,n)');p.write_text(s,newline='\n')
 p=d/'nes_planner211.c';s=p.read_text()
 s=s.replace('static bool patched(', 'static inline __attribute__((always_inline)) bool patched(').replace('static unsigned epoch(', 'static inline __attribute__((always_inline)) unsigned epoch(')
 a=s.index('static unsigned column225(');b=s.index('static bool fail(',a);s=s[:a]+s[b:]
 s=once(s,'((s->raster[y]>>49)&1)!=0','raw355(s,y)!=0');s=once(s,'(unsigned)(s->raster[y]>>44)&31',' epoch355(s,y)')
 s=once(s,'(uint8_t)(s->raster[first_normal]>>36)','(uint8_t)mask355(s,first_normal)')
 s=once(s,'s->raster[y]>>53||(s->raster[y]&((UINT64_C(1)<<49)-1))||((s->raster[y]>>50)&7)!=raw_count','badraw355(s,y)||slot355(s,y)!=raw_count')
 s=once(s,'s->raster[y]>>49||(s->rows[y]>>3)','badnormal355(s,y)||(s->rows[y]>>3)')
 s=once(s,'((s->raster[y]>>36)&255)','mask355(s,y)')
 s=once(s,'((s->raster[y]>>50)&7)','slot355(s,y)')
 s=s.replace('column225(s->raster[first[groups-1]])','column355(s,first[groups-1])').replace('column225(s->raster[first[g]])','column355(s,first[g])')
 s=once(s,'((s->raster[y]>>30)&7)','fine355(s,y)');assert 's->raster[' not in s;p.write_text(s,newline='\n')
 p=d/'nes_delta231.c';s=p.read_text()
 s=once(s,'((s->raster[first]>>49)&1)','raw355(s,first)');s=once(s,'(unsigned)(s->raster[first]>>36)&255','mask355(s,first)')
 s=once(s,'((s->raster[y]>>49)&1)','raw355(s,y)');s=once(s,'((s->raster[n]>>49)&1)','raw355(s,n)');assert 's->raster[' not in s;p.write_text(s,newline='\n')

 # Select representation once at geometry entry; retain native64 generic API.
 p=d/'nes_planner211.c';s=p.read_text();a=s.index('bool geometry286(');b=s.index('bool start286(',a);body=s[a:b]
 fast=body.replace('bool geometry286(', 'static bool geometry_compact355(')
 names={'patched':'raw_fast355','epoch':'epoch_fast355','badraw355':'badraw_fast355','badnormal355':'badnormal_fast355','slot355':'slot_fast355','mask355':'mask_fast355','column355':'column_fast355','fine355':'fine_fast355'}
 for old,new in names.items():fast=fast.replace(old+'(s,',new+'(s,')
 helpers='''static inline unsigned raw_fast355(const struct nes_native165*s,unsigned y){return(s->raster355[y]>>10)&1;}
static inline unsigned epoch_fast355(const struct nes_native165*s,unsigned y){return(s->raster355[y]>>9)&1;}
static inline unsigned slot_fast355(const struct nes_native165*s,unsigned y){return(s->raster355[y]>>11)&7;}
static inline unsigned mask_fast355(const struct nes_native165*s,unsigned y){(void)y;return s->mask355;}
static inline unsigned column_fast355(const struct nes_native165*s,unsigned y){return s->raster355[y]&63;}
static inline unsigned fine_fast355(const struct nes_native165*s,unsigned y){return(s->raster355[y]>>6)&7;}
static inline bool badraw_fast355(const struct nes_native165*s,unsigned y){return(s->raster355[y]&0xc3ff)!=0;}
static inline bool badnormal_fast355(const struct nes_native165*s,unsigned y){return(s->raster355[y]&0xf800)!=0;}
'''
 wrapper='''bool geometry286(const struct nes_native165*s,const uint16_t*lut,struct nes_native_video165*p,struct nes_resident211*r,struct nes_dirty231*d){
 if(s&&s->compact355)return geometry_compact355(s,lut,p,r,d);
 return geometry_dual355(s,lut,p,r,d);
}
'''
 s=s[:a]+body.replace('bool geometry286(', 'static bool geometry_dual355(')+helpers+fast+wrapper+s[b:];p.write_text(s,newline='\n')
