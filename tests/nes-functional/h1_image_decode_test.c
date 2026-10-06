/* SPDX-License-Identifier: MIT */
/* Run the pinned MCU rle_file_getc implementation on the generated BI3. */
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include "rle.h"
int file_status,file_res;
static FILE *input;
uint8_t file_getc(void) {
 int c=fgetc(input);
 if(c==EOF){file_status=1;return 0;}
 return (uint8_t)c;
}
int main(int argc,char **argv) {
 assert(argc==3);
 input=fopen(argv[1],"rb");FILE *raw=fopen(argv[2],"rb");assert(input && raw);
 unsigned count=0;int want;
 while((want=fgetc(raw))!=EOF) {
  uint8_t got=rle_file_getc();
  assert(!file_status && !file_res && got==(uint8_t)want);count++;
 }
 (void)rle_file_getc();assert(file_status && !file_res);
 fclose(input);fclose(raw);
 printf("PASS MCU rle_file_getc exact bytes=%u and EOF\n",count);
 return 0;
}
