/* Typed receive sections, after independently validating the complete map. */
static uint16_t crc_byte593(uint16_t crc, uint8_t value) {
 unsigned x = (crc >> 8) ^ value;
 x ^= x >> 4;
 return (uint16_t)((crc << 8) ^ (x << 12) ^ (x << 5) ^ x);
}

static bool check_map593(struct nes_native165 *s) {
 uint16_t crc = 0xffff;
 for (unsigned i = 0; i < s->counts[0]; ++i) {
  uint16_t word = s->maps[i];
  if (word & 0x8000) return false;
  crc = crc_byte593(crc, (uint8_t)word);
  crc = crc_byte593(crc, (uint8_t)(word >> 8));
  require_tile(s, word & 8191, 1);
 }
 if (crc != s->r_mapcrc) {
  /* Tag scratch has no external readers before META_END. */
  memset(s->required,0,sizeof(s->required));
  s->missing = 0;
  if (s->r_repair) return false;
  s->r_repair = true;
  unsigned rows = s->counts[0] / 33;
  s->r_request = UINT32_MAX >> (32 - rows);
  s->r_seen = 0;
  s->at[0] = 0;
 } else {
  s->at[0] = s->records = s->counts[0];
  s->r_length = 2 * s->records;
  s->r_crc = crc;
  s->next_kind = 1;
  s->r_request = 0;
  s->r_phase = 2;
 }
 s->r_ord = 255;
 s->r_pending = true;
 return true;
}

static bool finish_meta593(struct nes_native165 *s) {
 for (unsigned k=0; k<6; ++k)
  if (s->at[k] != s->counts[k]) return false;
 unsigned slot = 0;
 for (unsigned y=0; y<224; ++y)
  if (((s->raster[y] >> 49) & 1) && (s->raster[y] >> 50) != slot++) return false;
 if (slot != s->patch_count || s->missing > 512) return false;
 for (unsigned t=0; t<8192; t+=16) {
  uint32_t pending;
  memcpy(&pending, s->required + (t >> 2), sizeof(pending));
  while (pending) {
   unsigned shift = (unsigned)__builtin_ctz(pending) & ~1u;
   if (s->ntiles == 512) return false;
   struct nes_native165_tile *tile = &s->tiles[s->ntiles++];
   tile->tag = t + (shift >> 1);
   tile->kind = (pending >> shift) & 3u;
   pending &= ~(3u << shift);
  }
 }
 if (s->ntiles != s->missing) return false;
 s->missing = 0;
 s->last_tile = 0;
 s->next_kind = 7;
 return true;
}

/* The wire width and destination stride describe the same section for both
 * literal and repeat. Wide geometry fields have zeroed high bytes from BEGIN. */
struct section_layout593 {
 uint16_t offset;
 uint8_t width, stride;
};
#define SECTION593(field, width) {offsetof(struct nes_native165,field), width, sizeof(((struct nes_native165 *)0)->field[0])}
static const struct section_layout593 sections593[]={
 {0,0,0}, SECTION593(rows,1), SECTION593(objects,7), SECTION593(exceptions,4),
 SECTION593(raster,7), SECTION593(palette,1), SECTION593(raw_pixels,1)
};

static bool check_value593(struct nes_native165 *s, unsigned kind, unsigned index) {
 switch (kind) {
 case 1: return (s->rows[index] >> 3) < s->counts[0]/33u;
 case 2: {
  uint64_t obj=s->objects[index];
  if (obj >> 49) return false;
  require_tile(s,(unsigned)obj&8191,2);
  return true;
 }
 case 3: {
  uint32_t exc=s->exceptions[index];
  if (((exc>>6)&8191) >= 7392) return false;
  require_tile(s,exc>>19,1);
  return true;
 }
 case 4: {
  uint64_t line=s->raster[index];
  if ((line >> 49)&1) return !(line&((UINT64_C(1)<<49)-1)) && (line>>50)<s->patch_count;
  return !(line>>49) && ((line>>44)&31)<s->counts[5]/32u;
 }
 case 5: return s->palette[index]<64;
 default: return s->raw_pixels[index]<64;
 }
}

static bool nonmap593(struct nes_native165 *s, const uint8_t *p, unsigned n) {
 bool raw = s->r_phase == 3;
 if (s->state != NES_NATIVE165_RECEIVING) return false;
 while (n) {
  if (n == 8 && get591(p) == (raw ? 0xf001 : 0xf004)) {
   if (get591(p+2) != s->r_length || get591(p+4) != s->records ||
       get591(p+6) != s->r_crc) return false;
   if (raw) {
    if (s->bytes != 256u*s->patch_count) return false;
    s->state = NES_NATIVE165_COMPLETE;
   } else if (!finish_meta593(s)) return false;
   ++s->r_phase;
   s->r_ord = 255;
   return true;
  }
  if (n < 3) return false;
  unsigned kind = p[0] & 7, mode = p[0] >> 3, count = get591(p+1);
  if (!kind || kind > 6 || raw != (kind == 6) || !count || count > 256 ||
      mode > 2 || (mode == 2 && (kind != 4 || count < 2)) ||
      (mode == 1 && (kind == 1 || kind == 5 || count < (raw ? 10u : 2u)))) return false;
  if (!raw) {
   while (s->next_kind < 6 && s->at[s->next_kind] == s->counts[s->next_kind]) ++s->next_kind;
   if (kind != s->next_kind) return false;
  }
  const struct section_layout593 *layout = &sections593[kind];
  unsigned w = layout->width, body = w*(mode ? 1 : count);
  unsigned start = raw ? s->bytes : s->at[kind];
  unsigned cap = raw ? 256u*s->patch_count : s->counts[kind];
  if (start + count > cap || body > n-3) return false;
  const uint8_t *value = p+3;
  uint8_t *dest = (uint8_t *)s + layout->offset + start*layout->stride;
  for (unsigned i=0; i<count; ++i, dest+=layout->stride) {
   if (mode == 2 && i) s->raster[start+i] = raster_next471(s->raster[start+i-1]);
   else memcpy(dest,value,w);
   if (!check_value593(s,kind,start+i)) return false;
   if (mode == 2 && s->raster[start+i] >> 49) return false;
   for (unsigned j=0; j<w; ++j) s->r_crc = crc_byte593(s->r_crc,dest[j]);
   if (!mode) value+=w;
  }
  p += 3+body;
  if (raw) s->last_tile = s->bytes = start + count;
  else s->at[kind] = start + count;
  s->r_length += w*count;
  s->records += count;
  n -= body+3;
 }
 return true;
}
