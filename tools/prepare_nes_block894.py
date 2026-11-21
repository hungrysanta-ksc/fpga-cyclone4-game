"""Prepare a diagnostic that stops after the first checked input block."""
from pathlib import Path
from nes_raw506 import once
from prepare_nes_trial802 import rename_edition

PROBES = Path(__file__).resolve().parents[2] / 'probes'
BASE = PROBES / 'nes-first893/linkC'
WORK = PROBES / 'nes-block894'


def prepare():
    src = BASE / 'src'
    dest = WORK / 'patchB'
    rename_edition(src, dest, 893, 894)
    path = dest / 'nes_menu_diagnostic.c'
    menu = once(path.read_text(), 'return !strcmp(name,"NES MMC3 894.nh1")?384:0;',
                'return !strcmp(name,"NES BLOCK 894.nh1")?387:0;')
    menu = once(menu, ' if(!strcmp(name,"NES START 894.nh1"))return 385;', '')
    path.write_text(menu, newline='\n')
    file = 'nes_run136.inc'
    code = once((src/file).read_text(), 'nes_boot_probe798,total))return false;',
                'nes_boot_probe798,nes_boot_probe798==3?__get_MSP():total))return false;')
    (dest/file).write_text(code, newline='\n')
    file = 'nes_runtime_board165.inc'
    code = (src/file).read_text()
    code = once(code,'if(native_boot172(io) && !nes_boot_probe798)',
                'if(native_boot172(io) && nes_boot_probe798==3)')
    code = once(code,'NULL,6000,&work.resident','NULL,500,&work.resident')
    begin = code.index(' while(nes_runtime165_step')
    end = code.index(' /* Only scalar results',begin)
    code = code[:begin]+''' /* A successful step checks the D1 payload CRC, D2 status and following
  * D0 token. A local token alone cannot authorize diagnostic success. */
 bool confirmed=false;
 for(unsigned polls=0;polls<8192 && nes_runtime165_step(&native_runtime165);++polls){
  if(work.receiver.token_valid){confirmed=true;break;}
 }
 nes_cost471_end();
 if(!confirmed&&!nes_run136.first_error)nes_run136.first_error=4;
'''+code[end:]
    (dest/file).write_text(code,newline='\n')


if __name__=='__main__':
    prepare()
