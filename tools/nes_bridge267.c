/* SPDX-License-Identifier: MIT */
/* Blocking simulator/ARM rendezvous. Wall time never advances RTL time. */
#include <stdio.h>
#include <stdint.h>
#include <windows.h>
static unsigned serial, count, delay, tx[259], rx[259];
static int fail267(void) { return -1; }
int bridge267(int op, int a, int b) {
 char path[80], temporary[80]; FILE *f;
 if(op==0) {
  sprintf(path,"arm-frame%d",a); f=fopen("arm-frame.tmp","w");
  if(!f)return fail267();
  fprintf(f,"%d\n",a); fclose(f);
  return rename("arm-frame.tmp",path)==0?0:fail267();
 }
 if(op==1) {
  ++serial; sprintf(path,"arm-req%u",serial); DWORD start=GetTickCount();
  while(!(f=fopen(path,"r"))) { if(GetTickCount()-start>120000)return fail267(); Sleep(1); }
  if(fscanf(f,"%u %u",&count,&delay)!=2||count>259){fclose(f);return fail267();}
  for(unsigned i=0;i<count;i++)if(fscanf(f,"%x",&tx[i])!=1){fclose(f);return fail267();}
  fclose(f);return (int)count;
 }
 if(op==2)return a>=0&&(unsigned)a<count?(int)tx[a]:fail267();
 if(op==3){if(a<0||(unsigned)a>=count)return fail267();rx[a]=(unsigned)b;return 0;}
 if(op==4){
  sprintf(path,"arm-rsp%u",serial);sprintf(temporary,"arm-rsp%u.tmp",serial);
  f=fopen(temporary,"w");if(!f)return fail267();
  fprintf(f,"%u %u\n",(unsigned)a,(unsigned)b);
  for(unsigned i=0;i<count;i++)fprintf(f,"%02x ",rx[i]);
  fclose(f);return rename(temporary,path)==0?0:fail267();
 }
 if(op==5)return (int)delay;
 return fail267();
}
