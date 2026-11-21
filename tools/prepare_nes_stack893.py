"""Return the SD file and verification buffer to the stack before starting RUN."""
from pathlib import Path
import argparse
from nes_raw506 import once
from prepare_nes_trial802 import rename_edition

ROOT=Path(__file__).resolve().parents[2]
SOURCE=ROOT/'probes/nes-reset892/link/src'
WORK=ROOT/'probes/nes-first893'


def prepare(dest):
    rename_edition(SOURCE,dest,892,893)
    text=(SOURCE/'nes_h1_stm32.c').read_text()
    prefix,entry=text.split('bool nes_menu_sd_probe(',1)
    signature,entry=entry.split(' {\n',1)
    header,entry=entry.split(' if(nes_menu_base_only116())goto configure116;',1)
    entry=once(entry,' if(!nes_checkpoint112("OPEN_INPUT",0,0))return false;','')
    load,rest=entry.split(' if(!run136',1)
    _,rest=rest.split('cleanup:\n',1)
    guard,rest=rest.split(' if(opened',1)
    close,tail=(' if(opened'+rest).split(' if(report->verify.stop_ok)',1)
    start=header.index(' FIL file;')
    end=header.index(' if(!r')
    header=header[:start]+''' bool changed_fpga=false,begin_sent=false;
'''+header[end:]
    load=load.replace('&io','io').replace('changed_fpga=true','*changed=true').replace('begin_sent=true','*begun=true')
    # OPEN_INPUT is the last entry checkpoint outside this helper. The caller
    # retains its original immediate return if that checkpoint fails.
    worker='''static __attribute__((noinline)) bool prepare_rom893(const char *path,const char *image,bool expected_chr32,
 struct nes_menu_probe_report *candidate,const struct nes_rom_spi_io *io,bool *changed,bool *begun){
 struct nes_sd_readback_report *report=&candidate->sd;
 struct nes_mcu_load_report *r=&report->load;
 struct nes_rom_spi_status status={0};
 FIL file;
 uint8_t header[16],buffer[256];
 uint32_t total=0,expected_crc=0,crc=0xffffffffu;
 bool opened=false;
 if(nes_menu_base_only116())goto configure116;
'''+load+''' return true;
cleanup:
 if(opened){
  /* Before configuration the file is still ours. A configured board with
   * incomplete verification enters fail-stop before further SD access. */
  if(nes_cf86_monitoring094())(void)nes_cf86_check094();
  if(*changed||nes_return_failed())nes_cf86_fail094();
'''+''.join(' '+line for line in close.replace('if(opened&&','if(').splitlines(True))+''' }
 return false;
}
'''
    wrapper='bool nes_menu_sd_probe('+signature+' {\n'+header+''' if(!nes_menu_base_only116()&&!nes_checkpoint112("OPEN_INPUT",0,0))return false;
 if(prepare_rom893(path,image,expected_chr32,candidate,&io,&changed_fpga,&begin_sent)){
  if(!run136(&io,0x60000u,r,NES_MMC479_ROM_CRC)||
     !nes_checkpoint112("STOP_START",0x60000u,0x60000u))r->result=NES_MCU_LOAD_SPI;
 }
'''+guard+' if(report->verify.stop_ok)'+tail
    assert 'goto cleanup' not in wrapper and 'expected_crc' not in wrapper
    wrapper=once(wrapper,' const struct nes_rom_spi_io io=', ' static const struct nes_rom_spi_io io=')
    (dest/'nes_h1_stm32.c').write_text(prefix+worker+wrapper,newline='\n')
    path=dest/'nes_menu_diagnostic.c'
    menu=path.read_text()
    cut=menu.index(' FRESULT opened=f_open(&log,"/sd2snes/nes-game-last-')
    end=menu.index('\n}',cut)
    helper='''static __attribute__((noinline)) void write_report893(const char *path,const char *label,const char *text,UINT n){
 FIL log;UINT written=0;
 FRESULT opened=f_open(&log,path,FA_CREATE_ALWAYS|FA_WRITE),saved=opened,closed=opened;
 if(opened==FR_OK){saved=f_write(&log,text,n,&written);closed=f_close(&log);}
 printf("NES %s o%u w%u c%u %u/%u\\n",label,opened,saved,closed,(unsigned)written,(unsigned)n);
}
'''
    menu=menu[:cut]+''' write_report893("/sd2snes/nes-game-last-mmc893.txt","last",text,(UINT)n);
 int budget_n=nes_budget210_format(text,sizeof text);
 if(budget_n>0)write_report893("/sd2snes/nes-budget-mmc893.txt","budget",text,(UINT)budget_n);
 if(irq)NVIC_EnableIRQ(OTG_FS_IRQn);'''+menu[end:]
    menu=once(menu,'static void save_report(',helper+'static void save_report(')
    menu=once(menu,'char text[6144];FIL log;UINT written=0;','char text[6144];')
    # save_report already prints the BLOCKED_RESET_HELD state over UART.
    menu=once(menu,'{save_report("BLOCKED_RESET_HELD",false);printf("NES RESET/USB held\\n");}',
              'save_report("BLOCKED_RESET_HELD",false);')
    path.write_text(menu,newline='\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('dest',type=Path)
    prepare(p.parse_args().dest)
