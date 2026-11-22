"""Exercise palette scheduling at the checked slot-zero receipt on the MMC915 link."""
import argparse
import shutil
from pathlib import Path
from unittest.mock import patch

from nes_postobj916 import ARM, OUT, PROBES, LeadingRecord, monitor, peer
from nes_raw506 import once, sha

MODES = ('credit', 'two', 'follow')


def work(mode):
    return PROBES/f'nes-credit919-{mode}'


def prepare(mode):
    assert sha(ARM/'link/src/obj-nes-100/firmware.stm') == '98564fcd0f24e3d61eaccee021021a04fd48c45252bf14a676f79fa214e118a7'
    src = work(mode)/'link/src'
    shutil.copytree(ARM/'link', src.parent)
    def edit(file, at, new):
        path = src/file
        path.write_text(once(path.read_text(), at, new), newline='\n')
    call = 'op==3?NES_FINAL553:section==2?NES_MAP553:NES_ORDINARY553'
    edit('nes_native_sink165.c',call,
         'op==3?NES_FINAL553:section==2?NES_MAP553:section==3?NES_PALETTE919:NES_ORDINARY553')
    edit('nes_plan_service200.h','NES_HDMA554};','NES_HDMA554,NES_PALETTE919};')
    at = ' if(p->count){\n  /* Recheck tile'
    # After END issuance, while servicing the palette, use the live window owner.
    # A head that has not been checked cannot certify retirement or display.
    first = '''  if(!p->count && p->bulk_pending && !p->bulk[1] && p->bulk[2]==16 &&
     !p->bulk[3] && !p->bulk[4] && !p->bulk[5] && p->window->last[0]==7){
   return nes_plan200_valid(p) && complete485(p);
  }
'''
    second = '''  if(!p->count && p->window && p->window->last[1]==3 &&
     (uint16_t)(p->window->sent-p->bulk_until)==1 &&
     (uint16_t)(p->window->sent-p->window->retired)<=2 && p->bulk_valid){
   return nes_plan200_valid(p) && complete485(p);
  }
'''
    block = (first if mode!='follow' else '') + (second if mode!='credit' else '')
    edit('nes_plan_service200.c',at,' if(mode==NES_PALETTE919){\n  mode=NES_ORDINARY553;\n'+block+' }\n'+at)


def replay(temp, phase, cold, mode):
    with patch.object(peer,'PeerLink',LeadingRecord),patch.object(peer,'CLIENT',OUT/'consumer'),patch.object(peer,'monitor',monitor):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=work(mode),run_id='919'+mode)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action',choices=('prepare','replay','guards'))
    parser.add_argument('mode',choices=MODES)
    parser.add_argument('temp',nargs='?',type=Path)
    parser.add_argument('phase',nargs='?',type=int,choices=(1,2))
    parser.add_argument('--cold',action='store_true')
    a=parser.parse_args()
    if a.action=='prepare':
        prepare(a.mode)
    elif a.action=='replay':
        replay(a.temp,a.phase,a.cold,a.mode)
    else:
        from check_nes_supply905_arm import run
        run(Path.home()/'Downloads/test/Takahashi Meijin no Boukenjima 4 (J).nes',work(a.mode),915)
