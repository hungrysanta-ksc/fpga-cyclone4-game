"""Materialize the two builds from the FF3 128-byte policy and Kirby bank observer."""
from pathlib import Path
import argparse
import shutil
from prepare_nes_pair1054 import ROOT, WORK, PROBES
from prepare_nes_kirby1023 import edit

def replace_section(path, start, end, replacement):
    text=path.read_text()
    assert text.count(start)==text.count(end)==1, path
    a,b=text.index(start),text.index(end)
    path.write_text(text[:a]+replacement+text[b:])

def prepare(profile):
    src=WORK/profile/'link'
    shutil.copytree(PROBES/'nes-ff3-1051B/link',src,
                    ignore=shutil.ignore_patterns('obj-*','.dep-*','*.log'))
    d=src/'src'
    if profile=='debug':
        edit(d,'nes_checkpoint112.c',('ff31051','debug1054'),('MMC1036 seq','DEBUG1054 seq'))
        f=d/'nes_menu_diagnostic.c'
        replace_section(f,' FRESULT opened=', '\n}\nstatic void save_report', ''' if(f_open(&log,path,FA_CREATE_ALWAYS|FA_WRITE)==FR_OK){
  f_write(&log,text,n,&written);f_close(&log);
 }''')
        text=f.read_text().replace('ff31051','debug1054')
        text=text.replace('board=%02x rom_crc=%08lx start=%u error=%u rom_error=%u screen=%02x ',
                          'id=%02x crc=%08lx start=%u err=%u rom=%u scr=%02x ')
        text=text.replace('screen_error=%02x frames=%lu final_generation=%u stop=%u base_safe=%u menu=%s',
                          'se=%02x frames=%lu gen=%u stop=%u base=%u menu=%s w1=%lu w2=%lu')
        f.write_text(text.replace('safe_to_reload,menu_state);','safe_to_reload,menu_state,(unsigned long)nes_budget210.displayed_window[0],(unsigned long)nes_budget210.displayed_window[1]);'))
        edit(d,'nes_budget210.c',('edition=1036','edition=1054'),
             ('if(tick<3000 || tick>=6000','if(tick<100 || tick>=6000'),
             ('if(tick<5500)return;\n  unsigned width=tick<5750?10:5;',
              'unsigned width=tick<5500?1500:(tick<5750?10:5);'))
        return
    f=d/'nes_h1_stm32.c'
    replace_section(f,'struct sd_source_context {','#include "nes_cf86_session094.h"\n#include "nes_css108.h"','')
    replace_section(f,'static __attribute__((noinline)) bool prepare_rom893','bool nes_menu_sd_probe(',
                    '#include "nes_retail_preload1054.inc"\n')
    shutil.copyfile(ROOT/'tools/nes_retail_preload1054.inc',d/'nes_retail_preload1054.inc')
    edit(d,'nes_h1_stm32.c',('case NES_ROM_BEGIN:return s->flags==1&&s->count==0;',
                             'case NES_ROM_BEGIN:return arg==3 && !s->flags && s->count==NES_CART_BYTES;'),
         ('case NES_ROM_END:return s->flags==2','case NES_ROM_END:return s->flags==0x82'),
         ('if(!nes_checkpoint_begin112())return false;', '''bool staged=retail_stage1054(path,r);
 changed_fpga=true; /* loading UI replaces the base configuration */
 if(nes_return_failed())return false;
 if(!nes_checkpoint_begin112())return false;'''),
         ('if(prepare_rom893(path,image','if(staged && prepare_rom893(path,image'),
         ('||(changed_fpga&&(r->result','||(staged&&changed_fpga&&(r->result'))
    (d/'nes_checkpoint112.c').write_text('''#include "nes_checkpoint112.h"
#include "nes_cf86_session094.h"
#include "nes_menu_return.h"
bool nes_checkpoint112(const char *stage,uint32_t bytes,uint32_t total){
 return !nes_return_failed() && nes_cf86_check094();
}
bool nes_checkpoint_begin112(void){return nes_checkpoint112(0,0,0);}
void nes_checkpoint_progress112(unsigned phase,uint32_t bytes,uint32_t total){}
''')
    replace_section(d/'nes_menu_diagnostic.c','static __attribute__((noinline)) void write_report893',
                    'bool nes_menu_diagnostic_run','static void save_report(const char *state,bool persist){}\n')

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('profile',choices=['debug','release'])
    prepare(p.parse_args().profile)
