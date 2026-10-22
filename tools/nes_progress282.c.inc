/* Command-start snapshots are conservative: current E1/E9 acceptance is NOT
 * included. Old retirement may under-credit; it must never authorize a future
 * packet. CRC, namespace counters and flags are checked before caching. */
unsigned plan_cache282,plan_flags282,plan_accepted282;
unsigned progress282(const uint8_t *p,unsigned n){
 if(state259.error)return 0;
 if(n<12)return 1; /* short terminal E9 keeps the checked E8 fallback */
 unsigned c=0;for(unsigned i=1;i<11;i++)c=crc8(c,p[i]);
 if(p[1]!=0xfa||p[11]!=c||(p[2]&0xf8)||(p[7]&0xf8)||(p[8]&0xf8)||((p[8]&1)&&(p[8]&6)))return fail(21);
 unsigned a=(p[3]<<8)|p[4],r=(p[5]<<8)|p[6];
 unsigned pending=(uint16_t)(state259.sent-state259.retired),delta=(uint16_t)(r-state259.retired),used=(uint16_t)(a-r);
 if(a!=state259.sent||pending>4||delta>pending||used>4||!!(p[2]&1)!=(used!=0)||!!(p[2]&4)!=(used==4))return fail(22);
 state259.retired=r;status259[7]=p[7];
 plan_flags282=p[8];plan_accepted282=(p[9]<<8)|p[10];plan_cache282=1;
 return 1;
}
