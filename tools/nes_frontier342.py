# SPDX-License-Identifier: MIT
"""Bounded warm BG frontier on the selected336 ARM, unchanged338 RTL."""
from nes_delta231 import once
from nes_read336 import native as previous_native

def native(d):
 previous_native(d)
 p=d/'nes_planner285.c';s=p.read_text()
 s=s.replace('static unsigned reserve_bytes293,reserve_plans293;','static unsigned reserve_bytes293,reserve_plans293;\nunsigned frontier342=1,prefixes342,checks342;\nextern unsigned prefill287(void);')
 at=s.index('static bool emit285(')
 s=s[:at]+'''/* Used slots are immutable within this generation. Bound foreground work;
 * a non-advancing frontier leaves the original batch schedule intact. */
__attribute__((noinline)) unsigned advance342(void){
 if(input285.state!=NES_NATIVE165_COMMITTED||resident285.fault||!resident285.open)return 0;
 for(unsigned n=0;n<8&&frontier342<1024;n++){
  checks342++;if(!(resident285.used[frontier342/8]&(1u<<(frontier342%8))))break;
  frontier342++;
 }
 unsigned bytes=0,plans=0;
 while(bytes<batch_size285){
  unsigned key=order247_key(batch285+bytes);
  if(key>=frontier342||key>=1024)break;
  bytes+=order247_length(batch285+bytes);plans++;
 }
 /* Clear by itself starts no ROM fetch. At most one early prefix per frame. */
 if(prefixes342||!plans||(plans==1&&order247_key(batch285)==0))return 1;
 if(output_size285+bytes+3>sizeof output285)return 0;
 output285[output_size285++]=bytes;output285[output_size285++]=bytes>>8;output285[output_size285++]=plans;
 memcpy(output285+output_size285,batch285,bytes);output_size285+=bytes;
 memmove(batch285,batch285+bytes,batch_size285-bytes);batch_size285-=bytes;batch_count285-=plans;
 reserve_bytes293+=bytes;reserve_plans293+=plans;prefixes342++;
 trace259(2,plans);return prefill287()!=0;
}
''' +s[at:]
 s=once(s,'unsigned begin285(void){','unsigned begin285(void){frontier342=1;prefixes342=checks342=0;')
 # Existing BG split must preserve reservations from the new prefix too.
 s=once(s,'unsigned bytes=batch_size285,plans=batch_count285;','unsigned bytes=batch_size285+reserve_bytes293,plans=batch_count285+reserve_plans293;')
 p.write_text(s,newline='\n')
 p=d/'nes_input286.inc';s=p.read_text();s=once(s,'if(result==1&&bg_done293()&&!flush_bg293())','if(result==1&&!bg_done293()&&!advance342())return 0;if(result==1&&bg_done293()&&!flush_bg293())')
 s=once(s,'void stop286(void){','void stop286(void){frontier342=1;prefixes342=checks342=0;reserve_bytes293=reserve_plans293=0;')
 p.write_text(s,newline='\n')
