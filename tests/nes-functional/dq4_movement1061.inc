/* One 5.5 second window plus the preceding publication. 340 rows cover
 * 60.1 Hz at one publication per VBlank without dropping a fast interval. */
static uint8_t movement_slot;
static uint32_t movement_save[3],ack_clock;
static unsigned ack_key;
struct __attribute__((packed)) movement_row {
 uint32_t ack;
 uint16_t x,y;
 uint8_t page[11],dirty;
 uint16_t tile_bytes;
};
struct movement_log {
 uint32_t magic,edition,slot,save[3];
 uint16_t used,start,done,misses;
 struct movement_row rows[340];
};
_Static_assert(sizeof(struct movement_log)<=sizeof(struct log900),"movement buffer");
#define movement ((struct movement_log *)(void *)ptrcache)
static unsigned staged_bytes;

void dq4_loaded(unsigned slot,uint32_t rom,uint32_t serial,uint32_t crc){
 movement_slot=slot==1 && rom==0x9ac62bb9u;
 movement_save[0]=rom;movement_save[1]=serial;movement_save[2]=crc;
}
void dq4_new_session(void){movement_slot=0;}
void block1029(unsigned begin,unsigned gen,unsigned n,const uint32_t *t){}
void input900(uint16_t g){}
void finish_header950(void){}
void e0900(uint16_t gen,unsigned bank){
 if(ack_key!=(65536u|gen)){ack_key=65536u|gen;ack_clock=nes_cost471_now();}
}
static void record900(uint32_t tick,const struct nes_native_video165 *v){
 struct movement_log *m=movement;
 unsigned bytes=staged_bytes;
 staged_bytes=0;
 if(!movement_slot || m->done)return;
 uint8_t rx[16]={0};
 bool ok=page905(rx,256) && rx[1]==0xd2 && rx[15]==0x5a &&
         (rx[2]+256u*rx[3])==v->generation && ack_key==(65536u|v->generation);
 if(!ok){++m->misses;if(m->used)m->done=3;return;}
 unsigned i=m->used;
 if(!i && (rx[4]&16)){m->start=tick;i=1;}
 if(i>=340){m->done=2;return;}
 struct movement_row *r=&m->rows[i];
 r->ack=ack_clock;r->x=v->hofs[112];r->y=v->vofs[112];r->tile_bytes=bytes;
 r->dirty=__builtin_popcountll(v->map_dirty);memcpy(r->page,rx+2,11);
 if(i){m->used=i+1;if((uint16_t)(tick-m->start)>=552)m->done=1;}
}
void nes_budget210_reset(void){
 memset(movement,0,sizeof *movement);movement->magic=0x31364d44;
 movement->edition=1061;movement->slot=movement_slot;
 memcpy(movement->save,movement_save,sizeof movement_save);
 ack_key=0;staged_bytes=0;
