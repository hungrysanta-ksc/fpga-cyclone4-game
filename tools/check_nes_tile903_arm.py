"""Run boot, log, timer, independent CRC, STOP and menu checks on the release link."""
import sys
from pathlib import Path
from check_nes_frame900_arm import verify
from check_nes_frame862_arm import timer_cases
from check_nes_menu533 import check
from check_nes_sram897 import check_game_path
from package_nes_trial704 import checked, save
from package_nes_trial855 import loader
from prepare_nes_tile903 import WORK


def run(game):
    src=WORK/'link/src'
    out=WORK/'proof'
    out.mkdir(exist_ok=True)
    verify(903,src,out)
    save(out/'timer.json',timer_cases(src))
    loader(game,src,903,out)
    save(out/'menu.json',check(src,'903'))
    cases,ram,entry=check_game_path(src)
    save(out/'sram.json',dict(cases=cases,ram=ram,entry=entry))
    checked('check_nes_transfer512_recovery.py',['--arm',src,'--trial','903','--fault','none','--out',out/'base'],out/'base.log')
    print('PASS903 final ARM boot, SRAM D0, CRC, timer, STOP and base/menu')


if __name__=='__main__':
    run(Path(sys.argv[1]))
