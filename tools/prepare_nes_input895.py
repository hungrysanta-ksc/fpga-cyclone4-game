"""Build selectable return points in the real first-block path of MMC894."""
from nes_raw506 import once
from prepare_nes_trial802 import PROBES, rename_edition

BASE = PROBES/'nes-block894/linkB'
WORK = PROBES/'nes-input895'
MODES = {'BOOT':2, 'BLOCK':3, 'OFFER':4, 'DATA':5, 'INIT':6}


def prepare():
    src, dest = BASE/'src', WORK/'patch'
    rename_edition(src,dest,894,895)
    path = dest/'nes_menu_diagnostic.c'
    menu = path.read_text()
    old = ' if(!strcmp(name,"NES BOOT 895.nh1"))return 386;'
    selectors = '\n'.join(f' if(!strcmp(name,"NES {key} 895.nh1"))return {384+mode};'
                          for key, mode in MODES.items() if key!='BLOCK')
    path.write_text(once(menu,old,selectors),newline='\n')
    name = 'nes_native165.c'
    code = once((src/name).read_text(),'static const uint8_t status_request876',
                'extern unsigned char nes_boot_probe798;\nbool nes_input895_checked;\nstatic const uint8_t status_request876')
    code = once(code,' memset(tx,0,n+3);tx[0]=0xd1;', '''
 /* Stop on an actual, CRC-checked first offer with a legal length. */
 if(nes_boot_probe798==4){nes_input895_checked=true;return true;}
 memset(tx,0,n+3);tx[0]=0xd1;''')
    code = once(code,' if(!nes_native165_packet(s,tok,rx+1,n))return false;', '''
 if(!nes_native165_packet(s,tok,rx+1,n))return false;
 /* The block has been decoded. Leave it owned by the FPGA until STOP. */
 if(nes_boot_probe798==5){nes_input895_checked=true;return true;}''')
    (dest/name).write_text(code,newline='\n')
    name = 'nes_runtime_board165.inc'
    code = once((src/name).read_text(),'/* Large RUN storage',
                'extern bool nes_input895_checked;\n/* Large RUN storage')
    code = once(code,' (void)nes_runtime165_begin',' nes_input895_checked=false;\n bool started=nes_runtime165_begin')
    start = code.index(' bool confirmed=false;')
    end = code.index(' nes_cost471_end();',start)
    code = code[:start]+''' bool confirmed=started && nes_boot_probe798==6;
 for(unsigned polls=0;started && !confirmed && polls<8192;++polls){
  if(!nes_runtime165_step(&native_runtime165))break;
  confirmed=nes_boot_probe798==3 ? work.receiver.token_valid : nes_input895_checked;
 }
'''+code[end:]
    code = once(code,'nes_boot_probe798==3)native_frames222','nes_boot_probe798>=3)native_frames222')
    (dest/name).write_text(code,newline='\n')
    name = 'nes_run136.inc'
    (dest/name).write_text(once((src/name).read_text(),'nes_boot_probe798==3?__get_MSP()',
                               'nes_boot_probe798>=3?__get_MSP()'),newline='\n')
    name = 'nes_cost471.c'
    code = (src/name).read_text()
    start = code.index(' n=REPORT828(text,size,n,"cost_schema=474')
    end = code.index('\n return n;\n}',start)
    # Keep the sampling and timing code intact. These short probes do not
    # generate FPS measurements. Report SPI counts and errors after STOP.
    code = code[:start]+''' int written=snprintf(text+n,size-(unsigned)n,
  "first_input_D0=%lu\\nfirst_input_D1=%lu\\nfirst_input_D2=%lu\\nfirst_input_E0=%lu\\nfirst_input_crc_errors=%lu\\n",
  (unsigned long)nes_cost471_ops[0].calls,(unsigned long)nes_cost471_ops[1].calls,
  (unsigned long)nes_cost471_ops[2].calls,(unsigned long)nes_cost471_ops[4].calls,
  (unsigned long)nes_cost471_crc_errors);
 if(written<0 || (unsigned)written>=size-(unsigned)n)return -1;
 n+=written;'''+code[end:]
    (dest/name).write_text(code,newline='\n')


if __name__=='__main__':
    prepare()
