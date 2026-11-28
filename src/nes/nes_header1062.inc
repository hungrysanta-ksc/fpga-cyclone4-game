 /* Total-length validation above uses the legacy 8-bit size fields. All
  * fitted geometries are exactly representable there. Reject other size
  * encodings, trainers, consoles, timing modes and devices before routing. */
 if((h[7]&12)==8){
  if((h[7]&3) || h[9] || (h[6]&12) || h[12] || h[13] || h[14] || h[15]>1)return 0;
  unsigned mapper=(h[6]>>4)|(h[7]&0xf0)|((h[8]&15)<<8);
  unsigned sub=h[8]>>4;
  if(mapper==5 && !sub && h[6]==0x52 && h[4]==64 && !h[5] &&
     h[10]==0x70 && h[11]==7)return 0x84;
  /* CNROM's current latch takes CPU data without bus-conflict AND.
   * Only the explicit conflict-free NES2 wiring is admitted here. */
  if(mapper==3 && sub==1 && h[6]==0x31 && h[4]==2 && h[5]==4 && !h[10] && !h[11])return 0x81;
  if(mapper==7 && sub==1 && h[6]==0x70 && h[4]==32 && !h[5] && !h[10] && h[11]==7)return 0x82;
  return 0;
 }
