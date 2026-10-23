# SPDX-License-Identifier: MIT
"""Validator owns canonical expected reads; bounded ARM early map manifest."""
from nes_delta231 import once
from nes_metadata317 import native as previous_native

def apply(d):
    ports='input wire scan_start327,input wire [7:0] expected_data327,output wire [8:0] expected_addr327,output wire scan_done327,'
    connect='.scan_start327(scan_start327),.expected_data327(expected_data327),.expected_addr327(expected_addr327),.scan_done327(scan_done327),'
    for name,module in [('nes_validator278.sv','nes_validator278'),('nes_joint257.sv','nes_joint257')]:
        p=d/name;s=p.read_text();s=once(s,'module '+module+'(', 'module '+module+'('+ports)
        if name=='nes_joint257.sv':s=once(s,'nes_validator278 validator(', 'nes_validator278 validator('+connect)
        p.write_text(s,newline='\n')
    p=d/'nes_joint266.sv';s=p.read_text()
    s=once(s,' wire display_write,', ' wire scan_start327,scan_done327;wire [7:0] expected_data327;wire [8:0] expected_addr327;\n wire display_write,')
    s=once(s,' flow(', ' flow('+connect);s=once(s,'nes_joint257 core(', 'nes_joint257 core('+connect);p.write_text(s,newline='\n')
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'module nes_output260', 'module nes_output260')
    s=once(s,'output wire queue_admit319,', 'output wire scan_start327,output wire [7:0] expected_data327,input wire [8:0] expected_addr327,input wire scan_done327,output wire queue_admit319,')
    s=once(s,'canonical_read313?manifest_byte313:', 'canonical_read313?expected_addr327:')
    s=once(s,' wire canonical_read313=', ' assign scan_start327=header[0]==3&&state==MREAD313&&!rst&&!fault;\n assign expected_data327=qdata;\n wire canonical_read313=')
    s=once(s,'assign display_write=canonical_read313&&state==MISSUE313&&display_byte313&&range_ready&&!rst&&!fault;', "assign display_write=1'b0;")
    s=once(s,'assign ordinary_check=canonical_read313&&state==MISSUE313&&!display_byte313&&range_ready&&!rst&&!fault;', "assign ordinary_check=1'b0;")
    s=once(s,'MREAD313:state<=MCAP313;', 'MREAD313:state<=header[0]==3?MWAIT313:MCAP313;')
    s=once(s,'      if(header[0]==3)begin\n       held<=qdata;display_byte313<=manifest_byte313<24;state<=MISSUE313;\n      end else if', '      if')
    s=once(s,'     MWAIT313:if(range_ready)begin\n      if(header[0]==3)begin\n       if(manifest_byte313==445)state<=MHASH313;\n       else begin manifest_byte313<=manifest_byte313+1\'b1;state<=MREAD313;end\n      end else begin', '     MWAIT313:if(header[0]==3)begin\n      if(scan_done327)state<=MHASH313;\n     end else if(range_ready)begin\n      begin')
    p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'D_FETCH,D_RETURN} state_t;', 'D_FETCH,D_RETURN,E_READ327,E_CAPTURE327} state_t;')
    s=once(s," wire range_external=1'b1;", " wire range_external=1'b1;"+'''
 reg scanning327;
 assign expected_addr327=rec_i<24?{1'b0,rec_i}:map_phase305?9'd190+cursor[8:0]:9'd24+cursor[8:0];
 assign scan_done327=scanning327&&state==V_ACTIVE&&map_phase305&&cursor==256&&!fault&&!abort_source;
''')
    s=once(s,'map_phase305<=0;crc_mask287<=0;', 'scanning327<=0;map_phase305<=0;crc_mask287<=0;')
    s=once(s,'else if(abort_source)begin if(!fault)', 'else if(abort_source)begin scanning327<=0;if(!fault)')
    s=once(s,'     if(v_begin_valid)fault<=1;', '''     if(scan_start327)begin
      if(scanning327||rec_i!=0||cursor!=0||map_phase305||!v_all_consumed)fault<=3;
      else begin scanning327<=1;state<=E_READ327;end
     end else if(scanning327)begin
      if(map_phase305&&cursor==256)scanning327<=0;
      else state<=E_READ327;
     end else if(v_begin_valid)fault<=1;''')
    s=once(s,'    V_RREAD:begin', '''    E_READ327:state<=E_CAPTURE327;
    E_CAPTURE327:begin v_value<=expected_data327;state<=rec_i<24?D_READ:V_CHECKREAD;end
    V_RREAD:begin''')
    p.write_text(s,newline='\n')

def native(d):
    previous_native(d)
    p=d/'nes_native289.c';s=p.read_text();s+='\nunsigned map_byte327(unsigned at){return at<256?mapstale247[resident285.target][at]:0;}\n';p.write_text(s,newline='\n')
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'static unsigned begin,seal,requirements264;', 'static unsigned begin,seal,requirements264;\nstatic unsigned map_at327,map_run327,map_tag327,map_size327,map_zero327,map_issued327,map_disabled327;')
    s=once(s,'  if(!flush260())return 0;', '  if((p[0]==10||p[0]==11)&&map_issued327)return 1;\n  if(!flush260())return 0;')
    s=once(s,' if(requirements264||!begin||seal||state259.error||!metadata_ready317())return !state259.error;', ''' if(!begin||seal||state259.error||!metadata_ready317())return !state259.error;
 if(requirements264)return issue_map327();''')
    pos=s.index('__attribute__((noinline)) unsigned issue_metadata317')
    s=s[:pos]+'''extern unsigned map_byte327(unsigned);
__attribute__((noinline)) static unsigned issue_map327(void){
 if(map_issued327||map_disabled327)return 1;
 if((uint16_t)(state259.sent-state259.retired)>=2)return 1;
 if(!map_size327){
  for(unsigned i=1;i<=17;i++)metadata317[i]=0;
  metadata317[1]=11;metadata317[2]=2;metadata317[17]=3;map_size327=17;
 }
 /* At most16 bitmap bytes per idle visit; DMA/plan/IRQ rechecked by caller. */
 for(unsigned steps=0;steps<16&&map_at327<256;steps++){
  unsigned v=map_byte327(map_at327),zero=v==0;
  if(!map_run327||map_run327==128||zero!=map_zero327){
   if(map_size327>=200){map_disabled327=1;return 1;}
   map_tag327=++map_size327;map_run327=0;map_zero327=zero;
  }
  if(!zero){if(map_size327>=200){map_disabled327=1;return 1;}metadata317[++map_size327]=v;}
  map_run327++;metadata317[map_tag327]=(zero?128:0)|(map_run327-1);map_at327++;
 }
 if(map_at327==256){
  w16(metadata317+13,map_size327-16);
  if(!send317(map_size327,metadata317,1))return 0;
  map_issued327=1;
 }
 return 1;
}
'''+s[pos:]
    s=once(s,' begin=seal=requirements264=0;', ' begin=seal=requirements264=0;map_at327=map_run327=map_tag327=map_size327=map_zero327=map_issued327=map_disabled327=0;')
    p.write_text(s,newline='\n')

    p=d/'nes_refill267.c';s=p.read_text()
    s=once(s,'  if(work_pending302()&&!pending302()&&!supply303()&&!progress302()){\n   if(!issue_metadata317())', '  for(unsigned slices327=0;slices327<17&&work_pending302()&&!pending302()&&!supply303()&&!progress302();slices327++){\n   if(!issue_metadata317())')
    p.write_text(s,newline='\n')
