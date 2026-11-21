"""Build the normal 60-second game with one SRAM DMA source for every D0."""
from nes_raw506 import once
from prepare_nes_trial802 import PROBES, rename_edition

BASE = PROBES / 'nes-first893/linkC'
WORK = PROBES / 'nes-sram897'


def prepare():
    src = BASE / 'src'
    dest = WORK / 'patch'
    rename_edition(src, dest, 893, 897)
    name = 'nes_native165.c'
    code = (src / name).read_text()
    assert code.count('fn(ctx,status_request876,') == 4
    code = once(code, 'static const uint8_t status_request876[8]=',
                '/* SPI TX DMA reads this request from initialized SRAM. */\n'
                'static const uint8_t status_request876[8] '
                '__attribute__((section(".data.nes_status_d0"),aligned(4)))=')
    (dest / name).write_text(code, newline='\n')


if __name__ == '__main__':
    prepare()
