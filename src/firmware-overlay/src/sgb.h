/* sd2snes - SD card based universal cartridge for the SNES
   Copyright (C) 2009-2010 Maximilian Rehkopf <otakon@gmx.net>
   AVR firmware portion

   Inspired by and based on code from sd2iec, written by Ingo Korb et al.
   See sdcard.c|h, config.h.

   FAT file system access based on code by ChaN, Jim Brain, Ingo Korb,
   see ff.c|h.

   This program is free software; you can redistribute it and/or modify
   it under the terms of the GNU General Public License as published by
   the Free Software Foundation; version 2 of the License only.

   This program is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
   GNU General Public License for more details.

   You should have received a copy of the GNU General Public License
   along with this program; if not, write to the Free Software
   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

   sgb.h: SGB file structures
*/

#ifndef SGB_H
#define SGB_H

extern char SGBSR[30];

typedef struct __attribute__ ((__packed__)) _sgb_header {
  uint8_t entry[4];      /* 0x100 */
  uint8_t logo[48];      /* 0x104 */
  uint8_t name[16];      /* 0x134 */
  uint8_t licensee2[2];  /* 0x144 */
  uint8_t sgb;           /* 0x146 */
  uint8_t carttype;      /* 0x147 */
  uint8_t romsize;       /* 0x148 */
  uint8_t ramsize;       /* 0x149 */
  uint8_t destcode;      /* 0x14A */
  uint8_t licensee;      /* 0x14B */
  uint8_t mask_version;  /* 0x14C */
  uint8_t chk;           /* 0x14D */
  uint8_t gchk[2];       /* 0x14E */
} sgb_header_t;

typedef struct __attribute__ ((__packed__)) _sgb_romprops {
  uint8_t mapper_id;          /* FPGA mapper */
  uint8_t has_egbc;           /* .egbc dedicated core; keeps struct offsets */
  uint32_t ramsize_bytes;     /* CartRAM size in bytes */
  uint32_t romsize_bytes;     /* ROM size in bytes (rounded up) */
  uint8_t* sgb_boot;    /* SGB BOOT ROM filename */
  uint8_t* fpga_conf;   /* FPGA config file to load (default: base) */
  uint8_t has_sgb;            /* SGB presence flag */
  uint8_t has_rtc;            /* RTC presence flag */
  uint32_t srambase;          /* saveram base address */
  uint32_t sramsize_bytes;    /* saveram size in bytes */
  uint16_t fpga_sgbfeat;      /* SGB configuration bits */
  uint8_t error;              /* error text ID */
  uint8_t* error_param;       /* \0 separated list of parameters for error text */
  sgb_header_t header;        /* original header from ROM image */
} sgb_romprops_t;

enum { SGB_BIOS_CHECK = 0, SGB_BIOS_OK = 1, SGB_BIOS_MISMATCH = 2, SGB_BIOS_MISSING = 3 };

/* Replacement GBC core handshake.  The FPGA holds the handheld core in
 * reset until all three SRAM payloads and mapper masks are installed. */
#define SGB_FEAT_GBC_RUN 0x8000u
#if defined(GBC_PROBE_G12)
#define GBC_RENDERER_CRC32 0x0af44f8au
#ifdef GBC_SAVE_G12
#define GBC_LAUNCH_LABEL "G13C43"
#else
#define GBC_LAUNCH_LABEL "G12"
#endif
#elif defined(GBC_PROBE_G11)
#define GBC_RENDERER_CRC32 0xe25e6c6fu
#define GBC_LAUNCH_LABEL "G11"
#elif defined(GBC_PROBE_G10)
#define GBC_RENDERER_CRC32 0x13b53b36u
#define GBC_LAUNCH_LABEL "G10"
#elif defined(GBC_IO_G9)
#define GBC_RENDERER_CRC32 0xbcc0fda4u
#define GBC_LAUNCH_LABEL "G9"
#elif defined(GBC_VIDEO_G8)
#define GBC_RENDERER_CRC32 0xd9910b4fu
#define GBC_LAUNCH_LABEL "G8"
#elif defined(GBC_DIAGNOSTIC_G7)
#define GBC_RENDERER_CRC32 0x7ff5e435u
#define GBC_LAUNCH_LABEL "G7"
#elif defined(GBC_DIAGNOSTIC_G6)
#define GBC_RENDERER_CRC32 0xd49d14c9u
#define GBC_LAUNCH_LABEL "G6"
#elif defined(GBC_DIAGNOSTIC_G5)
#define GBC_RENDERER_CRC32 0xed862f4cu
#define GBC_LAUNCH_LABEL "G5"
#elif defined(GBC_DIAGNOSTIC_G4)
#define GBC_RENDERER_CRC32 0x8600d7ffu
#define GBC_LAUNCH_LABEL "G4"
#elif defined(GBC_DIAGNOSTIC)
#define GBC_RENDERER_CRC32 0xf89d79dbu
#define GBC_LAUNCH_LABEL "G3"
#else
#define GBC_RENDERER_CRC32 0x39df620cu
#define GBC_LAUNCH_LABEL "G2"
#endif

void sgb_id(sgb_romprops_t*, uint8_t *);
uint8_t sgb_update_file(uint8_t **);
uint8_t sgb_update_romprops(snes_romprops_t*, uint8_t *filename);
void sgb_cheat_program(void);
void sgb_load_sram(uint8_t *);
uint8_t sgb_bios_state(void);
uint8_t gbc_renderer_state(void);
void sgb_gtc_load(uint8_t* filename);
void sgb_gtc_save(uint8_t* filename);

#endif
