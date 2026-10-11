/* SPDX-License-Identifier: MIT */
static int pad156_format(char *text,size_t size,int n){
 if(n<=0||(size_t)n>=size)return -1;
 int used=snprintf(text+n,size-(size_t)n,
  "apu_channel_writes_blocked=1\npad_trace_valid=%u\npad_trace_total=%u\npad_trace_count=%u\npad_trace_flags=%u\npad_trace_clock=NES_MASTER_CYCLES\npad_trace_kind=COMPLETED_8BIT_READ_CHANGED\n",
  nes_run136.pad_valid,nes_run136.pad_total,nes_run136.pad_count,nes_run136.pad_flags);
 if(used<0||(size_t)used>=size-(size_t)n)return -1;
 n+=used;
 if(nes_run136.pad_valid)for(unsigned i=0;i<nes_run136.pad_count;i++){
  unsigned b=nes_run136.pad_buttons[i];
  used=snprintf(text+n,size-(size_t)n,"pad_%02u_ticks=%lu mask=%02x buttons=%s%s%s%s%s%s%s%s%s\n",i,
   (unsigned long)nes_run136.pad_ticks[i],b,b?"":"NONE",b&1?"A|":"",b&2?"B|":"",b&4?"SELECT|":"",b&8?"START|":"",b&16?"UP|":"",b&32?"DOWN|":"",b&64?"LEFT|":"",b&128?"RIGHT|":"");
  if(used<0||(size_t)used>=size-(size_t)n)return -1;
  n+=used;
 }
 return n;
}
