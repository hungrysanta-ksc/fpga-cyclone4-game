# SPDX-License-Identifier: MIT
"""Common final job producer and v2 packet boundary. No legacy runtime fallback."""
from nes_delta231 import ROOT,once

def rtl(d):
 p=d/'nes_mux260.sv';s=p.read_text();port=s[:s.index(' wire rst=')]
 p.write_text(port+(ROOT/'src/fpga/nes_jobs394/host_body.svh').read_text(),newline='\n')
 (d/'nes_tile_link394.sv').write_text((ROOT/'src/fpga/nes_jobs394/nes_tile_link394.sv').read_text(),newline='\n')
 p=d/'nes_spi270.sv';s=p.read_text().replace('count>=19&&count<=259','count>=13&&count<=259')
 s=s.replace('if(count==13)request_length280[7:0]<=incoming;else if(count==14)request_length280[15:8]<=incoming;',
             'if(count==9)request_length280[7:0]<=incoming;else if(count==10)request_length280[15:8]<=incoming;')
 p.write_text(s,newline='\n')
 p=d/'nes_queue260.sv';s=p.read_text()
 s=s.replace('reg bad_header312;','reg bad_header312;reg [8:0] lengths394[0:1];')
 s=s.replace('packet_ready?encoded312[8:0]+9\'d16:9\'d0','packet_ready?lengths394[retired[0]]:9\'d0')
 s=s.replace('-16\'d19','-16\'d13').replace('byte_count<=16','byte_count<=10').replace('byte_count>=3&&byte_count<=10','byte_count>=3&&byte_count<=8')
 s=s.replace('accepted<=accepted+1\'b1;sequence312<=sequence312+1\'b1;',
             'accepted<=accepted+1\'b1;sequence312<=sequence312+1\'b1;lengths394[accepted[0]]<=byte_count-3;')
 p.write_text(s,newline='\n')
 p=d/'nes_validator278.sv';s=p.read_text()
 # Reordering is allowed; duplicate/exact bitmap checks remain independently
 # implemented in this checker, including STOP and final receipt gates.
 s=s.replace('||unit359<v_map_end','').replace('||v_first<v_map_end','')
 p.write_text(s,newline='\n')

def arm(d,cold_quantum=0):
 assert cold_quantum in(0,256)
 p=d/'nes_output264.c';s=p.read_text()
 a=s.index('static unsigned phase(unsigned');z=s.index('static unsigned send317(',a);s=s[:a]+s[z:]
 a=s.index('static unsigned send317(');z=s.index('static unsigned send(unsigned n)',a)
 s=s[:a]+'''static unsigned direct394,wire_busy394;
static unsigned common394(unsigned,unsigned,unsigned);
static void reset_jobs394(void);
static unsigned tile394(const uint8_t *),ordinary_job394(const uint8_t *,unsigned),refs394(void);
static unsigned send317(unsigned n,uint8_t *b,unsigned direct){
 unsigned op=b[1],flags=b[2],body=n-16,start=u16(b+11);
 if(n<16||n>256||u16(b+13)!=body)return fail(5);
 if(op==3&&!refs394())return 0;
 unsigned prefix=op==10||op==11?2:0;
 for(unsigned i=0;i<body;i++)wire259[11+prefix+i]=b[17+i];
 if(prefix)w16(wire259+11,start);
 unsigned saved=direct394;direct394=direct;
 unsigned ok=common394(0xa0|op,flags,body+prefix);direct394=saved;return ok;
}
'''+s[z:]
 a=s.index('static unsigned batch_bytes260;');z=s.index('/* SPDX-License-Identifier: MIT */',a)
 s=s[:a]+'''static unsigned batch_bytes260;
static unsigned flush260(void){return !state259.error;}
unsigned publish_map332(void){return !state259.error;}
'''+s[z:]
 # No compact-plan packet or redundant map byte batching. Native producer now
 # calls jobs_map394 directly, including cold/empty frames.
 a=s.index('void reset_plan390(void);');z=s.index('static unsigned begin,seal,requirements264;',a)
 s=s[:a]+s[z:]
 a=s.index('  if(p[0]==9&&p[1]==2){');z=s.index('  if((p[0]==10||p[0]==11)&&map_issued327)',a)
 s=s[:a]+s[z:]
 a=s.index('  if(p[0]==7){');z=s.index('  if((p[0]==10||p[0]==11)&&!requirements264)',a)
 s=s[:a]+'''  if(p[0]==7)return tile394(p);
  if(p[0]==2||p[0]==4||p[0]==5||p[0]==8)return ordinary_job394(p,n);
'''+s[z:]
 s=s.replace(' reset_plan390();sent_plan390=0;begin=seal=requirements264=0;',' reset_jobs394();begin=seal=requirements264=0;')
 a=s.index('/* SPDX-License-Identifier: MIT */\n/* Uses192B bounded scratch.')
 s=s[:a]+f'#define JOBS394_COLD_QUANTUM {cold_quantum}\n'+(ROOT/'tools/nes_jobs394.c').read_text()
 # Forward declaration needed before the common component definition.
 s=s.replace('static unsigned begin,seal,requirements264;','extern unsigned map_byte327(unsigned);\nstatic unsigned begin,seal,requirements264;')
 s=s.replace('uint8_t *map_scratch330(void){return map_issued327&&!seal&&!state259.error?metadata317:0;}','uint8_t *map_scratch330(void){return 0;}')
 s=s.replace('if(!begin||seal||state259.error||!metadata_ready317())return !state259.error;',
             'if(wire_busy394||!begin||seal||state259.error||!metadata_ready317())return !state259.error;')
 # Old literal split policy is no longer a DMA/job boundary; send original
 # complete span through HEAD/DATA. Retain manifest codec splitting only.
 a=s.index(' if(op==2){',s.index('static unsigned parts274('));z=s.index(' if(op==10){',a)
 s=s[:a]+s[z:]
 # Unused legacy program/cut helpers are deleted, not suppressed in compiler.
 a=s.index('static unsigned program274(');z=s.index('static unsigned part274(',a);s=s[:a]+s[z:]
 p.write_text(s,newline='\n')
 p=d/'nes_native289.c';s=p.read_text();a=s.index('static bool map247(');z=s.index('static bool manifest247(',a)
 s=s[:a]+'''extern unsigned jobs_map394(const uint8_t *);
static bool map247(struct nes_native_sink165 *s,const struct nes_native_video165 *p,unsigned bank){
 (void)s;(void)bank;return jobs_map394(p->map)!=0;
}
'''+s[z:]
 if cold_quantum:s=once(s,'if(!used290){kind290=nextkind;first290=slot;}used290+=unit;',
  '''if(!used290){kind290=nextkind;first290=slot;}used290+=unit;
   /* Cold startup:publish a final256B job while its plans are already
    * immutable,so the first tile is not blocked behind all BG planning. */
   if(sink289.serial<=2&&used290>=256){if(!bulk289(kind290,first290,used290))return 0;used290=0;}''')
 # Remove the old map packet prebuilder, its cursors and scratch ownership.
 a=s.index('/* The209B metadata buffer');s=s[:a]+'''static void reset_map330(void){}
unsigned prepare_map330(void){return 2;}
'''
 s=s.replace('static const uint8_t *take_map330(unsigned *,unsigned *);','')
 p.write_text(s,newline='\n')
