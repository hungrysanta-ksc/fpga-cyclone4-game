"""Qualify the four D0 DMA call sites in the final normal-game ARM image."""
import argparse
from collections import Counter
import struct
import zlib
from pathlib import Path
from zipfile import ZipFile

from check_nes_first893 import ColdFrame, entry_stack
from check_nes_game478 import ELFFile, Machine, UC_HOOK_CODE, UC_ARM_REG_PC, UC_ARM_REG_R1, crc
from check_nes_menu533 import check
from check_nes_reset796 import replay
from package_nes_trial872 import ROOT, loader, read, save, sha, write_verified_archive
from prepare_nes_sram897 import BASE, WORK

SRC = WORK / 'link/src'
OBJ = SRC / 'obj-nes-100'
TRACE = BASE.parent / 'adventure893.json'
D0 = bytes.fromhex('d000000000fff7a5')


class GameReplay(ColdFrame):
    def __init__(self, trace, entry, corrupt, ram, functions):
        super().__init__(trace, entry, corrupt)
        self.ram = ram
        self.functions = functions
        self.calls = Counter()
        self.d0_count = 0

    def install(self, cpu, symbols):
        args = super().install(cpu, symbols)
        if 'block1029' in symbols:
            from read_nes_ingress1029 import INGRESS, OFFSET
            self.input_records = []
            def completed(cpu, at, size, user):
                start = symbols['ptrcache'] + OFFSET + 82 * INGRESS.size
                first, end, wire, restore, retire, payload, gen, blocks = INGRESS.unpack(
                    cpu.mem_read(start, INGRESS.size))
                reads = [rx[1:-2] for tx,rx in self.rows[:self.index] if tx[0]==0xd1]
                begin = max(i for i,r in enumerate(reads) if r[:2]==b'\xe0\0')
                generation_reads = reads[begin:]
                assert gen==int.from_bytes(generation_reads[0][2:4],'big')
                if getattr(self,'ready_age_oracle',None) is not None:
                    age,payload=divmod(payload,1<<24)
                    assert age==self.ready_age_oracle[gen]
                assert blocks==len(generation_reads) and payload==sum(map(len,generation_reads))
                assert min(wire,restore,retire)>0 and ((end-first)&0xffffffff)>=wire+restore+retire
                self.input_records.append(dict(generation=gen,blocks=blocks,payload_bytes=payload))
            at = symbols['input900'] & ~1
            cpu.hook_add(UC_HOOK_CODE, completed, begin=at, end=at)
        def observe(cpu, at, size, name):
            if cpu.reg_read(UC_ARM_REG_R1) == self.ram:
                self.calls[f'{name}+0x{at-self.functions[name][0]:x}'] += 1
        for name, (start, size) in self.functions.items():
            code = bytes(cpu.mem_read(start, size))
            for offset, (insn,) in enumerate(struct.iter_unpack('<H', code)):
                if insn & 0xff87 == 0x4780:  # BLX register
                    at = start + offset * 2
                    cpu.hook_add(UC_HOOK_CODE, observe, name, begin=at, end=at)
        return args

    def exchange(self, cpu, tx, rx, n):
        request = bytes(cpu.mem_read(tx, n))
        if request[0] == 0xd0:
            assert tx == self.ram and request == D0
            self.d0_count += 1
        super().exchange(cpu, tx, rx, n)


def check_game_path(src, *, order=None, rom_revision=0x7b, rom_pages=6, content_crc=None, ready_age_oracle=None):
    obj = src / 'obj-nes-100'
    path = obj / 'firmware.stm'
    fw = path.read_bytes()
    length, checksum, inverse = struct.unpack_from('<III', fw, 8)
    assert fw[:4] == b'STM3' and len(fw) == 512 + length
    assert zlib.crc32(fw[512:]) == checksum == inverse ^ 0xffffffff
    with (obj / 'sd2snes.elf').open('rb') as f:
        symbols = {s.name: (s['st_value'], s['st_size']) for s in
                   ELFFile(f).get_section_by_name('.symtab').iter_symbols()}
    ram, width = symbols['status_request876']
    assert width == 8 and ram % 4 == 0 and 0x20000000 <= ram <= 0x20010000 - width
    m = Machine(src, bytes(128))
    m.u.mem_write(0x0800c000, fw)
    m.u.mem_write(ram, b'\xcc' * width)
    stop = symbols['bssloop'][0]
    m.u.emu_start(symbols['_start'][0] | 1, stop, count=40000)
    assert m.u.reg_read(UC_ARM_REG_PC) == stop and bytes(m.u.mem_read(ram, width)) == D0
    functions = {k:(symbols[k][0] & ~1, symbols[k][1])
                 for k in ('nes_native165_poll', 'nes_native165_prepare')}
    entry = 0x20010000 - sum(entry_stack(src)) + read(ROOT/'analysis/hardware894-results.json')['delta_B']
    fixture = read(TRACE)
    baseline = read(ROOT/'analysis/trial893-package.json')
    assert sha(TRACE) == baseline['candidate']['trace'] and fixture['client'] == baseline['client']
    ready = fixture['transactions']
    if order is not None:
        ready = order(ready)
    empty = bytearray.fromhex('00d6000000000000')
    empty[-1] = crc(empty[1:-1], 8, 7, 0)
    delayed = ready[:1] + [[D0.hex(), empty.hex()]] * 1247 + ready[1:]
    cases = {}
    for name, trace, corrupt in [('normal', ready, False), ('bad-crc', ready, True),
                                  ('1247-empty-offers', delayed, False)]:
        frame = GameReplay(trace, entry, corrupt, ram, functions)
        frame.ready_age_oracle=ready_age_oracle
        result = replay(src, 1, 'defer', pre_snapshots=[bytes.fromhex('e6000040000003')], game=frame,
                        rom_revision=rom_revision, rom_pages=rom_pages, content_crc=content_crc)
        checked = frame.result()
        assert not result['terminal'] and result['reset_asserted'] and result['spi'].count(0x64) == 1
        assert result['checkpoints'] == ['DISPLAY_NEXT', 'DISPLAY_STOPPED']
        assert checked['static_gap_bytes'] > 0 and checked['first_stack_write_to_static'] is None
        assert sum(frame.calls.values()) == frame.d0_count
        if corrupt:
            assert checked['opcodes'] == {'0xe0':1, '0xd0':1, '0xd1':1}
        else:
            assert checked['opcodes']['0xd1'] == checked['opcodes']['0xd2'] == 33
            assert checked['opcodes']['0xea'] == 1
        cases[name] = dict(**checked, d0_sites=frame.calls, control=result)
        if hasattr(frame,'input_records'):
            assert [r['generation'] for r in frame.input_records]==([] if corrupt else [905,906])
            cases[name]['input_observer']=frame.input_records
    # Check the first block and the final accepted identity against the wire
    # bytes as well as exercising the normal firmware comparisons above.
    first = [tuple(bytes.fromhex(v) for v in row) for row in ready[:5]]
    assert [tx[0] for tx, rx in first] == [0xe0, 0xd0, 0xd1, 0xd2, 0xd0]
    offer, block, pop, returned = first[1][1], first[2][1], first[3][0], first[4][1]
    assert int.from_bytes(offer[5:7], 'big') == len(block)-3
    assert crc(block[1:-2], 16, 0x1021, 0xffff) == int.from_bytes(block[-2:], 'big')
    assert offer[3:5] == pop[1:3] and int.from_bytes(returned[3:5], 'big') == int.from_bytes(pop[1:3], 'big') + 1
    last = [tuple(bytes.fromhex(v) for v in row) for row in ready[-3:]]
    assert [tx[0] for tx, rx in last] == [0xe0, 0xea, 0xe8]
    assert last[0][1][15:17] == last[1][0][1:3]
    assert len(cases['normal']['d0_sites']) == 4, cases['normal']['d0_sites']
    return cases, ram, entry


def verify(game):
    path = OBJ / 'firmware.stm'
    fw = path.read_bytes()
    assert len(fw) <= 212992
    fixture = read(TRACE)
    baseline = read(ROOT/'analysis/trial893-package.json')
    cases, ram, entry = check_game_path(SRC)
    save(WORK/'replay.json', cases)
    menu = check(SRC, '897')
    assert menu['rows']['normal']['released']
    for kind in ('progress', 'game-last', 'budget'):
        assert f'/sd2snes/nes-{kind}-mmc897.txt\0'.encode() in fw
    loader(game, SRC, 897, WORK)
    full = read(WORK/'full-loader/result.json')
    assert full['passed'] and full['firmware'] == sha(path) and full['compared'] == 393216
    recovery = {k:read(WORK/f'base-{k}/result.json') for k in ('none','program','done','busy','token')}
    assert all(r['passed'] and r['firmware_sha256'] == sha(path) and r['safe_return'] == (k=='none')
               for k,r in recovery.items())
    archive = BASE.parent/'MMC893-ADVENTURE-60SEC-SD-ROOT.zip'
    with ZipFile(archive) as z:
        bitstream = z.read(next(n for n in z.namelist() if n.endswith('/fpga_mmc893.bi3')))
    report = dict(edition=897, physical=False, ARM=sha(path), flash_B=len(fw), flash_free_B=212992-len(fw),
                  client=fixture['client'], board=baseline['board'], board_reused_from=893,
                  d0_sram=hex(ram), startup_copy=True, entry_msp=hex(entry), trace=sha(TRACE), cases=cases,
                  checks=dict(menu=menu, loader=read(WORK/'loader.json'), full_loader=full, recovery=recovery),
                  scope='Linked ARM, recorded first-screen SPI responses and modeled peripherals. '
                        'Timer advanced after first retirement to test STOP. Physical 60s run pending.')
    write_verified_archive(WORK, baseline, fw, bitstream, report, source=archive)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('game', type=Path)
    verify(parser.parse_args().game)
