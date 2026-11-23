/* Included before planner221 in the MMC955 runtime. Only committed input may
 * hint immutable CHR. The ordinary planner still owns slot allocation. */
extern uint8_t nes_wire_crc807(const uint8_t *,unsigned);
static bool page_hint963(struct nes_native_runtime165 *s){
 const struct nes_native165 *r=s->receiver;
 /* Scan the sorted tag directory once. Only examine fragments for a full
  * aligned directory run. A hint may overfetch hidden rows without changing
  * the independently validated rendering plan. */
 unsigned consecutive=0;
 for(unsigned i=0;i<r->ntiles;i++){
  unsigned tag=r->tiles[i].tag;
  if(!(tag&7))consecutive=0;
  if(!(r->tiles[i].kind&2) || (tag&7)!=consecutive){consecutive=0;continue;}
  if(++consecutive!=8)continue;
  unsigned base=tag-7,mask=0;
  for(unsigned k=0;k<r->counts[2];k++){
   uint64_t obj=r->objects[k];
   unsigned id=obj&8191;
   if((id&~7u)==base && (uint8_t)(obj>>38)==255)mask|=1u<<(id&7);
  }
  if(mask==255){
   uint8_t tx[7]={0xeb,r->generation,r->generation>>8,base,base>>8,0,0xa5},rx[7];
   tx[5]=nes_wire_crc807(tx,5);
   return transfer(s,tx,rx,sizeof tx);
  }
 }
 return true;
}
