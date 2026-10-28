# SPDX-License-Identifier: MIT
"""Fixed SPI transaction ownership and ended-read owner on the398 record path.
The descriptor/manifest semantic interpreter is retained and charged explicitly.
"""
from nes_delta231 import ROOT,BASE,once
import nes_joint398 as old

TAG_PORTS='.tag_write400(tag_write400),.tag_at400(tag_at400),.tag_data400(tag_data400),.tag_ready400(tag_ready400),'
TAG_DECL='wire tag_write400,tag_ready400;wire[3:0]tag_at400;wire[7:0]tag_data400;\n '
def hint_top(s):
 s=once(s,'wire hint_metaactive398;',TAG_DECL+'wire hint_metaactive398;')
 return s.replace('(.hint_metaactive398(', '('+TAG_PORTS+'.hint_metaactive398(')

def program():
 from nes_host398 import host_program
 p=host_program();a=p.labels['interrupt'];b=p.labels['bounds'];delta=b-a
 p.code=p.code[:a]+p.code[b:]
 p.fix=[(at if at<a else at-delta,label)for at,label in p.fix if at<a or at>=b]
 p.labels={n:(v if v<a else v-delta)for n,v in p.labels.items()if v<a or v>=b}
 p.labels['interrupt']=p.labels['fault'];return p

def apply(d):
 # Restore direct fixed transaction field/CRC handling, not the old source
 # or semantic host path. Physical packet and plan ownership stay distinct.
 for name in('nes_spi270.sv','nes_queue260.sv','nes_plan_spi200.sv'):
  (d/name).write_text((BASE/'probes/nes-joint396/build08'/name).read_text(),newline='\n')
 old.ea(d)
 p=d/'nes_spi270.sv';s=p.read_text().replace('[113:0]','[153:0]')
 s=s.replace(' assign link[113]=transaction_admit319;'," assign link[153:114]=40'd0;\n assign link[113]=transaction_admit319;")
 p.write_text(s,newline='\n')
 p=d/'nes_plan_spi200.sv';s=p.read_text().replace('[113:0]','[153:0]');p.write_text(s,newline='\n')
 p=d/'nes_queue260.sv';s=p.read_text().replace('[113:0]','[153:0]')
 s=s.replace('module nes_queue260(',"module nes_queue260(output wire irq398,input wire control_write398,input wire[7:0]control_address398,output wire[7:0]control_q398,\n")
 s=s.replace(' reg [15:0] sequence312;'," assign irq398=1'b0;assign control_q398=8'd0;\n reg reserved398;reg [15:0] sequence312;")
 s=s.replace('assign storage_empty312=empty315;','assign storage_empty312=empty315&&!reserved398;')
 s=s.replace('full,1\'b0,(!empty315)',"full||reserved398,1'b0,(!empty315)")
 s=s.replace('assign admit319=enable&&!full&&!fault;', 'assign admit319=enable&&!full&&!reserved398&&!fault;')
 s=s.replace('sequence312<=0;bad_header312<=0;','sequence312<=0;bad_header312<=0;reserved398<=0;')
 s=s.replace('   if(frame_start312)',"   if(link270[110]&&count270==0&&incoming==8'he1&&admit319)reserved398<=1;\n   if(frame_start312)")
 s=s.replace('else if(!can_write||!enable||fault||bad_header312', 'else if(!reserved398||!can_write||!enable||fault||bad_header312')
 s=s.replace('else begin accepted<=accepted+1\'b1;', "else begin reserved398<=0;accepted<=accepted+1'b1;")
 p.write_text(s,newline='\n')
 # Host-side hint parser writes the same existing metadata RAM as the core.
 p=d/'nes_plan_path267.sv';s=p.read_text();s=s[:s.index('module nes_hint361(')]+(ROOT/'src/fpga/nes_joint400/hint.sv').read_text()
 s=s.replace('module nes_plan_path267(', 'module nes_plan_path267(output wire tag_write400,output wire[3:0]tag_at400,output wire[7:0]tag_data400,input wire tag_ready400,',1)
 s=s.replace('hint(.control_q398(', 'hint('+TAG_PORTS+'.control_q398(');p.write_text(s,newline='\n')
 p=d/'nes_joint266.sv';s=p.read_text().replace('input wire hint_metaactive398,','input wire tag_write400,input wire[3:0]tag_at400,input wire[7:0]tag_data400,output wire tag_ready400,\n input wire hint_metaactive398,',1)
 s=s.replace(' flow(.hint_metaactive398(', ' flow('+TAG_PORTS+'.hint_metaactive398(');p.write_text(s,newline='\n')
 p=d/'nes_live_joint.sv'
 if p.exists():p.write_text(hint_top(p.read_text()),newline='\n')
 p=d/'nes_mux260.sv';s=p.read_text().replace('input wire hint_metaactive398,','input wire tag_write400,input wire[3:0]tag_at400,input wire[7:0]tag_data400,output wire tag_ready400,\n input wire hint_metaactive398,',1)
 s=once(s,'.irq(footer_request396||queue_irq398)',".irq(1'b0)")
 s=once(s,'reg[2:0] footer_at398;assign footer_index396=footer_at398;assign footer_address396=250+footer_at398;', '''reg[2:0] footer_at398;reg footer_phase400;
 assign footer_index396=footer_at398;assign footer_address396=250+footer_at398;
 always @(posedge host_clk or posedge rst)if(rst)begin footer_phase400<=0;footer_at398<=0;end
 else if(!footer_request396)begin footer_phase400<=0;footer_at398<=0;end
 else if(!footer_phase400)footer_phase400<=1;
 else begin footer_phase400<=0;footer_at398<=footer_at398==5?0:footer_at398+1'b1;end''')
 s=once(s,'assign footer_capture396=out398&&ioa==IO_FOOTER_CAPTURE&&footer_request396;', 'assign footer_capture396=footer_phase400&&footer_request396&&!rst&&!fault;')
 s=s.replace('footer_at398<=0;\n   parser_address', '\n   parser_address').replace('IO_FOOTER_INDEX:footer_at398<=iod[2:0];','')
 s=s.replace('reg[15:0] canonical,fragment_at,tap_position;reg[11:0] chunk_length,read_count;', 'reg[15:0] canonical,fragment_at,tap_base400;wire[15:0]tap_position;reg[11:0]chunk_length;wire[11:0]read_count;')
 s=s.replace('reg wp,rp,tap_seen,read_pending,tap_fault,taken;', 'reg wp,rp,taken;wire tap_seen,read_pending,tap_fault;wire[7:0]read_data400;wire read_event400;')
 s=once(s,'assign read359={capture&&ready359&&!read_pending&&address==24\'h400800+read_count&&read_count<chunk_length&&!fault&&!rst,', 'assign read359={read_event400,')
 s=once(s,'region,tap_position,aperture_data};','region,tap_position,read_data400};')
 marker=' wire good_consume='
 at=s.index(marker);s=s[:at]+''' nes_read_owner400 read_owner(.clk(host_clk),.reset(rst),.stop(fault),.active(phase==1),
  .start(out398&&ioa==IO_OPEN),.clear(out398&&ioa==IO_TAKE),.read_n(read_n),.capture(capture),
  .ended(read_end&&ap>=24'h400800&&ap<24'h401800&&!invalidate_banks),.checker_ready(ready359),
  .address(address),.ended_address(ap),.data(aperture_data),.token(chunk_token),.length(chunk_length),
  .base_position(tap_base400),.map_stride(region==2&&stride32),.count(read_count),.position(tap_position),
  .held_data(read_data400),.seen(tap_seen),.pending(read_pending),.fault(tap_fault),.event_valid(read_event400));
'''+s[at:]
 s=s.replace('tap_position<=0;','tap_base400<=0;').replace('read_count<=0;','').replace('tap_seen<=0;read_pending<=0;tap_fault<=0;','')
 a=s.index('   if(read_n)tap_seen');b=s.index('   if(word_valid&&word_end',a);s=s[:a]+s[b:]
 s=s.replace('IO_TAP0:tap_position[7:0]<=iod;IO_TAP1:tap_position[15:8]<=iod;', 'IO_TAP0:tap_base400[7:0]<=iod;IO_TAP1:tap_base400[15:8]<=iod;')
 s=once(s,'wire core_grant=mv&&ma<224', 'wire tag_grant400=tag_write400&&!ctx_busy&&!header_request&&!stage_atomic&&!fault&&!rst;\n assign tag_ready400=tag_grant400;\n wire core_grant=!tag_write400&&mv&&ma<224')
 s=s.replace('assign ctx_pause=header_grant||core_grant;', 'assign ctx_pause=header_grant||tag_grant400||core_grant;')
 s=s.replace('core_grant?10\'d800+ma:stage_addr;', "tag_grant400?10'd928+tag_at400:core_grant?10'd800+ma:stage_addr;")
 s=s.replace('(core_grant?mw:!header_grant&&stage_write)', '(tag_grant400|| (core_grant?mw:!header_grant&&stage_write))')
 s=s.replace('assign metadata_data=core_grant?md:stage_data;', 'assign metadata_data=tag_grant400?tag_data400:core_grant?md:stage_data;')
 p.write_text(s,newline='\n')
 prog=program();words=prog.finish();words +=[15<<14|255]*(4096-len(words))
 (d/'program398.hex').write_text('\n'.join(f'{x:05x}'for x in words)+'\n',newline='\n')
 import json
 (d/'program398.json').write_text(json.dumps(dict(words=len(prog.code),labels=prog.labels),indent=2)+'\n')
 (d/'nes_read_owner400.sv').write_text((ROOT/'src/fpga/nes_joint400/read_owner.sv').read_text(),newline='\n')
