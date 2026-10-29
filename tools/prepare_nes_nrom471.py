# SPDX-License-Identifier: MIT
"""Prepare paired471 compact map runs and normal-scroll raster spans on457."""
import argparse,shutil,json
from pathlib import Path
from nes_delta231 import BASE,ROOT,sha
p=argparse.ArgumentParser();p.add_argument('--board',required=True,type=Path);p.add_argument('--out',required=True,type=Path);a=p.parse_args();d=a.out.resolve();assert not d.exists();d.mkdir(parents=True)
shutil.copytree(a.board,d/'board',ignore=shutil.ignore_patterns('db','incremental_db','output_files','work','simulation','*.wlf'))
(d/'arm').mkdir();shutil.copyfile(BASE/'probes/nes-nrom418/arm01/src/nes_native165.c',d/'arm/nes_native165.c')
def once(s,old,new):assert s.count(old)==1,(old[:100],s.count(old));return s.replace(old,new,1)
f=d/'board/nes_native_export203.sv';s=f.read_text();s=once(s,'reg [8:0] pack_count;reg map_repeat;','reg [8:0] pack_count;reg map_repeat;reg [14:0] scroll_next;\n function automatic [14:0] next_y(input [14:0] v);\n  reg [14:0] t;begin t=v;if(v[14:12]!=7)t=v+15\'h1000;\n  else begin t[14:12]=0;if(v[9:5]==29)begin t[9:5]=0;t[11]=!v[11];end\n   else if(v[9:5]==31)t[9:5]=0;else t[9:5]=v[9:5]+1\'b1;end next_y=t;end\n endfunction')
s=once(s,'else if(pack_count!=1)', '''else if(query_kind==0 && map_repeat)
     tx_data={3'd6,generation,5'b10000,count_minus_one,48'd0,held_data[15:0]};
    else if(query_kind==4 && pack_count!=1 && !map_repeat)
     tx_data={3'd7,generation,2'b11,3'd4,count_minus_one,held_data};
    else if(pack_count!=1)''')
s=once(s,'16\'h2231','16\'h2232');s=once(s,'held_data<=0;header<=0;cycles<=0;', 'held_data<=0;header<=0;cycles<=0;scroll_next<=0;')
s=once(s,'end else if(pack_count==0)begin\n      held_data<=data;', '''end else if(query_kind==4)begin
      if(pack_count==0)begin held_data<=data;pack_count<=1;map_repeat<=0;
       scroll_next<=next_y(data[14:0]);query_index<=query_index+1'b1;state<=ASK;end
      else if(data==held_data && (map_repeat||pack_count==1) && pack_count<256)begin
       map_repeat<=1;pack_count<=pack_count+1'b1;query_index<=query_index+1'b1;state<=ASK;end
      else if(!map_repeat && data[63:15]==held_data[63:15] && !data[49] &&
              data[14:0]==scroll_next && pack_count<256)begin
       scroll_next<=next_y(data[14:0]);pack_count<=pack_count+1'b1;
       query_index<=query_index+1'b1;state<=ASK;end
      else state<=VALUE;
     end else if(pack_count==0)begin
      held_data<=data;''')
f.write_text(s,encoding='utf8',newline='\n')
f=d/'arm/nes_native165.c';s=f.read_text();s=once(s,'(v>>48)!=0x2231','(v>>48)!=0x2232')
s=once(s,'static bool record(struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t v){', '''static uint64_t raster_next471(uint64_t v){
 unsigned lo=(unsigned)v&32767;
 if((lo&0x7000)!=0x7000)lo+=0x1000;
 else {lo&=~0x7000u;unsigned y=(lo>>5)&31;
  if(y==29){lo&=~0x3e0u;lo^=0x800;}else if(y==31)lo&=~0x3e0u;else lo+=32;}
 return (v&~UINT64_C(32767))|lo;
}
static bool record(struct nes_native165 *s,unsigned kind,unsigned gen,unsigned index,uint64_t v){
 if(kind==6 && (index&0x1f00)==0x1000){
  unsigned n=(index&255)+1,start=s->at[0];
  if(s->state!=NES_NATIVE165_RECEIVING||gen!=s->generation||s->next_kind!=0||
     n<2||n>(unsigned)s->counts[0]-start||v>>15)return fail(s,37);
  for(unsigned i=0;i<n;i++)if(!logical_record(s,0,gen,start+i,v))return false;
  return true;
 }
 if(kind==7 && (index&0x1f00)==0x1c00){
  unsigned n=(index&255)+1,start=s->at[4];
  if(s->state!=NES_NATIVE165_RECEIVING||gen!=s->generation||s->next_kind>4||
     n<2||n>(unsigned)s->counts[4]-start||v>>49)return fail(s,38);
  for(unsigned i=0;i<n;i++){
   if(!logical_record(s,4,gen,start+i,v))return false;
   v=raster_next471(v);
  }
  return true;
 }''')
f.write_text(s,encoding='utf8',newline='\n')
shutil.copyfile(ROOT/'src/nes/experimental471/nes_rom_spi.sv',d/'board/nes_rom_spi.sv')
r={'paired_wire_header':'2232','base':'457/418','modified':{'nes_native_export203.sv':sha(d/'board/nes_native_export203.sv'),'nes_native165.c':sha(f),'nes_rom_spi.sv':sha(d/'board/nes_rom_spi.sv')},'scope':'compact map repeat payload and exact NES normal vertical-scroll spans; per-blockCRC, D2/D3, finalACK and STOP unchanged; no history reuse'};(d/'preparation.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r))
