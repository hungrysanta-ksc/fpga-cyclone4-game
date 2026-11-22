"""Use one indexed WRAM address per HDMA row during the 65816 SEAL check."""
import argparse
import json
import shutil
from pathlib import Path
from unittest.mock import patch

from boot_nes_column854 import build
from build_nes_trace_replay import Code
from nes_prefetch912 import ORIGIN, OUT, LeadingRecord, peer, monitor
from prepare_nes_trial915 import PROBES
from nes_raw506 import once


CLIENT=PROBES/'nes-postobj916'/'consumer'
ARM=PROBES/'nes-trial915-step'
ONE_DRAIN=PROBES/'nes-postobj916-drain'
REPEAT=PROBES/'nes-postobj916-repeat'
AFTER_DMA=PROBES/'nes-postobj916-after-dma'


def client():
    parent=OUT/'consumer'
    labels=json.loads((parent/'labels.json').read_bytes())
    body=bytearray((parent/'body.bin').read_bytes())
    start,end=labels['values181'],labels['invalid_pop181']
    c=Code(start)
    c.labels.update(labels)
    # Y points to A's mode word; $70 is the independently selected WRAM
    # table base. X holds this row only and must survive success and failure.
    c.emit(0xda,0x98,0x18,0x65,0x70,0xaa)  # PHX / TYA / CLC / ADC $70 / TAX
    def load(displacement):
        c.long(0xbf,0x7f0000+displacement)
    def expect_dp(displacement,expected,subtract_bank=False):
        load(displacement)
        if subtract_bank:c.emit(0x38,0xe9,0x20,0)
        c.emit(0xc5,expected)
        c.branch(0xd0,'invalid_values916')
    load(0)
    c.long(0xdf,0x7f0051)  # A/B mode + MOSAIC
    c.branch(0xd0,'invalid_values916')
    expect_dp(2,0x7a)
    expect_dp(83,0x7a,True)
    expect_dp(162,0x7c)
    expect_dp(164,0x7e)
    c.emit(0xfa,0xc8,0xc8,0xc8,0xc8,0xc0,81,0)
    c.branch(0xb0,'overrun916')
    c.jump('table181')
    c.label('invalid_values916')
    c.emit(0xfa)
    c.label('overrun916')
    c.jump('invalid181')
    code=c.finish()
    assert len(code)<=end-start and body[start-ORIGIN:start-ORIGIN+4]==bytes.fromhex('b7708578')
    body[start-ORIGIN:end-ORIGIN]=code+bytes(end-start-len(code))
    build(parent,CLIENT,bytes(body),c.labels)


def prepare_drain():
    link=ONE_DRAIN/'link'
    shutil.copytree(ARM/'link',link)
    src=link/'src/nes_native_sink165.c'
    src.write_text(once(src.read_text(),
        '   for(unsigned sample=0;sample<4;sample++)\n    if(!nes_window184_drain(w,consumed))',
        '   if(!nes_window184_drain(w,consumed))'),newline='\n')


def prepare_repeat(after_dma=False):
    link=(AFTER_DMA if after_dma else REPEAT)/'link'
    shutil.copytree(ONE_DRAIN/'link',link)
    src=link/'src/nes_plan_service200.c'
    s=once(src.read_text(),'if(phase==NES_PLAN215_FINISH&&!complete485(p))return false;',
           'if(phase==NES_PLAN215_FINISH)result|=8;')
    s=once(s,'if((mode==NES_MAP553 || mode==NES_ORDINARY553) && p->bulk_pending &&',
           '''if((!(flags&8) || (mode==NES_ORDINARY553 && p->bulk[1] &&
       (uint16_t)(p->window->sent-p->bulk_until)<2)) &&
      (mode==NES_MAP553 || mode==NES_ORDINARY553) && p->bulk_pending &&''')
    s=once(s,'A repeat was already checked and drained inside poll. Only a new',
           'Bit 3 identifies a repeat after the complete descriptor comparison. A new')
    s=once(s,'descriptor can leave bulk_pending set here. A map may take one of',
           'descriptor or an eligible repeat can still owe bulk_until. Allow one of')
    if after_dma:
        s=once(s,'(mode==NES_ORDINARY553 && p->bulk[1] &&',
               '(mode==NES_ORDINARY553 && (p->window->status_flags&8) && p->bulk[1] &&')
    src.write_text(s,newline='\n')


def replay(temp,phase,cold,variant):
    arm,tag={'index':(ARM,'916index'),'drain':(ONE_DRAIN,'916drain'),
             'repeat':(REPEAT,'916repeat'),'after-dma':(AFTER_DMA,'916afterdma')}[variant]
    client_dir=CLIENT if variant=='index' else OUT/'consumer'
    with patch.object(peer,'PeerLink',LeadingRecord),patch.object(peer,'CLIENT',client_dir),patch.object(peer,'monitor',monitor):
        peer.compare(temp,phase,cold,True,edition=915,work_arm=arm,run_id=tag)


def guards(temp):
    from guard_nes_output852 import run
    from check_nes_prefetch912 import stop_test
    trial=temp/'nes-tile821-obj-jointmirror-p1-916index-warm-pair'
    results={}
    for off in (0,81,2,83,162,164):
        def inject(lua,labels):
            # Write one bit in the independently checked WRAM row, after all packets retired.
            condition="if not injected852 and packet and pb(0)==3 and pw(8)==909 then"
            lua=once(lua,'if not injected852 then',condition)
            lua=once(lua,'emu.write(0x10000+word(0x7a)+63,0x81,emu.memType.snesWorkRam)',
                     f"local a=0x10000+word(0x70)+emu.getState()['cpu.y']+{off};emu.write(a,rd(a)~1,emu.memType.snesWorkRam)")
            lua=once(lua,'end,emu.callbackType.exec,'+str(labels['column_write'])+')',
                     'end,emu.callbackType.exec,'+str(labels['values181'])+')')
            return once(lua,'  assert(captured==commits)','  assert(injected852);assert(captured==commits)')
        results[str(off)]=run(temp,trial,'damage',column_client=CLIENT,adapt_lua=inject,
                              select_packet=lambda b,g:g==909 and b[0]==3,output_name=f'field{off}')
    results['stop']=stop_test(temp,'916index',CLIENT)
    (CLIENT.parent/'guards.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['build','prepare-drain','prepare-repeat','prepare-after-dma','replay','guards'])
    p.add_argument('temp',type=Path,nargs='?')
    p.add_argument('phase',type=int,choices=(1,2),nargs='?')
    p.add_argument('--cold',action='store_true')
    p.add_argument('--variant',choices=['index','drain','repeat','after-dma'],default='index')
    a=p.parse_args()
    if a.action=='build':client()
    elif a.action=='prepare-drain':prepare_drain()
    elif a.action in ('prepare-repeat','prepare-after-dma'):prepare_repeat(a.action=='prepare-after-dma')
    elif a.action=='guards':guards(a.temp)
    else:replay(a.temp,a.phase,a.cold,a.variant)
