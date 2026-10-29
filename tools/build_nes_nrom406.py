# SPDX-License-Identifier: MIT
"""Create an experimental mapper0 cart_top from the actual 227 board source.

The loader, board binding and package are not changed by this script. A fixed
profile must be selected when the board is built; this is not runtime mapper
selection. This output is not approved for hardware use.
"""
import argparse
import hashlib
import json
from pathlib import Path
from nes_delta231 import BASE


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    d = a.out.resolve()
    d.mkdir(parents=True, exist_ok=False)
    original = BASE / 'probes/nes-repeat227/asm02/cart_nrom.sv'
    text = original.read_text(encoding='utf-8')
    assert text.count('module cart_top(') == 1
    assert text.count('wire [18:0] game148_chr_offset;') == 1
    assert text.count('\nmodule MMC3 (') == 1
    top = text[:text.index('wire [18:0] game148_chr_offset;')]
    top = top.replace('module cart_top(',
                      'module cart_top #(parameter NROM_PRG16=1, parameter NROM_VERTICAL=0)(')
    body = '''// NROM fixed-profile experimental cart mapping. No mapper registers or IRQ.
wire [14:0] nrom_prg = NROM_PRG16 ? {1'b0,prg_ain[13:0]} : prg_ain[14:0];
wire nrom_nt = chr_ain_orig[13];
wire nrom_a10 = NROM_VERTICAL ? chr_ain_orig[10] : chr_ain_orig[11];
assign game148_hint_physical = 22'h200000 | {9'd0,game148_hint_logic[12:0]};
assign prg_aout = prg_ain<16'h2000 ? (25'h380000 | {14'd0,prg_ain[10:0]}) : {10'd0,nrom_prg};
assign prg_dout = 8'hff;
assign prg_allow = prg_ain<16'h2000 ? 1'b1 : (prg_ain[15] && !prg_write);
assign prg_bus_write = 1'b0;
assign prg_conflict = 1'b0;
assign has_savestate = 1'b0;
assign prg_conflict_d0 = 1'b0;
assign has_flashsaves = 1'b0;
assign chr_aout = nrom_nt ? (22'h3a0000 | {11'd0,nrom_a10,chr_ain_orig[9:0]}) :
                           (22'h200000 | {9'd0,chr_ain_orig[12:0]});
assign chr_dout = 8'hff;
assign has_chr_dout = 1'b0;
assign chr_allow = 1'b0; // CHR-ROM; nametable RAM is routed via vram_ce.
assign vram_a10 = nrom_a10;
assign vram_ce = nrom_nt;
assign mapper_addr = '0;
assign mapper_data_out = '0;
assign mapper_prg_write = 1'b0;
assign mapper_ovr = 1'b0;
assign irq = 1'b0;
assign audio = audio_in;
assign diskside = '0;
assign SaveStateBus_Dout = '0;
assign Savestate_MAPRAMReadData = '0;
endmodule
'''
    output = top + body + text[text.index('\nmodule MMC3 ('):]
    (d / 'cart_nrom.sv').write_text(output, encoding='utf-8', newline='\n')
    (d / 'manifest406.json').write_text(json.dumps({
        'original': sha(original), 'candidate': sha(d / 'cart_nrom.sv'),
        'boundary': 'actual 227 cart_top port interface; fixed build profile',
        'loader_changed': False, 'board_connected': False, 'physical_test': False,
    }, indent=2) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps({'original': sha(original), 'candidate': sha(d / 'cart_nrom.sv')}))


if __name__ == '__main__':
    main()
