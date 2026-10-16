/* SPDX-License-Identifier: MIT */
/* Test-only transaction bridge. Scheduling is NOT a shared performance clock. */
#include <stdio.h>
#include <stdlib.h>
#include <windows.h>
static unsigned seq[2]={1,1},who,turn;
static unsigned char input[4096],output[4096];
static DWORD idle;
__declspec(dllexport) int join208_poll(void){
 if(!idle)idle=GetTickCount();
 for(unsigned i=0;i<2;i++){
  unsigned channel=(turn+i)%2;char p[80];sprintf(p,"%c-%06u.req",channel?'S':'H',seq[channel]);
  FILE*f=fopen(p,"rb");if(!f)continue;
  unsigned n=(unsigned)fread(input,1,sizeof input,f);fclose(f);if(n<8)abort();
  who=channel;turn=1-channel;idle=GetTickCount();return input[0];
 }
 if(GetTickCount()-idle>120000)return 99;
 Sleep(1);return 0;
}
__declspec(dllexport) int join208_get(int i){if(i<0||i>=4096)abort();return input[i];}
__declspec(dllexport) void join208_put(int i,int v){if(i<0||i>=4096)abort();output[i]=(unsigned char)v;}
__declspec(dllexport) void join208_reply(int n){
 char a[80],b[80];sprintf(a,"%c-%06u.tmp",who?'S':'H',seq[who]);sprintf(b,"%c-%06u.rsp",who?'S':'H',seq[who]++);
 FILE*f=fopen(a,"wb");if(!f||fwrite(output,1,n,f)!=(unsigned)n)abort();fclose(f);if(rename(a,b))abort();
}
