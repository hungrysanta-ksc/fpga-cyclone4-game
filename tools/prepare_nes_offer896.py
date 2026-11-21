"""Change only the offer query DMA source between two markers in one ARM link."""
from nes_raw506 import once
from prepare_nes_trial802 import PROBES, rename_edition

BASE = PROBES/'nes-input895/link'
WORK = PROBES/'nes-offer896'
MODES = {'FLASH':4,'SRAM':7}


def report_path(code, kind):
    path = f'/sd2snes/nes-{kind}-mmc896'
    return once(code,f'"{path}.txt"',f'(nes_boot_probe798==7?"{path}-sram.txt":"{path}-flash.txt")')


def prepare():
    src, dest = BASE/'src', WORK/'patch'
    rename_edition(src,dest,895,896)
    menu = dest/'nes_menu_diagnostic.c'
    code = menu.read_text()
    start = code.index(' if(!strcmp(name,"NES BOOT 896.nh1"))')
    end = code.index('\n}',start)
    code = code[:start]+''' if(!strcmp(name,"NES FLASH 896.nh1"))return 388;
 return !strcmp(name,"NES SRAM 896.nh1")?391:0;'''+code[end:]
    for kind in ('game-last','budget'):
        code = report_path(code,kind)
    menu.write_text(code,newline='\n')
    checkpoint = dest/'nes_checkpoint112.c'
    code = once(checkpoint.read_text(),'extern int nes_entry_transfer113;',
                'extern unsigned char nes_boot_probe798;\nextern int nes_entry_transfer113;')
    checkpoint.write_text(report_path(code,'progress'),newline='\n')
    name = 'nes_native165.c'
    code = (src/name).read_text()
    literal = '{0xd0,0x0,0x0,0x0,0x0,0xff,0xf7,0xa5}'
    code = once(code,'static const uint8_t status_request876[8]='+literal+';',
                '#define NES_OFFER896_BYTES '+literal+'''
static const uint8_t status_request876[8]=NES_OFFER896_BYTES;
/* The normal startup .data copy initializes this separate DMA source. */
static const uint8_t status_sram896[8] __attribute__((section(".data.nes_offer896"),aligned(4)))=NES_OFFER896_BYTES;''')
    code = once(code,'else {if(!fn(ctx,status_request876,rx,8))return fail(s,21);}', '''else {
  const uint8_t *request=nes_boot_probe798==7 ? status_sram896 : status_request876;
  if(!fn(ctx,request,rx,8))return fail(s,21);
 }''')
    code = once(code,'if(nes_boot_probe798==4){nes_input895_checked=true;',
                'if(nes_boot_probe798==4 || nes_boot_probe798==7){nes_input895_checked=true;')
    (dest/name).write_text(code,newline='\n')
    name = 'nes_run136.inc'
    code = once((src/name).read_text(),' r->stop_ok=true;nes_run136.stop_ok=true;',
                ''' r->stop_ok=true;nes_run136.stop_ok=true;
 /* RESET is asserted and STOP status and loaded length were checked above. */
 if(!nes_checkpoint112("OFFER_STOP_OK",nes_boot_probe798,nes_run136.first_error))return false;''')
    (dest/name).write_text(code,newline='\n')


if __name__=='__main__':
    prepare()
