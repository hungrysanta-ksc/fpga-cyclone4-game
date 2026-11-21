"""Check both D0 DMA addresses, identical wire transactions and the post-STOP checkpoint."""
import argparse
import json

from check_nes_first893 import entry_stack
from check_nes_game478 import (ELFFile, Machine, UC_HOOK_CODE, UC_ARM_REG_PC,
                               UC_ARM_REG_LR, UC_ARM_REG_R0, UC_ARM_REG_R1, crc, sha)
from check_nes_input895 import InputReplay, ROOT
from check_nes_menu533 import check
from check_nes_reset796 import replay
from package_nes_input895 import package
from prepare_nes_offer896 import BASE, MODES, WORK
from prepare_nes_trial802 import PROBES

D0 = bytes.fromhex('D0 00 00 00 00 FF F7 A5')


class AddressReplay(InputReplay):
    def __init__(self,trace,entry,fault):
        super().__init__(trace,entry,fault)
        self.transactions = []

    def exchange(self,u,tx,rx,n):
        request = bytes(u.mem_read(tx,n))
        super().exchange(u,tx,rx,n)
        self.transactions.append((tx,rx,request.hex(),bytes(u.mem_read(rx,n)).hex()))


def log_paths(src,symbols,mode):
    """Inspect the three real f_open arguments with storage and console IO stubbed."""
    m = Machine(src,bytes(128))
    m.u.mem_map(0xe000e000,0x1000)
    m.u.mem_write(symbols['nes_boot_probe798'],bytes([MODES[mode]]))
    paths = []
    def stub(cpu,at,size,name):
        if name=='f_open':
            value = cpu.reg_read(UC_ARM_REG_R1)
            paths.append(bytes(cpu.mem_read(value,80)).split(b'\0')[0].decode())
        cpu.reg_write(UC_ARM_REG_R0,int(name in ('f_open','nes_diag_active','get_snes_reset',
                                               'nes_cf86_check094','nes_return_checkpoint_enter112')))
        cpu.reg_write(UC_ARM_REG_PC,cpu.reg_read(UC_ARM_REG_LR))
    for name in ('f_open','printf','iprintf','puts','fiprintf','nes_return_failed','nes_cf86_failed094',
                 'nes_return_fail','get_snes_reset','nes_cf86_check094','nes_return_checkpoint_enter112',
                 'nes_return_checkpoint_leave112','nes_diag_active','nes_base_spi_sr116','nes_base_spi_cr116'):
        if name in m.syms:
            at=m.syms[name]
            m.u.hook_add(UC_HOOK_CODE,stub,name,begin=at,end=at)
    m.call('nes_checkpoint_begin112',[])
    m.u.mem_write(0x20012000,b'PREPARED_RESET_HELD\0')
    m.call('save_report',[0x20012000,1])
    assert paths==[f'/sd2snes/nes-{k}-mmc896-{mode.lower()}.txt' for k in ('progress','game-last','budget')],paths
    return paths


def verify():
    src = WORK/'link/src'
    obj = src/'obj-nes-100'
    firmware = (obj/'firmware.stm').read_bytes()
    with (obj/'sd2snes.elf').open('rb') as f:
        symbols = {s.name:s['st_value'] for s in ELFFile(f).get_section_by_name('.symtab').iter_symbols()}
    flash, ram = symbols['status_request876'],symbols['status_sram896']
    assert 0x0800c000<=flash<0x08040000 and 0x20000000<=ram<0x20010000 and ram%4==0
    machine = Machine(src,bytes(128))
    for mode,value in MODES.items():
        machine.u.mem_write(0x20012000,f'NES {mode} 896.nh1\0'.encode())
        assert machine.call('marker_geometry',[0x20012000])==384+value
    # Use the packaged flash load image and the linked reset startup to initialize RAM.
    machine.u.mem_write(0x0800c000,firmware)
    machine.u.mem_write(ram,b'\xcc'*8)
    machine.u.emu_start(symbols['_start']|1,symbols['bssloop'],count=40000)
    assert machine.u.reg_read(UC_ARM_REG_PC)==symbols['bssloop']
    assert bytes(machine.u.mem_read(ram,8))==D0==bytes(machine.u.mem_read(flash,8))
    nominal = 0x20010000-sum(entry_stack(src))
    entry = nominal+json.loads((ROOT/'analysis/hardware894-results.json').read_bytes())['delta_B']
    trace = json.loads((PROBES/'nes-first893/adventure893.json').read_bytes())['transactions'][:2]
    empty = bytearray.fromhex('00d6000000000000')
    empty[-1] = crc(empty[1:-1],8,7,0)
    cases = {}
    for case,fault in [('ready',None),('delayed',None),('bad-e0','e0-crc'),('bad-d0','offer-crc'),
                       ('zero-length','offer-length'),('timeout','empty'),('stop-refused',None)]:
        sequence = trace if case!='delayed' else trace[:1]+[[trace[1][0],empty.hex()]]*3+trace[1:]
        pair = {}
        for mode,value in MODES.items():
            test = AddressReplay(sequence,entry,fault)
            stop_fault = case=='stop-refused'
            row = replay(src,1,'stop' if stop_fault else 'defer',probe=value,
                         pre_snapshots=None if stop_fault else [bytes.fromhex('e6000040000003')],
                         game=test,stop_checkpoint='OFFER_STOP_OK')
            expected_ops = [0xe0]+[0xd0]*(0 if case=='bad-e0' else 4 if case=='delayed' else 1)
            assert test.ops==expected_ops and test.injected==bool(fault)
            assert test.first_write is None and row['reset_asserted'] and row['spi'].count(0x64)==1
            for tx,rx,request,reply in test.transactions[1:]:
                assert tx==(ram if mode=='SRAM' else flash) and bytes.fromhex(request)==D0
            assert row['terminal']==stop_fault
            pair[mode]=dict(transactions=test.transactions,records=row['records'],control_spi=row['spi'])
        a,b=pair['FLASH'],pair['SRAM']
        assert a['control_spi']==b['control_spi'] and a['transactions'][0]==b['transactions'][0]
        assert [x[1:] for x in a['transactions']]==[x[1:] for x in b['transactions']]
        assert [(s,total) for s,mode,total in a['records']]==[(s,total) for s,mode,total in b['records']]
        cases[case]=pair
    menu = check(src,'896','SRAM')
    assert check(src,'896','FLASH')==menu
    report=dict(firmware=sha(obj/'firmware.stm'),entry_sp=hex(nominal),replay_entry_sp=hex(entry),
                flash=hex(flash),sram=hex(ram),reset_data_copy=True,markers=MODES,cases=cases,menu=menu,
                log_paths={mode:log_paths(src,symbols,mode) for mode in MODES})
    (WORK/'checks.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'PASS {len(cases)} paired cases, D0 {flash:#x} / {ram:#x}')


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=['verify','pack'])
    if p.parse_args().action=='verify':
        verify()
    else:
        package(WORK,896,MODES,source=BASE.parent/'MMC895-FIRST-INPUT-SD-ROOT.zip',
                parent_report='input895-results',folder='MMC896-OFFER-AB-SD-ROOT',
                root_markers=MODES,log_suffixes=('-sram','-flash'),result_name='offer896-results')
