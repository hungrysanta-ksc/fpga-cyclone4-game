// SPDX-License-Identifier: MIT
// Production receiver parses a single block captured from actual NROM RTL.
#include <assert.h>
#include <stdio.h>
#include "nes_native165.h"
static struct nes_native165 receiver;
int main(int argc,char **argv){
 assert(argc==2);FILE *f=fopen(argv[1],"r");assert(f);
 unsigned v,n=0;unsigned char bytes[256];while(fscanf(f,"%x",&v)==1){assert(n<256&&v<=255);bytes[n++]=(unsigned char)v;}assert(feof(f));fclose(f);
 nes_native165_reset(&receiver);
 int accepted=nes_native165_packet(&receiver,0,bytes,n);
 printf("accepted=%d state=%u error=%u records=%u bytes=%u generation=%u size=%u\n",accepted,receiver.state,receiver.error,receiver.records,receiver.bytes,receiver.generation,n);
 assert(accepted && receiver.state!=NES_NATIVE165_FAILED && receiver.token_valid && receiver.next_token==1);
 return 0;
}
