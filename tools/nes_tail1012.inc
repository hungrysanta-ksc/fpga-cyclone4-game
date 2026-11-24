/* Only the validated FPGA header can promote this scratch trace to a sample. */
#define current1012 (log900p->trace[2])
static struct packet1012 *active1012;
static uint8_t submitted1012;

static uint16_t stamp1012(void){
 uint32_t delta=(nes_cost471_now()-current1012.base)>>9;
 return delta<65535 ? delta : 65535;
}

void ready1012(const uint8_t *p){
 uint16_t seq=p[2]|(p[3]<<8),gen=p[8]|(p[9]<<8);
 if(p[0]==1){
  active1012=NULL;
  submitted1012=0;
  current1012.count=current1012.credits=0;
  if(nes_budget210.frame_start-5500u>=500 || mode900==3 || mode900==1)return;
  current1012.gen=gen;
  current1012.base=nes_cost471_now();
 }else if(!active1012)return;
 if(gen!=current1012.gen || seq!=current1012.count || seq>=64){
  active1012=NULL;
  return;
 }
 ++current1012.count;
 active1012=&current1012.packet[seq];
 active1012->op=p[0];active1012->section=p[1];
 memcpy(&active1012->offset,p+10,4);
 active1012->ready=stamp1012();
}
void issue1012(uint16_t sent){
 if(!active1012)return;
 if(active1012->op==1)current1012.first_sent=sent;
 active1012->issue=stamp1012();
}
void sent1012(void){
 if(active1012){active1012->sent=stamp1012();submitted1012=current1012.count;}
}
void credit1012(uint16_t retired){
 if(!active1012)return;
 unsigned n=(uint16_t)(retired-current1012.first_sent);
 if(n<=current1012.credits || n>submitted1012)return;
 uint16_t now=stamp1012();
 while(current1012.credits<n)current1012.packet[current1012.credits++].credit=now;
}
static void keep1012(const struct row900 *r){
 if(r==&log900p->other || !active1012 || active1012->op!=3 || current1012.gen!=r->gen ||
    current1012.credits!=current1012.count || r->valid!=3 || r->obj!=18 || r->dirty!=23)return;
 unsigned slot;
 if(r->tick<=5547 && r->bg==532 && r->wire[4]==3 && r->wire[5]==2 && r->descriptor[1]==1 && r->descriptor[2]==64)slot=0;
 else if(r->tick>=5574 && r->tick<=5634 && r->bg==529 && r->wire[4]==1 && r->wire[5]==1 && !r->descriptor[1] && r->descriptor[2]==16)slot=1;
 else return;
 if(r->descriptor[3] || r->descriptor[4] || r->descriptor[5] || log900p->trace[slot].count)return;
 current1012.tick=r->tick;
 current1012.e0=(ack900.clock-current1012.base)>>9;
 memcpy(&log900p->trace[slot],&current1012,offsetof(struct trace1012,packet)+current1012.count*sizeof(*active1012));
}
