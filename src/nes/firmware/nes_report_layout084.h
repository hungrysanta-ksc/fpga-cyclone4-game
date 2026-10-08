/* SPDX-License-Identifier: GPL-2.0-only */
#ifndef NES_REPORT_LAYOUT084_H
#define NES_REPORT_LAYOUT084_H
#include <stdbool.h>
#include <string.h>
/* 32 tiles, at least three blank columns on each edge; no silent truncation. */
static bool report_format084(char line[33],const char *text) {
 if(!text||strlen(text)>26)return false;
 unsigned n=(unsigned)strlen(text);
 memset(line,' ',32);line[32]=0;memcpy(line+(32-n)/2,text,n);
 return true;
}
#endif
