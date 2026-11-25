/* Kirby uses the 2 KiB raw scratch as a 16384-bit BG presence set until
 * META_END. OBJ geometry is already stored losslessly in its own array. */
static void require_tile(struct nes_native165 *s,unsigned tag,unsigned kind){
 (void)kind;
 uint8_t *byte=&s->required[tag>>3];
 unsigned bit=1u<<(tag&7);
 if(!(*byte&bit))s->missing++;
 *byte|=bit;
}
static bool finish_tiles1023(struct nes_native165 *s){
 if(s->missing>512)return false;
 for(unsigned base=0;base<16384;base+=32){
  uint32_t word;memcpy(&word,s->required+(base>>3),sizeof(word));
  while(word){
   unsigned tag=base+__builtin_ctz(word);
   s->tiles[s->ntiles++]=(struct nes_native165_tile){.tag=tag,.kind=1};
   word&=word-1;
  }
 }
 if(s->ntiles!=s->missing)return false;
 for(unsigned i=0;i<s->counts[2];i++){
  unsigned tag=nes_obj_tag1023(s->objects[i]),lo=0,hi=s->ntiles;
  while(lo<hi){
   unsigned m=(lo+hi)/2;
   if(s->tiles[m].tag<tag)lo=m+1;else hi=m;
  }
  if(lo<s->ntiles && s->tiles[lo].tag==tag){s->tiles[lo].kind|=2;continue;}
  if(s->ntiles==512)return false;
  memmove(&s->tiles[lo+1],&s->tiles[lo],(s->ntiles-lo)*sizeof(s->tiles[0]));
  s->tiles[lo]=(struct nes_native165_tile){.tag=tag,.kind=2};s->ntiles++;
 }
 for(unsigned i=0;i+7<s->ntiles&&!s->obj_page_plus_one964;i++){
  unsigned tag=s->tiles[i].tag;
  if(!(tag&7) && (s->tiles[i].kind&2) && s->tiles[i+7].tag==tag+7)page964(s,tag);
 }
 return true;
}
