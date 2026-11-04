/* Keep the bus lease across each READ/POP/confirmation.
 * Poll and PREPARE share the same checked eight-byte status transaction. */
struct bus593 {
 nes_native165_transfer_fn transfer;
 void *ctx;
 uint8_t *tx, *rx;
};
static bool control593(struct bus593 *bus,unsigned cmd,unsigned token,unsigned arg) {
 frame(bus->tx,cmd,token,arg);
 return bus->transfer(bus->ctx,bus->tx,bus->rx,8) && status(bus->rx);
}

static bool request593(struct nes_native165 *s,struct bus593 *bus) {
 bool hello = !s->r_hello;
 /* The serialized D4 always has the same fields; zero defaults cover HELLO. */
 struct __attribute__((packed)) request593_wire {
  uint8_t command, version;
  uint32_t epoch, serial;
  uint16_t generation, token;
  uint32_t bitmap;
  uint8_t action, reserved;
  uint16_t checksum, trailer;
 } req = {.command=0xd4,.version=1,.epoch=s->r_epoch,.serial=s->r_active,
          .trailer=0xa55a};
 _Static_assert(sizeof(req)==24 && offsetof(struct request593_wire,checksum)==20,"D4 layout");
 if (hello) {
  req.serial=s->r_serial+1;
  req.action=s->r_base;
 } else {
  req.generation=s->generation; req.token=s->r_token; req.bitmap=s->r_request;
  req.action=s->r_phase==2 ? 4 : s->r_repair ? 3 : 2;
 }
 req.checksum=crc16((const uint8_t *)&req,20);
 if (!bus->transfer(bus->ctx,(const uint8_t *)&req,bus->rx,sizeof(req)) || !control593(bus,0xd0,0,0) ||
     !!(bus->rx[2]&4) == s->r_toggle) return fail(s,56);
 s->r_toggle ^= 1;
 s->r_hello = true;
 s->r_pending = false;
 return true;
}

bool nes_native165_poll(struct nes_native165 *s,nes_native165_transfer_fn fn,void *ctx) {
 if (!s || !fn || s->state >= NES_NATIVE165_COMMITTED) return false;
 uint8_t tx[257],rx[257];
 struct bus593 bus={fn,ctx,tx,rx};
 if ((!s->r_hello || s->r_pending) && !request593(s,&bus)) return false;
 if (s->ready183) {
  memcpy(rx,s->status183,8);
  s->ready183=false;
  if (!status(rx)) return fail(s,21);
 } else if (!control593(&bus,0xd0,0,0)) return fail(s,21);
 if (!(rx[2]&1)) return true;
 uint16_t token=(uint16_t)((rx[3]<<8)|rx[4]);
 unsigned n=(rx[5]<<8)|rx[6];
 if (n<2 || n>254) return fail(s,22);
 memset(tx,0,n+3); tx[0]=0xd1;
 if (!fn(ctx,tx,rx,n+3)) { ++nes_cost471_transfer_stops; return fail(s,23); }
 if (crc16(rx+1,n) != ((rx[n+1]<<8)|rx[n+2])) { ++nes_cost471_crc_errors; return fail(s,23); }
 if (!nes_native165_packet(s,token,rx+1,n)) return false;
 if (!control593(&bus,0xd2,token,0) || !control593(&bus,0xd0,0,0) ||
     ((rx[3]<<8)|rx[4]) != (uint16_t)(token+1)) return fail(s,27);
 if (s->r_commit) {
  s->r_serial=s->r_active; s->r_base_count=s->counts[0];
  s->r_base=true; s->r_commit=false; s->state=NES_NATIVE165_COMMITTED;
 }
 if (s->r_pending) return request593(s,&bus);
 if (s->state==NES_NATIVE165_RECEIVING && (rx[2]&1)) {
  memcpy(s->status183,rx,8); s->ready183=true;
 }
 return true;
}

bool nes_native165_prepare(struct nes_native165 *s,bool accept,nes_native165_transfer_fn fn,void *ctx) {
 if (!s || !fn || s->state!=NES_NATIVE165_COMPLETE) return false;
 uint8_t tx[8],rx[8];
 struct bus593 bus={fn,ctx,tx,rx};
 s->ready183=false;
 if (!control593(&bus,0xd0,0,0) || !(rx[2]&2) ||
     !control593(&bus,0xd3,s->generation,accept) || !control593(&bus,0xd0,0,0)) return fail(s,28);
 s->state=accept ? NES_NATIVE165_PREPARED : NES_NATIVE165_FAILED;
 return true;
}
