/* Diagnostic-only storage overlays the existing post-run journal buffer. */
unsigned char movement_slot;
uint32_t movement_save[3];
struct movement_row {
 uint32_t arm_ack;
 uint16_t tick,gen,x,y,bg,obj;
 uint8_t page[12],footer,ack_ok;
};
struct movement_log {
 uint32_t magic,edition,slot,save[3];
 uint16_t used,start,done,misses;
 struct movement_row rows[218];
};
_Static_assert(sizeof(struct movement_log)<=sizeof(struct log900),"movement log capacity");
#define movement ((struct movement_log *)(void *)ptrcache)
static uint32_t arm_ack;
static unsigned ack_key;
void block1029(unsigned begin,unsigned gen,unsigned n,const uint32_t *t){}
void input900(uint16_t g){}
void finish_header950(void){}
void e0900(uint16_t gen,unsigned bank){
 if(ack_key!=(65536u|gen)){ack_key=65536u|gen;arm_ack=nes_cost471_now();}
}
static void record900(uint32_t tick,const struct nes_native_video165 *v){
 struct movement_log *m=movement;
 if(!movement_slot || m->done)return;
 uint8_t rx[16]={0};
 bool ok=page905(rx,256) && rx[1]==0xd2 && rx[15]==0x5a &&
         (rx[2]+256u*rx[3])==v->generation;
 if(!ok)++m->misses;
 unsigned i=m->used;
 if(!i && (!ok || !(rx[4]&16)))i=0;
 else if(!i){m->start=tick;i=1;}
 if(i>=218){m->done=2;return;}
 struct movement_row *r=&m->rows[i];
 r->arm_ack=arm_ack;r->ack_ok=ack_key==(65536u|v->generation);
 r->tick=tick;r->gen=v->generation;r->bg=v->bg_count;r->obj=v->obj_count;
 r->x=v->hofs[112];r->y=v->vofs[112];
 memcpy(r->page,rx+1,12);r->footer=ok?0x5a:0;
 if(i){m->used=i+1;if((uint16_t)(tick-m->start)>=400)m->done=1;}
}
void nes_budget210_reset(void){
 memset(movement,0,sizeof *movement);movement->magic=0x32354d46;
 movement->edition=EDITION1052;movement->slot=movement_slot;
 memcpy(movement->save,movement_save,sizeof movement_save);
 ack_key=0;
