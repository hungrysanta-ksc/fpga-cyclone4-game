# SPDX-License-Identifier: MIT
"""Executable N5-v3 byte-run source; no placeholder CRC or geometry trailer."""
import binascii,struct
from nes_delta231 import ROOT,once
from probe_nes_decode280 import encode280

REGIONS=[(0,2112),(2112,224),(3360,512),(3872,448),(4320,1),(4321,64),(4385,13),(2336,1024),(4398,512)]

def runs(rid,old,new,cold):
    # Streaming hardware policy: one seed, <=64-byte literal scratch, no
    # lookahead into a future query. Repeat starts with two equal bytes.
    out=[];i=0
    if rid==3:
        for i in range(0,len(new),64):
            v=new[i:i+64]
            if not cold and old[i:i+64]==v:continue
            rep=v==v[:2]*(len(v)//2)
            out.append(bytes([67])+struct.pack('<H',i)+bytes([(128 if rep else 0)+len(v)-1])+(v[:2] if rep else v))
        return out
    while i<len(new):
        if not cold and old[i]==new[i]:i+=1;continue
        j=i+1;repeat=False
        if j<len(new) and new[j]==new[i]:
            repeat=True
            while j<min(i+64,len(new)) and new[j]==new[i]:j+=1
        else:
            while j<min(i+64,len(new)) and (cold or old[j]!=new[j]):j+=1
        out.append(bytes([64+rid])+struct.pack('<H',i)+bytes([(64 if repeat else 0)+j-i-1])+new[i:i+1 if repeat else j])
        i=j
    return out

def encode340(old,new,raw,prior_raw,serial,generation):
    ref=encode280(old,new,raw,prior_raw,serial,generation)
    header=bytearray(ref[0]);header[2]=3
    maps=[r for r in ref[1:] if r[:3]!=b'\xff\xff\0' and (r[0]&127)<32]
    rr=[bytes(header),*maps];cold=bool(header[3]&1)
    expanded=0
    for r in maps:expanded+=66 if r[0]&128 else len(r)-10
    spans=len(maps)
    for rid in range(1,9):
        at,n=REGIONS[rid]
        before=(prior_raw or bytes(len(raw))) if rid==8 else old[at:at+n]
        after=raw if rid==8 else new[at:at+n]
        items=runs(rid,before,after,bool(header[3]&2) if rid==8 else cold)
        rr+=items
        if rid<7:
            spans+=len(items);expanded+=sum((r[3]&63)+1 for r in items)
        if rid==6:rr.append(b'\xff\xff\0\3'+struct.pack('<HHH',spans,expanded,0))
    rr.append(b'\xff\xff\0\4\0\0')
    result=[];crc=65535
    for r in rr:
        trailer=r[:4] in (b'\xff\xff\0\3',b'\xff\xff\0\4')
        crc=binascii.crc_hqx(r[:-2] if trailer else r,crc)
        result.append(r[:-2]+struct.pack('<H',crc) if trailer else r)
    return result

def decoder():
    s=(ROOT/'tools/nes_decode280.c').read_text()
    s=s.replace('uint8_t valid,phase,cold,raw_cold,blocks,raw_blocks,prior_raw;',
                'uint8_t valid,phase,cold,raw_cold,blocks,raw_blocks,prior_raw,region; uint16_t ends[9];')
    s=s.replace("p[2]!=2","p[2]!=3")
    s=once(s,'s->last=-1;s->phase=1;take=ci=20;', 's->last=-1;s->phase=1;s->region=0;for(unsigned r=0;r<9;r++)s->ends[r]=0;take=ci=20;')
    s=once(s,'(s->cold&&s->blocks!=68)', '(s->cold&&(s->blocks!=32||s->ends[1]!=224||s->ends[2]!=512||s->ends[3]!=448||s->ends[4]!=1||s->ends[5]!=64||s->ends[6]!=13))')
    s=once(s,'s->phase=2;s->last=67;', 's->phase=2;s->region=6;')
    s=once(s,'(s->raw_cold&&s->raw_blocks!=s->raw_count/64)', '(s->cold&&s->ends[7]!=1024)||(s->raw_cold&&s->ends[8]!=s->raw_count)')
    # Parenthesize whole END condition after adding independent cold domains.
    s=s.replace('if(n!=6||(s->cold&&s->ends[7]!=1024)||(s->raw_cold&&s->ends[8]!=s->raw_count))', 'if(n!=6||(s->cold&&s->ends[7]!=1024)||(s->raw_cold&&s->ends[8]!=s->raw_count))')
    anchor='  }else{\n   unsigned index=p[0]&127,at,len;'
    s=once(s,anchor,'''  }else if(p[0]>=65&&p[0]<=72){
   static const uint16_t starts[9]={0,2112,3360,3872,4320,4321,4385,2336,4398};
   static const uint16_t sizes[9]={2112,224,512,448,1,64,13,1024,512};
   unsigned r=p[0]-64;
   if(n<5||r<s->region||(s->phase==1?r>6:r<7))return reject();
   unsigned at=u16(p+1),count=(p[3]&63)+1,mode=p[3]>>6;
   unsigned limit=r==8?s->raw_count:sizes[r],cold=r==8?s->raw_cold:s->cold;
   if(mode>2||(mode==2&&(r!=3||(at&1)||(count&1)))||at<s->ends[r]||at+count>limit||(cold&&at!=s->ends[r]))return reject();
   take=ci=4+(mode==2?2:mode?1:count);if(n<take)return reject();
   for(unsigned i=0;i<count;i++){
    uint8_t v=p[4+(mode==2?(i&1):mode?0:i)];if(r==8&&v>=64)return reject();
    base[starts[r]+at+i]=v;
   }
   s->region=(uint8_t)r;s->ends[r]=(uint16_t)(at+count);
   if(s->phase==1){s->spans++;s->expanded+=count;}
  }else{
   unsigned index=p[0]&127,at,len;''')
    s=once(s,'if(index>=68)return reject();', 'if(index>=32||s->region)return reject();')
    a=s.index('   }else{\n    if(index<68');b=s.index('   s->last=index;',a)
    s=s[:a]+'   }else return reject();\n'+s[b:]
    return s

def apply(d):
    p=d/'nes_core257.sv';s=p.read_text()
    s=once(s,'{H,MASK,SHIFT,GEO,ENDREC}', '{H,MASK,SHIFT,GEO,ENDREC,RUN340}')
    s=once(s,' reg seal_state;', ''' reg [3:0] region340;
 reg [6:0] run340;reg repeat340,pending340;
 reg [7:0] seed340;reg [10:0] offset340;
 reg [12:0] region_base340,region_end340;
 always @*begin
  case(region340)
   0:begin region_base340=0;region_end340=2112;end
   1:begin region_base340=2112;region_end340=2336;end
   2:begin region_base340=3360;region_end340=3872;end
   3:begin region_base340=3872;region_end340=4320;end
   4:begin region_base340=4320;region_end340=4321;end
   5:begin region_base340=4321;region_end340=4385;end
   6:begin region_base340=4385;region_end340=4398;end
   7:begin region_base340=2336;region_end340=3360;end
   default:begin region_base340=4398;region_end340=4398+raw_limit;end
  endcase
 end
 wire equal340=new_byte==seed340;
 wire repeat_next340=repeat340||(run340==1&&equal340);
 wire stop_run340=region340!=0&&run340!=0&&
   !(repeat340?equal340:(run340==1&&equal340)||changed);
 wire [6:0] count340=run340+7'd1;
 reg seal_state;''')
    s=once(s,'wire base_we=live&&state==FSTORE;', 'wire base_we=live&&state==FSTORE&&!stop_run340;')
    s=once(s,'((!raw_mode&&q_cursor<4385&&q_cursor!=4320)||(raw_mode&&q_cursor<4398+raw_limit))', '(q_cursor<region_end340&&region340!=4&&region340!=6)')
    s=once(s,'wire q_synthetic=!raw_mode&&(cursor==4320||cursor>=4385);','wire q_synthetic=region340==4||region340==6;')
    # Region-local query ownership replaces chained global-byte thresholds.
    a=s.index('  if(raw_mode)begin q_section=7;');b=s.index('  else begin\n   q_first=0;',a)
    s=s[:a]+'''  if(region340==8)begin q_section=7;q_index=q_cursor-4398;q_active=1;end
  else if(region340==0)begin q_section=0;q_index=q_cursor[11:1];q_first=!q_cursor[0];q_active=q_index<q_maps;end
  else if(region340==1)begin q_section=1;q_index=q_cursor-2112;q_active=1;end
  else if(region340==7)begin q_section=2;q_index=(q_cursor-2336)>>3;q_first=q_cursor[2:0]==0;q_active=q_index<q_objects;end
  else if(region340==2)begin q_section=3;q_index=(q_cursor-3360)>>2;q_first=q_cursor[1:0]==0;q_active=q_index<q_exceptions;end
  else if(region340==3)begin q_section=4;q_index=(q_cursor-3872)>>1;q_first=!q_cursor[0];q_active=1;end
  else if(region340==4)begin q_value=q_mode;q_first=0;end
  else if(region340==5)begin q_section=5;q_index=q_cursor-4321;q_active=q_index<q_palettes;end
'''+s[b:]
    s=once(s,'2:header_byte=2;', '2:header_byte=3;')
    s=once(s,'   FSTORE:begin\n    a_addr=', '   FSTORE:if(region340==0)begin\n    a_addr=')
    s=once(s,'   GEOTRAILER,ENDTRAILER:begin', '''   else begin
    a_addr={2'd0,run340};a_we=!stop_run340&&(run340!=0||changed);a_w=new_byte;
   end
   GEOTRAILER,ENDTRAILER:begin''')
    s=once(s,'  case(state)\n   HEADER:', '  if(kind==RUN340)a_addr={1\'b0,rec_i}-9\'d4;\n  case(state)\n   HEADER:')
    s=once(s,'  if(kind==GEO||kind==ENDREC)begin', '''  if(kind==RUN340)case(rec_i)
   0:out_byte=8'd64+{4'd0,region340};
   1:out_byte=offset340[7:0];2:out_byte={5'd0,offset340[10:8]};
   3:out_byte={1'b0,repeat340,6'd0}+{1'b0,run340}-8'd1;
   default:if(repeat340)out_byte=seed340;
  endcase
  if(kind==GEO||kind==ENDREC)begin''')
    a=s.index(' task automatic next_block;');b=s.index(' always @(posedge clk)begin\n  if(reset)',a)
    s=s[:a]+''' task automatic next_region340;
  begin
   run340<=0;repeat340<=0;pending340<=0;q_have<=0;q_pending<=0;state<=FETCH;
   case(region340)
    0:begin region340<=1;cursor<=2112;end
    1:begin region340<=2;cursor<=3360;end
    2:begin region340<=3;cursor<=3872;end
    3:begin region340<=4;cursor<=4320;end
    4:begin region340<=5;cursor<=4321;end
    5:begin region340<=6;cursor<=4385;end
    6:begin build_i<=0;state<=GEOTRAILER;end
    7:begin region340<=8;raw_mode<=1;cursor<=4398;
      if(!raw_limit)begin build_i<=0;state<=ENDTRAILER;end
    end
    default:begin build_i<=0;state<=ENDTRAILER;end
   endcase
  end
 endtask
 task automatic next_block;
  begin
   if(cursor==2112)next_region340();
   else begin block_id<=block_id+1'b1;row_i<=0;diff_count<=0;mask_acc<=0;
    left_row<=1;right_row<=1;state<=FETCH;end
  end
 endtask
 task automatic emit_run340(input [6:0] n,input rep);
  begin
   run340<=n;repeat340<=rep;
   if(region340<7)begin spans<=spans+1'b1;expanded<=expanded+{9'd0,n};end
   emit_record(RUN340,rep?8'd5:{1'b0,n}+8'd4);
  end
 endtask
'''+s[b:]
    s=once(s,'   state<=IDLE;external_range<=0;', '   region340<=0;run340<=0;repeat340<=0;pending340<=0;seed340<=0;offset340<=0;\n   state<=IDLE;external_range<=0;')
    s=once(s,'      cursor<=0;block_id<=0;', '      region340<=0;run340<=0;repeat340<=0;pending340<=0;cursor<=0;block_id<=0;')
    s=once(s,'    FSTORE:begin\n     cursor<=', '''    FSTORE:if(region340!=0)begin
     if(stop_run340)begin pending340<=1;emit_run340(run340,repeat340);end
     else begin
      cursor<=cursor+1'b1;
      if(run340!=0||changed)begin
       if(run340==0)begin seed340<=new_byte;offset340<=cursor-region_base340;end
       run340<=count340;repeat340<=repeat_next340;
       if(count340==64||cursor+1'b1==region_end340)begin
        pending340<=0;emit_run340(count340,repeat_next340);
       end else state<=FETCH;
      end else if(cursor+1'b1==region_end340)next_region340();else state<=FETCH;
     end
    end else begin
     cursor<=''')
    s=once(s,'      H:state<=FETCH;MASK,SHIFT:next_block();GEO:state<=RAWSTART;', '''      H:state<=FETCH;MASK,SHIFT:next_block();GEO:state<=RAWSTART;
      RUN340:begin
       run340<=0;repeat340<=0;
       if(pending340)begin pending340<=0;state<=FSTORE;end
       else if(cursor==region_end340)next_region340();else state<=FETCH;
      end''')
    a=s.index('    RAWSTART:begin');b=s.index('    ENDTRAILER:',a)
    s=s[:a]+'''    RAWSTART:begin
     region340<=7;cursor<=2336;run340<=0;repeat340<=0;pending340<=0;
     q_have<=0;q_pending<=0;state<=FETCH;
    end
'''+s[b:]
    # Raster bytes are alternating little-endian words. A bounded 64-byte
    # block uses repeat16 only when every pair matches, else literal. No
    # unbounded future-query lookahead or extra RAM is assumed.
    s=s.replace('reg repeat340,pending340;', 'reg [1:0] repeat340;reg pending340;reg [7:0] seed_hi340;reg same_pair340,any_change340;')
    s=s.replace('region340!=0&&run340!=0&&', 'region340!=0&&region340!=3&&run340!=0&&')
    s=s.replace('wire repeat_next340=repeat340||', 'wire repeat_next340=(repeat340!=0)||')
    s=s.replace('a_we=!stop_run340&&(run340!=0||changed);', 'a_we=!stop_run340&&(region340==3||run340!=0||changed);')
    s=s.replace("{1'b0,repeat340,6'd0}", "{repeat340,6'd0}")
    s=s.replace('default:if(repeat340)out_byte=seed340;', "default:if(repeat340!=0)out_byte=(repeat340==2&&rec_i[0])?seed_hi340:seed340;")
    s=s.replace('input [6:0] n,input rep)', 'input [6:0] n,input [1:0] rep)')
    s=s.replace("rep?8'd5:{1'b0,n}+8'd4", "rep==2?8'd6:rep==1?8'd5:{1'b0,n}+8'd4")
    s=s.replace('region340<=0;run340<=0;repeat340<=0;pending340<=0;seed340<=0;', 'region340<=0;run340<=0;repeat340<=0;pending340<=0;seed_hi340<=0;same_pair340<=0;any_change340<=0;seed340<=0;')
    s=s.replace('    FSTORE:if(region340!=0)begin', '''    FSTORE:if(region340==3)begin
     cursor<=cursor+1'b1;run340<=count340;state<=FETCH;
     if(run340==0)begin seed340<=new_byte;offset340<=cursor-region_base340;same_pair340<=1;any_change340<=changed;end
     else begin
      any_change340<=any_change340||changed;
      if(run340==1)seed_hi340<=new_byte;
      else if(new_byte!=(run340[0]?seed_hi340:seed340))same_pair340<=0;
     end
     if(count340==64||cursor+1'b1==region_end340)begin
      if(any_change340||changed)begin pending340<=0;
       emit_run340(count340,(same_pair340&&new_byte==seed_hi340)?2'd2:2'd0);
      end else if(cursor+1'b1==region_end340)next_region340();else run340<=0;
     end
    end else if(region340!=0)begin''')
    # Keep all combinational helper declarations after their source registers.
    a=s.index(' reg [3:0] region340;');b=s.index(' reg seal_state;',a)
    helper=s[a:b];at=helper.index(' always @*begin');decl=helper[:at];helper=helper[at:];s=s[:a]+decl+s[b:]
    s=once(s,' wire shift_ok=',helper+' wire shift_ok=')
    s=s.replace(' reg [3:0] region340;', ' wire stop_run340;\n reg [3:0] region340;').replace(' wire stop_run340=', ' assign stop_run340=')
    p.write_text(s,newline='\n')

def native(d):
    from nes_read336 import native as previous
    previous(d)
    (d/'nes_decode280.c').write_text(decoder(),newline='\n')
    p=d/'nes_input286.inc';s=p.read_text()
    s=once(s,'static void need286(unsigned tag,unsigned kind){input285.required[tag/4]|=(uint8_t)(kind<<((tag%4)*2));}', '''static unsigned required340;
static void need286(unsigned tag,unsigned kind){
 uint8_t *bits=(uint8_t *)input285.tiles;
 unsigned old=(bits[tag/4]>>((tag%4)*2))&3;
 if(!old)required340++;
 bits[tag/4]|=(uint8_t)(kind<<((tag%4)*2));
}''')
    s=once(s,'memcpy(s->objects,p+2336,1024);','')
    s=once(s,' memset(s->required,0,sizeof s->required);', ' _Static_assert(sizeof s->tiles>=2048,"bitmap must fit old sorted list");required340=0;memset(s->tiles,0,2048);')
    objects=' for(unsigned i=0;i<s->counts[2];i++){if(s->objects[i]>>49)return bad286(4);need286((unsigned)s->objects[i]&8191,2);}'
    s=once(s,objects,'')
    a=s.index(' s->ntiles=0;');b=s.index(' s->state=NES_NATIVE165_PREPARED;',a)
    s=s[:a]+' s->ntiles=0;if(required340>512)return bad286(10);\n'+s[b:]
    s=once(s,' memcpy(input285.raw_pixels,history286+4398,input285.patch_count*256u);', ''' struct nes_native165 *s=&input285;
 memcpy(s->objects,history286+2336,1024);
 for(unsigned i=0;i<s->counts[2];i++){if(s->objects[i]>>49)return bad286(4);need286((unsigned)s->objects[i]&8191,2);}
 if(required340>512)return bad286(10);
 memcpy(input285.raw_pixels,history286+4398,input285.patch_count*256u);''')
    p.write_text(s,newline='\n')
    planner(d)

def host(d):
    """One encoded packet position; no saved next-descriptor address.

    Only the checked typed batch path uses cursor. The immutable packet and
    byte-at-a-time reader own parser_address until exact DMA/receipt retirement.
    Metadata's run count shares the otherwise idle header/byte counter.
    """
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'reg batch;reg [8:0] cursor;', 'reg batch;')
    s=once(s,'active305.left<=0;cursor<=0;', 'active305.left<=0;')
    s=once(s,'batch<=1;cursor<=21;parser_address<=21;', 'batch<=1;parser_address<=21;')
    s=once(s,'endcase cursor<=cursor+1\'b1;parser_address<=parser_address+1\'b1;', 'endcase parser_address<=parser_address+1\'b1;')
    s=once(s,"cursor+{1'b0,header[14]}+(remaining>1?9'd5:9'd0)>qlen", "parser_address+{1'b0,header[14]}+(remaining>1?9'd5:9'd0)>qlen")
    s=once(s,"(remaining==1&&cursor+{1'b0,header[14]}!=qlen)", "(remaining==1&&parser_address+{1'b0,header[14]}!=qlen)")
    s=once(s,"cursor<=cursor+{1'b0,header[14]};map_receipt<=0;", 'map_receipt<=0;')
    s=once(s,'parser_address<=cursor[7:0];state<=DREAD;', "parser_address<=parser_address+9'd1;state<=DREAD;")
    s=once(s,' reg [7:0] run_left313;reg run_zero313;', ' reg run_zero313;')
    s=once(s,'failed<=0;run_left313<=0;', 'failed<=0;')
    s=s.replace('run_left313','at')
    p.write_text(s,newline='\n')

def planner(d):
    p=d/'nes_planner211.c';s=p.read_text()
    a=s.index('static const struct nes_native165_tile *tile(');b=s.index('static bool patched(',a)
    s=s[:a]+'''/* Receiver-owned bitmap is the checked membership interface. No sorted
 * tile-list materialization or binary search; payload semantics still checked. */
static bool tile(const struct nes_native165 *s,unsigned tag,unsigned kind){
 const uint8_t *bits=(const uint8_t *)s->tiles;
 return tag<8192&&((bits[tag/4]>>((tag%4)*2))&kind)!=0;
}
'''+s[b:]
    p.write_text(s,newline='\n')
    p=d/'nes_planner285.c';s=p.read_text()
    s=once(s,' return batch_count285+reserve_plans293<15||flush285();', ''' /* First BG prefix is irrevocable only for slot1 after the clear. Later
  * fresh slots are allocated above it; reused slots emit no duplicate plan. */
 if(output_size285==0&&batch_count285==2&&b[0]==0x80&&b[3]==1&&b[4]==0){
  unsigned bytes=batch_size285,plans=batch_count285;if(!flush285())return false;
  reserve_bytes293=bytes;reserve_plans293=plans;return true;
 }
 return batch_count285+reserve_plans293<15||flush285();''')
    p.write_text(s,newline='\n')
    s=p.read_text();s=once(s,'unsigned bytes=batch_size285,plans=batch_count285;\n if(!flush285())return false;', 'unsigned bytes=batch_size285+reserve_bytes293,plans=batch_count285+reserve_plans293;\n if(!flush285())return false;');p.write_text(s,newline='\n')
