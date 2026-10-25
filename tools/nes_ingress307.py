# SPDX-License-Identifier: MIT
"""Credit-safe manifest issue and shared transaction admission/CRC."""
from nes_delta231 import once
from nes_joint303 import native as previous
import os

def native(d):
    previous(d)
    p=d/'nes_output264.c';s=p.read_text()
    s=once(s,'if((p[0]==10||p[0]==11)&&!requirements264){\n   if(!drain())return 0;',
        '''if((p[0]==10||p[0]==11)&&!requirements264){
   /* All preceding DMA packets have been accepted in order. send() still
    * waits for checked credit; independent retirement stays in hardware. */''')
    if os.environ.get('NES307_RTL')=='1':
        s=once(s,'wire259[1]=15;if(!send(206))return 0;requirements264=1;', '''wire259[1]=15;
   /* Existing 24 display bytes remain independently checked. The shared
    * bounded decoder handles the following exact 166 requirements. */
   unsigned at307=0,encoded307=41;
   wire259[41]=1;
   while(at307<166){
    unsigned zero307=seal262[40+at307]==0,n307=1;
    while(at307+n307<166&&n307<128&&(seal262[40+at307+n307]==0)==zero307)n307++;
    if(encoded307+1+(zero307?0:n307)>=206){encoded307=206;break;}
    wire259[1+encoded307++]=(zero307?128:0)|(n307-1);
    if(!zero307)for(unsigned j307=0;j307<n307;j307++)wire259[1+encoded307++]=seal262[40+at307+j307];
    at307+=n307;
   }
   if(encoded307<206){wire259[2]=1;w16(wire259+13,encoded307-16);}
   else{for(unsigned i=0;i<206;i++)wire259[i+1]=seal262[i];wire259[1]=15;encoded307=206;}
   if(!send(encoded307))return 0;requirements264=1;''')
    p.write_text(s,newline='\n')

def apply(d):
    # Two shared, combinational transaction-close signals. Domain ownership
    # remains endpoint-local; widen every actual link including testbench.
    for p in d.glob('*.sv'):
        s=p.read_text().replace('[107:0]','[109:0]');p.write_text(s,newline='\n')
    p=d/'nes_spi270.sv';s=p.read_text()
    s=once(s,'assign link[106:49]=', '''assign link[109]=ss[1]&&!prev_ss;
 assign link[108]=bits==0&&
   (command==8'he1 ? (count>=19&&count<=259&&payload_crc280==0):
    command==8'he9 ? (request_length280>=3&&request_length280<=512&&request_number280>=1&&request_number280<=16&&
      count==request_length280+8&&crc_good280&&tail_good280&&request_value280==payload_crc280):
    command==8'hea ? (count==7&&crc_good280&&tail_good280):1'b0);
 assign link[106:49]=''')
    s=once(s,"if((count==0&&incoming==8'he1)||command==8'he1)",
        "if((count==0&&incoming==8'he1)||command==8'he1||(command==8'he9&&count>=4&&count<=request_length280+3))")
    p.write_text(s,newline='\n')
    p=d/'nes_queue260.sv';s=p.read_text()
    s=once(s,'if(!prev_ss&&ours)begin','if(link270[109]&&ours)begin')
    s=once(s,'byte_count<19||byte_count>259||bit_count!=0||request_crc!=0','!link270[108]')
    p.write_text(s,newline='\n')
    p=d/'nes_plan_spi200.sv';s=p.read_text()
    s=once(s,'if(!prev_ss&&ours)begin','if(link270[109]&&ours)begin')
    s=once(s,"count!=7||bits!=0||length!=ended_generation||received16!=accepted||!link270[66]||!link270[65]",
        "!link270[108]||length!=ended_generation||received16!=accepted")
    s=once(s,"length<3||length>512||number==0||number>16||count!=length+8||bits!=0||!link270[66]||!link270[65]",'!link270[108]')
    p.write_text(s,newline='\n')
    # Legacy standalone instances retain their local CRC. Real shared SPI
    # paths select external integrity checking, removing the duplicate CRC.
    p=d/'nes_plan_batch206.sv'
    if p.exists():
        s=p.read_text()
        s=once(s,'module nes_plan_batch206(', 'module nes_plan_batch206 #(parameter SHARED_CRC307=0)(')
        s=once(s,'seal_crc!=crc||','(!SHARED_CRC307&&seal_crc!=crc)||')
        s=once(s,'crc<=crc16(crc,write_data);','if(!SHARED_CRC307)crc<=crc16(crc,write_data);')
        p.write_text(s,newline='\n')
    for name in ('nes_plan_rom267.sv','nes_plan_path267.sv'):
        p=d/name
        if p.exists():p.write_text(once(p.read_text(),'nes_plan_batch206 transport(', 'nes_plan_batch206 #(.SHARED_CRC307(1)) transport('),newline='\n')
    # One existing validator body decoder for both manifest domains.
    p=d/'nes_mux260.sv';s=p.read_text()
    s=once(s,'manifest_phase!=0||qlen!=206||header[1]!=0||plen!=190||startpos!=0||outlen!=0',
        "manifest_phase!=0||(header[1]==0?(qlen!=206||plen!=190):header[1]==1?(qlen<42||qlen>206):1'b1)||startpos!=0||outlen!=0")
    s=once(s,'assign exec_op298=header[0][3:0];',"assign exec_op298=header[0]==15&&header[1]==1?4'd4:header[0][3:0];")
    p.write_text(s,newline='\n')
    p=d/'nes_validator278.sv';s=p.read_text()
    s=once(s,'reg [11:0] v_bit_at,v_end283,v_map_end;', '''wire requirements307=exec_op298==4;
 wire rle307=exec_op298==11||(requirements307&&packet_at298>40);
 wire [9:0] run_end307=cursor+{3'd0,exec_data298[6:0]}+10'd1;
 reg [11:0] v_bit_at,v_end283,v_map_end;''')
    s=once(s,'exec_op298!=15&&exec_op298!=10&&exec_op298!=11','exec_op298!=15&&exec_op298!=10&&exec_op298!=11&&exec_op298!=4')
    s=once(s,'else if(exec_op298==11&&packet_at298==16)begin\n      if(exec_data298!=3||exec_length298<18)fault<=3;',
        "else if((exec_op298==11&&packet_at298==16)||(requirements307&&packet_at298==40))begin\n      if(exec_data298!=(requirements307?1:3)||exec_length298<(requirements307?42:18))fault<=3;")
    s=once(s,'else if(exec_op298==11&&rle_left298==0)begin\n      if(manifest_at282+{2\'d0,exec_data298[6:0]}+1>256||',
        "else if(rle307&&rle_left298==0)begin\n      if((requirements307?(map_phase305||run_end307>166):(!map_phase305||run_end307>256))||")
    s=once(s,'if(exec_op298==11)rle_left298<=','if(rle307)rle_left298<=')
    s=once(s,'if(exec_op298==15&&packet_at298<40)', 'if((exec_op298==15||requirements307)&&packet_at298<40)')
    s=once(s,'if(rle_left298!=0)fault<=3;else begin complete_execution298();',
        'if(rle_left298!=0||(requirements307&&(!map_phase305||cursor!=0||rec_i!=24)))fault<=3;else begin complete_execution298();')
    p.write_text(s,newline='\n')

def reference(d):
    # Independent scalar C decoder reconstructs the old requirements packet.
    p=d/'nes_producer264.c';s=p.read_text()
    s=once(s,'if(op==15){if(a!=206)return fail(30);memcpy(requirements264,packet,206);requirements264[0]=3;return 0;}', '''if(op==15){
  if(section==0){if(a!=206)return fail(30);memcpy(requirements264,packet,206);}
  else{
   if(section!=1||a<42||packet[40]!=1)return fail(30);
   memcpy(requirements264,packet,40);unsigned i=41,o=40;
   while(i<(unsigned)a){unsigned code=packet[i++],n=(code&127)+1;
    if(o+n>206||(!(code&128)&&i+n>(unsigned)a))return fail(30);
    while(n--)requirements264[o++]=(code&128)?0:packet[i++];
   }
   if(o!=206){return fail(30);}
   requirements264[1]=0;requirements264[12]=190;requirements264[13]=0;
  }
  requirements264[0]=3;return 0;
 }''')
    p.write_text(s,newline='\n')
