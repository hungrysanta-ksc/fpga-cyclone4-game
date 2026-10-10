# SPDX-License-Identifier: MIT
"""Adapt actual116 source, retaining shared guards and normal base/menu recovery."""
from pathlib import Path
import zlib
from nes_menu098 import once
from nes_spi_boot import ROOT

def fixture():
 header=b'NES\x1a'+bytes([4,2,0,0])+bytes(8)
 prg=bytearray([0xea])*65536;prg[:3]=b'\x4c\x00\x80'
 prg[65530:]=b'\x00\x80'*3
 return header+prg+bytes(16384)

def adapt(src):
 src=Path(src)
 def edit(n,old,new):
  p=src/n;p.write_text(once(p.read_text(encoding='utf8'),old,new),encoding='utf8',newline='\n')
 for n in ['nes_run136.h','nes_run136.inc']:(src/n).write_bytes((ROOT/'src/nes/firmware'/n).read_bytes())
 p=src/'nes_menu_diagnostic.c';s=p.read_text(encoding='utf8')
 begin=s.index('static unsigned marker_geometry(');end=s.index('bool nes_menu_diagnostic_marker(',begin)
 s=s[:begin]+'''static unsigned marker_geometry(const uint8_t *path) {
 if(!path)return 0;
 const char *name=(const char *)path;
 for(const char *p=name;*p;p++)if(*p=='/'||*p=='\\\\')name=p+1;
 return !strcmp(name,"NES RUN 136.nh1")?80:0;
}
'''+s[end:];p.write_text(s,encoding='utf8',newline='\n')
 edit('nes_menu_diagnostic.c','#include "snes.h"','#include "snes.h"\n#include "nes_run136.h"')
 edit('nes_menu_diagnostic.c','char text[640]','char text[896]')
 edit('nes_menu_diagnostic.c','candidate=NES-CF86-MCU-094\\nboard_expected_hex=86','candidate=NES-RUN-136\\nboard_expected_hex=59')
 edit('nes_menu_diagnostic.c','menu_state=%s\\nstart_sent=0\\n','menu_state=%s\\nstart_sent=%u\\nrun_passed=%u\\nrun_error=%u\\nobserver_id_hex=%02x\\nrun_first=%lu\\nrun_last=%lu\\nrun_stopped=%lu\\nrun_flags=%u\\nrun_rom_error=%u\\n')
 edit('nes_menu_diagnostic.c','safe_to_reload,menu_state);','safe_to_reload,menu_state,nes_run136.start_sent,nes_run136.passed,nes_run136.error,nes_run136.observer_id,\n  (unsigned long)nes_run136.first,(unsigned long)nes_run136.last,(unsigned long)nes_run136.stopped,nes_run136.flags,nes_run136.rom_error);')
 edit('nes_menu_diagnostic.c','/sd2snes/nes-verify-last-094.txt','/sd2snes/nes-run-last-136.txt')
 edit('nes_menu_diagnostic.c','memset(&report,0,sizeof(report));','memset(&report,0,sizeof(report));memset(&nes_run136,0,sizeof(nes_run136));')
 edit('nes_menu_diagnostic.c','NES094 manual load/verify-only:','NES136 load/verify/bounded RUN:')
 edit('nes_menu_diagnostic.c','/sd2snes/nes/fine_x.nes','/sd2snes/nes/run136.nes')
 edit('nes_menu_diagnostic.c','/sd2snes/fpga_n86.bi3','/sd2snes/fpga_n136.bi3')
 edit('nes_h1_stm32.c','bool nes_menu_sd_probe(', '#include "nes_run136.inc"\nbool nes_menu_sd_probe(')
 # Only the final actual diagnostic probe, not the legacy044/MCU-load routine.
 p=src/'nes_h1_stm32.c';s=p.read_text(encoding='utf8')
 # CF86-only short identifier has no caller in this59/D4 candidate.
 first=s.index('static bool cf86_short094(');last=s.index('extern bool nes_menu_entry_only113(void);',first)
 s=s[:first]+s[last:]
 pos=s.index('bool nes_menu_sd_probe(');prefix,body=s[:pos],s[pos:]
 body=once(body,'header[6]!=0x40','header[6]!=0')
 body=once(body,'expected_crc=r->chr_32k?0x7a5a55c1u:0x5a226793u;',f'expected_crc=0x{zlib.crc32(fixture()):08x}u;')
 body=once(body,'if(r->chr_32k!=expected_chr32)','if(r->chr_32k||expected_chr32)')
 begin=body.index(' {\n  uint8_t tx[2]={0xcf,0}');end=body.index(' if(nes_menu_base_only116()) {',begin)
 body=body[:begin]+''' if(!identify136(&io,candidate)){r->result=NES_MCU_LOAD_ID;goto cleanup;}
'''+body[end:]
 body=once(body,'/* Exact iNES1 diagnostic geometry: mapper4, no trainer/battery/NES2,','/* Exact synthetic RUN136 geometry, no trainer/battery/NES2,')
 body=once(body,' if(!nes_checkpoint112("STOP_START",total,total))r->result=NES_MCU_LOAD_SPI;\n /* No START: this entry only verifies and restores the base/menu path. */',
 ''' if(!run136(&io,total,r)){r->result=NES_MCU_LOAD_SPI;goto cleanup;}
 if(!nes_checkpoint112("STOP_START",total,total))r->result=NES_MCU_LOAD_SPI;''')
 p.write_text(prefix+body,encoding='utf8',newline='\n')
 edit('nes_checkpoint112.c','NES116 seq=','NES136 seq=')
 edit('nes_checkpoint112.c','/sd2snes/nes-progress-116.txt','/sd2snes/nes-progress-136.txt')
